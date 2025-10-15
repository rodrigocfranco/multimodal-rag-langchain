#!/usr/bin/env python3
"""
Consultar Knowledge Base com RERANKER (Cohere)
Melhora DRASTICAMENTE a precisão do retrieval
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Verificar API key do Cohere
if not os.getenv("COHERE_API_KEY"):
    print("❌ COHERE_API_KEY não configurada no .env")
    print("Adicione: COHERE_API_KEY=sua_chave")
    exit(1)

modo_api = '--api' in sys.argv

if modo_api:
    # ========================================================================
    # MODO API
    # ========================================================================
    from flask import Flask, request, jsonify, render_template_string, Response
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    
    from langchain_chroma import Chroma
    from langchain.storage import InMemoryStore
    from langchain_openai import OpenAIEmbeddings
    from langchain.retrievers.multi_vector import MultiVectorRetriever
    from langchain_cohere import CohereRerank
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    from langchain_core.messages import HumanMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    from typing import List
    from base64 import b64decode
    import pickle
    
    persist_directory = "./knowledge_base"
    
    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(),
        persist_directory=persist_directory
    )
    
    docstore_path = f"{persist_directory}/docstore.pkl"
    store = InMemoryStore()
    if os.path.exists(docstore_path):
        with open(docstore_path, 'rb') as f:
            store.store = pickle.load(f)
    
    base_retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key="doc_id",
        search_kwargs={"k": 10}  # Busca 10 para rerank
    )
    
    # Wrapper para converter objetos Unstructured em Documents
    class DocumentConverter(BaseRetriever):
        retriever: MultiVectorRetriever
        
        def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
        ) -> List[Document]:
            docs = self.retriever.invoke(query)
            converted = []
            for doc in docs:
                # Converter para Document do LangChain
                if hasattr(doc, 'page_content'):
                    converted.append(doc)
                elif hasattr(doc, 'text'):
                    # Table ou CompositeElement → Document
                    # Converter metadata para dict
                    metadata = {}
                    if hasattr(doc, 'metadata'):
                        if isinstance(doc.metadata, dict):
                            metadata = doc.metadata
                        else:
                            # ElementMetadata → dict
                            metadata = doc.metadata.to_dict() if hasattr(doc.metadata, 'to_dict') else {}
                    
                    converted.append(Document(
                        page_content=doc.text,
                        metadata=metadata
                    ))
                elif isinstance(doc, str):
                    converted.append(Document(page_content=doc, metadata={}))
                else:
                    converted.append(Document(page_content=str(doc), metadata={}))
            return converted
    
    # Wrapper do retriever para converter objetos
    wrapped_retriever = DocumentConverter(retriever=base_retriever)
    
    # 🔥 RERANKER COHERE
    compressor = CohereRerank(
        model="rerank-multilingual-v3.0",  # Suporta português
        top_n=5  # Retornar top 5 após rerank
    )
    
    # Retriever com reranking (agora recebe Documents)
    retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=wrapped_retriever
    )
    
    def parse_docs(docs):
        """Docs podem ser: Document, Table, CompositeElement, ou string"""
        b64, text = [], []
        for doc in docs:
            # Extrair conteúdo baseado no tipo
            if hasattr(doc, 'page_content'):
                # Document do LangChain
                content = doc.page_content
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif hasattr(doc, 'text'):
                # Table ou CompositeElement da Unstructured
                content = doc.text
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif isinstance(doc, str):
                # String simples
                content = doc
                metadata = {}
            else:
                # Fallback
                content = str(doc)
                metadata = {}
            
            # Tentar identificar se é imagem (base64)
            try:
                b64decode(content)
                b64.append(content)
            except:
                # Criar objeto com .text para compatibilidade
                class TextDoc:
                    def __init__(self, text_content, meta):
                        self.text = text_content
                        self.metadata = meta
                
                text.append(TextDoc(content, metadata))
        
        return {"images": b64, "texts": text}
    
    def build_prompt(kwargs):
        docs = kwargs["context"]
        question = kwargs["question"]
        
        context = ""
        for text in docs["texts"]:
            source = 'unknown'
            if hasattr(text, 'metadata'):
                if isinstance(text.metadata, dict):
                    source = text.metadata.get('source', 'unknown')
                elif hasattr(text.metadata, 'source'):
                    source = text.metadata.source
            context += f"\n[{source}] {text.text}\n"
        
        prompt_content = [{
            "type": "text",
            "text": f"Answer based on context:\n{context}\n\nQuestion: {question}"
        }]
        
        for image in docs["images"]:
            prompt_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"}
            })
        
        return ChatPromptTemplate.from_messages([HumanMessage(content=prompt_content)])
    
    chain = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
    } | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | ChatOpenAI(model="gpt-4o-mini")
            | StrOutputParser()
        )
    )
    
    @app.route('/query', methods=['POST'])
    def query():
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Campo 'question' obrigatório"}), 400
        
        try:
            response = chain.invoke(data['question'])
            
            sources = set()
            for text in response['context']['texts']:
                if hasattr(text, 'metadata'):
                    if isinstance(text.metadata, dict):
                        source = text.metadata.get('source', 'unknown')
                    elif hasattr(text.metadata, 'source'):
                        source = text.metadata.source
                    else:
                        source = 'unknown'
                    sources.add(source)
            
            return jsonify({
                "answer": response['response'],
                "sources": list(sources),
                "reranked": True
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok", "reranker": "cohere"})
    
    @app.route('/', methods=['GET'])
    def home():
        """Página inicial com documentação"""
        return jsonify({
            "message": "RAG Multimodal API com Reranker Cohere",
            "version": "1.0",
            "reranker": "cohere-multilingual-v3.0",
            "endpoints": {
                "GET /": "Esta página (documentação)",
                "GET /health": "Health check",
                "POST /query": "Fazer pergunta ao RAG"
            },
            "example": {
                "url": "POST /query",
                "body": {
                    "question": "Sua pergunta aqui"
                },
                "response": {
                    "answer": "Resposta do RAG",
                    "sources": ["arquivo.pdf"],
                    "reranked": True
                }
            },
            "status": "online"
        })
    
    # =============== UI & Upload ===============
    UPLOAD_HTML = """
    <!doctype html>
    <html lang=pt-br>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Enviar PDF - Knowledge Base</title>
      <style>
        body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;max-width:800px;margin:40px auto;padding:0 16px;color:#222}
        .card{border:1px solid #ddd;border-radius:10px;padding:24px}
        .muted{color:#666;font-size:14px}
        .ok{color:#0a7a0a}
        .err{color:#b00020}
        input[type=file]{padding:8px}
        button{padding:10px 16px;border:none;border-radius:8px;background:#1f6feb;color:#fff;cursor:pointer;margin:5px}
        button:disabled{opacity:.6}
        .row{margin:12px 0}
        code{background:#f6f8fa;padding:2px 6px;border-radius:6px}
        .progress{background:#f8f9fa;border:1px solid #dee2e6;color:#495057;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow-y:auto;padding:12px;border-radius:6px}
        .button-group{display:flex;gap:10px;flex-wrap:wrap}
      </style>
    </head>
    <body>
      <h2>Enviar PDF para Knowledge Base</h2>
      <div class="card">
        <form id="form" enctype="multipart/form-data">
          <div class="row">
            <input type="file" name="file" accept="application/pdf" required />
          </div>
          <div class="row">
            <input type="password" name="api_key" placeholder="API Key (se configurada)" />
          </div>
          <div class="row">
            <div class="button-group">
              <button type="button" id="uploadBtn">📤 Enviar e Processar</button>
              <button type="button" id="streamBtn">📡 Enviar com acompanhamento (tempo real)</button>
            </div>
          </div>
        </form>
        <div id="out" class="row muted"></div>
      </div>
      <p class="muted">Depois, faça perguntas em <code>POST /query</code>.</p>
      <script>
        const form = document.getElementById('form');
        const out = document.getElementById('out');
        const uploadBtn = document.getElementById('uploadBtn');
        const streamBtn = document.getElementById('streamBtn');
        const fileInput = form.querySelector('input[type="file"]');

        // Upload normal
        uploadBtn.addEventListener('click', async (e)=>{
          e.preventDefault();
          if (!fileInput.files || fileInput.files.length === 0) {
            out.innerHTML = '<span class="err">❌ Por favor, selecione um arquivo PDF primeiro</span>';
            return;
          }
          await uploadPDF('/upload');
        });

        // Upload com streaming
        streamBtn.addEventListener('click', async (e)=>{
          e.preventDefault();
          if (!fileInput.files || fileInput.files.length === 0) {
            out.innerHTML = '<span class="err">❌ Por favor, selecione um arquivo PDF primeiro</span>';
            return;
          }
          await uploadPDF('/upload-stream', true);
        });

        async function uploadPDF(endpoint, isStreaming = false) {
          const data = new FormData(form);
          uploadBtn.disabled = true;
          streamBtn.disabled = true;
          out.innerHTML = '';
          
          if (isStreaming) {
            streamBtn.textContent = '⏳ Processando...';
            out.innerHTML = '<div class="progress" id="progress">⏳ Iniciando processamento...\n</div>';
            
            try {
              const res = await fetch(endpoint, { method:'POST', body:data });
              if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
              
              const reader = res.body.getReader();
              const decoder = new TextDecoder();
              const progressDiv = document.getElementById('progress');
              
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = line.substring(6);
                    progressDiv.textContent += data + '\n';
                    progressDiv.scrollTop = progressDiv.scrollHeight;
                  }
                }
              }
              
              const finalText = progressDiv.textContent;
              if (finalText.includes('✅')) {
                out.innerHTML = '<span class="ok">✅ PDF processado com sucesso!</span>';
                form.reset();
              } else {
                out.innerHTML = '<span class="err">❌ Erro no processamento</span>';
              }
              
            } catch (err) {
              console.error('Erro no upload streaming:', err);
              out.innerHTML = '<span class="err">❌ Erro: ' + err.message + '</span>';
            }
          } else {
            uploadBtn.textContent = '⏳ Enviando...';
            out.innerHTML = '<p class="muted">⏳ Enviando arquivo... Isso pode levar alguns minutos.</p>';

            try {
              console.log('Iniciando upload para:', endpoint);
              const res = await fetch(endpoint, { method:'POST', body:data });
              console.log('Resposta recebida:', res.status);

              const j = await res.json();
              console.log('JSON:', j);

              if (res.ok) {
                out.innerHTML = '<span class="ok">✅ ' + (j.message || 'Processado com sucesso!') + '</span>';
                form.reset();
              } else {
                out.innerHTML = '<span class="err">❌ ' + (j.error || 'Falha') + '</span>';
              }
            } catch (err) {
              console.error('Erro no upload:', err);
              out.innerHTML = '<span class="err">❌ Erro: ' + err.message + '</span>';
            }
          }
          
          uploadBtn.disabled = false;
          streamBtn.disabled = false;
          uploadBtn.textContent = '📤 Enviar e Processar';
          streamBtn.textContent = '📡 Enviar com acompanhamento (tempo real)';
        }
      </script>
    </body>
    </html>
    """

    @app.route('/ui', methods=['GET'])
    def ui():
        return render_template_string(UPLOAD_HTML)

    CHAT_HTML = """
    <!doctype html>
    <html lang=pt-br>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Chat – Knowledge Base</title>
      <style>
        body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;max-width:800px;margin:40px auto;padding:0 16px;color:#222}
        .card{border:1px solid #ddd;border-radius:10px;padding:16px}
        .row{display:flex;gap:8px}
        input,button{padding:10px;border-radius:8px;border:1px solid #ccc}
        button{background:#1f6feb;color:#fff;border:none;cursor:pointer}
        #log{margin-top:16px}
        .msg-q{background:#f6f8fa;border-radius:8px;padding:10px;margin:8px 0}
        .msg-a{background:#eef6ff;border-radius:8px;padding:10px;margin:8px 0}
        .muted{color:#666;font-size:14px}
      </style>
    </head>
    <body>
      <h2>Chat com a Base de Conhecimento</h2>
      <div class="card">
        <div class="row">
          <input id="q" type="text" placeholder="Digite sua pergunta..." style="flex:1" />
          <button id="go">Enviar</button>
        </div>
        <div id="log"></div>
        <div class="muted">As fontes são exibidas abaixo de cada resposta.</div>
      </div>
      <script>
        const q = document.getElementById('q');
        const go = document.getElementById('go');
        const log = document.getElementById('log');
        async function ask(){
          const question = q.value.trim();
          if(!question) return;
          const qEl = document.createElement('div');
          qEl.className='msg-q';
          qEl.textContent = '🧑‍💻 ' + question;
          log.appendChild(qEl);
          q.value='';
          const aEl = document.createElement('div');
          aEl.className='msg-a';
          aEl.textContent = '⏳ Buscando...';
          log.appendChild(aEl);
          try{
            const res = await fetch('/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});
            const j = await res.json();
            if(res.ok){
              aEl.innerHTML = '🤖 ' + (j.answer||'(sem resposta)') + (j.sources && j.sources.length ? '<div class="muted">📄 Fontes: ' + j.sources.join(', ') + '</div>' : '');
            } else {
              aEl.innerHTML = '❌ ' + (j.error||'Falha');
            }
          }catch(err){ aEl.textContent = '❌ ' + err.message; }
          window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'});
        }
        go.addEventListener('click', ask);
        q.addEventListener('keydown', e=>{ if(e.key==='Enter') ask(); });
      </script>
    </body>
    </html>
    """

    @app.route('/chat', methods=['GET'])
    def chat():
        return render_template_string(CHAT_HTML)

    @app.route('/upload', methods=['POST'])
    def upload():
        # API Key opcional
        required_key = os.getenv('API_SECRET_KEY')
        provided = request.form.get('api_key') or request.headers.get('X-API-Key')
        if required_key and provided != required_key:
            return jsonify({"error": "Unauthorized"}), 401

        if 'file' not in request.files:
            return jsonify({"error": "Arquivo não enviado (campo 'file')"}), 400
        f = request.files['file']
        if not f.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Apenas .pdf"}), 400

        os.makedirs('content', exist_ok=True)
        save_path = os.path.join('content', f.filename)
        f.save(save_path)

        # Processar usando o script existente
        try:
            import subprocess, sys
            proc = subprocess.run([sys.executable, 'adicionar_pdf.py', save_path], capture_output=True, text=True, timeout=1800)
            if proc.returncode != 0:
                return jsonify({"error": proc.stderr.strip() or proc.stdout.strip() or "Falha ao processar"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({"message": "PDF processado e adicionado ao knowledge base", "filename": f.filename})

    @app.route('/upload-stream', methods=['POST'])
    def upload_stream():
        # API Key opcional
        required_key = os.getenv('API_SECRET_KEY')
        provided = request.form.get('api_key') or request.headers.get('X-API-Key')
        if required_key and provided != required_key:
            return jsonify({"error": "Unauthorized"}), 401

        if 'file' not in request.files:
            return jsonify({"error": "Arquivo não enviado (campo 'file')"}), 400
        f = request.files['file']
        if not f.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Apenas .pdf"}), 400

        os.makedirs('content', exist_ok=True)
        save_path = os.path.join('content', f.filename)
        f.save(save_path)

        def generate():
            import subprocess, sys
            try:
                # Iniciar processo com streaming
                proc = subprocess.Popen(
                    [sys.executable, 'adicionar_pdf.py', save_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Stream output linha por linha
                for line in iter(proc.stdout.readline, ''):
                    if line:
                        yield f"data: {line.strip()}\n\n"
                
                # Aguardar processo terminar
                proc.wait()
                
                if proc.returncode == 0:
                    yield f"data: ✅ PDF processado com sucesso!\n\n"
                else:
                    yield f"data: ❌ Erro no processamento (código {proc.returncode})\n\n"
                    
            except Exception as e:
                yield f"data: ❌ Erro: {str(e)}\n\n"

        return Response(generate(), mimetype='text/plain')

    print("=" * 60)
    print("🌐 API COM RERANKER rodando em http://localhost:5001")
    print("=" * 60)
    print("\n🔥 Reranker: Cohere (melhora precisão em 30-40%)")
    print("\nEndpoints:")
    print("  GET  /        → Página inicial (documentação)")
    print("  GET  /health  → Health check")
    print("  GET  /ui      → Upload UI")
    print("  GET  /chat    → Chat UI")
    print("  POST /upload  → Enviar PDF (multipart)")
    print("  POST /query   → Fazer pergunta (com rerank)")
    print("\n💡 Teste no navegador: http://localhost:5001/ui")
    print("\n⚠️  Porta mudada de 5000 → 5001 (5000 usada pelo AirPlay)")
    print("\n" + "=" * 60 + "\n")
    
    # Porta configurável para Railway
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)

else:
    # ========================================================================
    # MODO TERMINAL
    # ========================================================================
    persist_directory = "./knowledge_base"
    
    if not os.path.exists(persist_directory):
        print("❌ Knowledge base vazio!")
        print("Primeiro: python adicionar_pdf.py arquivo.pdf")
        exit(1)
    
    print("📂 Carregando knowledge base com RERANKER...\n")
    
    from langchain_chroma import Chroma
    from langchain.storage import InMemoryStore
    from langchain_openai import OpenAIEmbeddings
    from langchain.retrievers.multi_vector import MultiVectorRetriever
    from langchain_cohere import CohereRerank
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    from langchain_core.messages import HumanMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    from typing import List
    from base64 import b64decode
    import pickle
    
    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(),
        persist_directory=persist_directory
    )
    
    docstore_path = f"{persist_directory}/docstore.pkl"
    store = InMemoryStore()
    if os.path.exists(docstore_path):
        with open(docstore_path, 'rb') as f:
            store.store = pickle.load(f)
    
    base_retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key="doc_id",
        search_kwargs={"k": 10}  # Busca 10 para rerank
    )
    
    # Wrapper para converter objetos Unstructured em Documents
    class DocumentConverter(BaseRetriever):
        retriever: MultiVectorRetriever
        
        def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
        ) -> List[Document]:
            docs = self.retriever.invoke(query)
            converted = []
            for doc in docs:
                # Converter para Document do LangChain
                if hasattr(doc, 'page_content'):
                    converted.append(doc)
                elif hasattr(doc, 'text'):
                    # Table ou CompositeElement → Document
                    # Converter metadata para dict
                    metadata = {}
                    if hasattr(doc, 'metadata'):
                        if isinstance(doc.metadata, dict):
                            metadata = doc.metadata
                        else:
                            # ElementMetadata → dict
                            metadata = doc.metadata.to_dict() if hasattr(doc.metadata, 'to_dict') else {}
                    
                    converted.append(Document(
                        page_content=doc.text,
                        metadata=metadata
                    ))
                elif isinstance(doc, str):
                    converted.append(Document(page_content=doc, metadata={}))
                else:
                    converted.append(Document(page_content=str(doc), metadata={}))
            return converted
    
    # Wrapper do retriever para converter objetos
    wrapped_retriever = DocumentConverter(retriever=base_retriever)
    
    # 🔥 RERANKER COHERE
    print("🔥 Inicializando Cohere Reranker...")
    compressor = CohereRerank(
        model="rerank-multilingual-v3.0",  # Suporta português!
        top_n=5  # Top 5 após reranking
    )
    
    # Retriever com reranking (agora recebe Documents)
    retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=wrapped_retriever
    )
    
    # Metadados
    metadata_path = f"{persist_directory}/metadata.pkl"
    metadata = {}
    if os.path.exists(metadata_path):
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
    
    # Mostrar PDFs
    print("=" * 60)
    print("📚 KNOWLEDGE BASE (COM RERANKER)")
    print("=" * 60)
    if 'pdfs' in metadata:
        for p in metadata['pdfs']:
            print(f"  • {p['filename']} ({p['texts']}T, {p['tables']}Tab, {p['images']}I)")
    print("=" * 60)
    print("\n🔥 Reranker ativado: Cohere Multilingual v3.0")
    print("   → Busca inicial: ~10 resultados")
    print("   → Após rerank: Top 5 mais relevantes")
    print("   → Melhoria de precisão: 30-40%\n")
    print("💡 Faça perguntas - busca em TODOS os PDFs com reranking!")
    print("   Digite 'sair' para encerrar\n")
    
    # Pipeline RAG
    def parse_docs(docs):
        """Docs podem ser: Document, Table, CompositeElement, ou string"""
        b64, text = [], []
        for doc in docs:
            # Extrair conteúdo baseado no tipo
            if hasattr(doc, 'page_content'):
                # Document do LangChain
                content = doc.page_content
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif hasattr(doc, 'text'):
                # Table ou CompositeElement da Unstructured
                content = doc.text
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif isinstance(doc, str):
                # String simples
                content = doc
                metadata = {}
            else:
                # Fallback
                content = str(doc)
                metadata = {}
            
            # Tentar identificar se é imagem (base64)
            try:
                b64decode(content)
                b64.append(content)
            except:
                # Criar objeto com .text para compatibilidade
                class TextDoc:
                    def __init__(self, text_content, meta):
                        self.text = text_content
                        self.metadata = meta
                
                text.append(TextDoc(content, metadata))
        
        return {"images": b64, "texts": text}
    
    def build_prompt(kwargs):
        docs = kwargs["context"]
        question = kwargs["question"]
        
        context = ""
        for text in docs["texts"]:
            source = 'unknown'
            if hasattr(text, 'metadata'):
                if isinstance(text.metadata, dict):
                    source = text.metadata.get('source', 'unknown')
                elif hasattr(text.metadata, 'source'):
                    source = text.metadata.source
            context += f"\n[{source}] {text.text}\n"
        
        prompt_content = [{
            "type": "text",
            "text": f"Answer based on:\n{context}\n\nQuestion: {question}"
        }]
        
        for image in docs["images"]:
            prompt_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"}
            })
        
        return ChatPromptTemplate.from_messages([HumanMessage(content=prompt_content)])
    
    chain = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
    } | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | ChatOpenAI(model="gpt-4o-mini")
            | StrOutputParser()
        )
    )
    
    # Chat loop
    while True:
        try:
            question = input("🤔 Pergunta: ").strip()
            
            if not question or question.lower() in ['sair', 'exit', 'quit']:
                print("👋 Até logo!")
                break
            
            print("⏳ Buscando com reranking...")
            response = chain.invoke(question)
            
            print(f"\n🤖 {response['response']}\n")
            
            sources = set()
            for text in response['context']['texts']:
                if hasattr(text, 'metadata'):
                    if isinstance(text.metadata, dict):
                        sources.add(text.metadata.get('source', 'unknown'))
                    elif hasattr(text.metadata, 'source'):
                        sources.add(text.metadata.source)
                    else:
                        sources.add('unknown')
            
            num_results = len(response['context']['texts'])
            print(f"📊 {num_results} resultados rerankeados")
            if sources:
                print(f"📄 Fontes: {', '.join(sorted(sources))}\n")
            
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n👋 Até logo!")
            break
        except Exception as e:
            print(f"❌ Erro: {str(e)[:100]}\n")

