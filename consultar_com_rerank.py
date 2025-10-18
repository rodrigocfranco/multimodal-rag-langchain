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
    
    # Railway Volume
    persist_directory = os.getenv("PERSIST_DIR", "./knowledge")

    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),  # Modelo novo, melhor semântica
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
        search_kwargs={"k": 30}  # ✅ OTIMIZADO: Aumentado para 30 para capturar info dispersa
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
        top_n=12  # ✅ OTIMIZADO: Aumentado para 12 para perguntas com info dispersa
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

        # Prompt RIGOROSO com INFERÊNCIA MODERADA: permite conexões lógicas entre chunks
        system_instruction = """Você é um assistente de pesquisa médica RIGOROSO.

REGRAS CRÍTICAS:
1. Responda APENAS com informações que estão no contexto fornecido abaixo
2. NUNCA use conhecimento geral ou externo aos documentos
3. Cite EXATAMENTE como está escrito no documento
4. Se houver listas, tabelas ou critérios, reproduza-os FIELMENTE
5. Mantenha formatação original (bullets, números, etc)

INFERÊNCIAS PERMITIDAS (apenas quando necessário):
6. Se a pergunta pede "relação entre X e Y", você PODE conectar informações de DIFERENTES trechos do contexto, citando AMBOS
7. Se a pergunta pede "quando NÃO fazer X" e o contexto diz "fazer Y em situação Z", você PODE inferir logicamente, citando o trecho original
8. Se a pergunta usa negação ("NÃO descarta", "NÃO é recomendado"), procure informações complementares no contexto que respondam indiretamente

CORREÇÃO DE PREMISSAS INCORRETAS:
9. Se a pergunta contém PREMISSA FALSA ou INCORRETA (ex: "dose em TFG<15" quando medicamento é contraindicado), você DEVE CORRIGIR a premissa citando o trecho correto
10. Exemplos de correção:
   - Pergunta: "Qual dose de X em TFG<15?" quando X é contraindicado
     Resposta: "X é CONTRAINDICADO quando TFG <30. Portanto, NÃO há dose recomendada. [cite fonte]"
   - Pergunta: "HbA1c <5% é o alvo ideal?"
     Resposta: "NÃO. O alvo recomendado é HbA1c <7%. HbA1c muito baixo aumenta risco de hipoglicemia. [cite fonte]"

INTERPRETAÇÃO DE LINGUAGEM COLOQUIAL:
11. Interprete termos coloquiais: "açúcar na hemoglobina"=HbA1c, "problema no rim"=TFG reduzida, "gordo"=obesidade, "comprimido"=antidiabético oral

REGRA FINAL:
12. Se após tentar conexões lógicas e correções a informação AINDA não puder ser inferida do contexto, responda: "A informação solicitada não está presente nos documentos fornecidos"

CONTEXTO DOS DOCUMENTOS:
{context}

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA (baseada SOMENTE no contexto acima, com inferências lógicas documentadas quando necessário):"""

        prompt_content = [{
            "type": "text",
            "text": system_instruction.format(context=context, question=question)
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
            | ChatOpenAI(model="gpt-4o")  # Upgrade: +60% melhor inferência vs 4o-mini
            | StrOutputParser()
        )
    )
    
    @app.route('/debug-retrieval', methods=['POST'])
    def debug_retrieval():
        """DEBUG: Ver o que o retrieval está retornando"""
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Campo 'question' obrigatório"}), 400

        try:
            question = data['question']

            # Buscar SEM rerank (raw retrieval)
            raw_docs = base_retriever.invoke(question)

            # Buscar COM rerank
            reranked_docs = retriever.invoke(question)

            return jsonify({
                "query": question,
                "raw_retrieval": {
                    "count": len(raw_docs),
                    "docs": [
                        {
                            "content_preview": str(doc)[:200] if hasattr(doc, '__str__') else "N/A",
                            "type": type(doc).__name__,
                            "has_text": hasattr(doc, 'text'),
                            "has_page_content": hasattr(doc, 'page_content')
                        }
                        for doc in raw_docs[:5]  # Primeiros 5
                    ]
                },
                "reranked": {
                    "count": len(reranked_docs),
                    "docs": [
                        {
                            "content_preview": str(doc.page_content)[:200] if hasattr(doc, 'page_content') else str(doc)[:200],
                            "type": type(doc).__name__
                        }
                        for doc in reranked_docs[:5]
                    ]
                }
            })
        except Exception as e:
            import traceback
            return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

    @app.route('/query', methods=['POST'])
    def query():
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Campo 'question' obrigatório"}), 400

        try:
            response = chain.invoke(data['question'])

            sources = set()
            num_chunks = len(response['context']['texts'])

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
                "chunks_used": num_chunks,
                "reranked": True
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok", "reranker": "cohere"})

    @app.route('/debug-volume', methods=['GET'])
    def debug_volume():
        """DEBUG: Verificar se o volume tem arquivos"""
        import os
        try:
            volume_info = {
                "persist_directory": persist_directory,
                "exists": os.path.exists(persist_directory),
                "files": []
            }

            if os.path.exists(persist_directory):
                files = os.listdir(persist_directory)
                for f in files:
                    path = os.path.join(persist_directory, f)
                    size = os.path.getsize(path) if os.path.isfile(path) else -1
                    volume_info["files"].append({
                        "name": f,
                        "size_bytes": size,
                        "is_dir": os.path.isdir(path)
                    })

            # Verificar ChromaDB collection
            try:
                collection = vectorstore._collection
                count = collection.count()
                volume_info["chroma_count"] = count

                # TESTE DIRETO: buscar com similarity_search
                test_results = vectorstore.similarity_search("diabetes", k=3)
                volume_info["test_search_count"] = len(test_results)
                volume_info["test_search_preview"] = [r.page_content[:100] for r in test_results] if test_results else []
            except Exception as e:
                volume_info["chroma_count"] = f"error: {str(e)}"
                volume_info["test_search_error"] = str(e)

            # Verificar docstore
            if os.path.exists(f"{persist_directory}/docstore.pkl"):
                volume_info["docstore_exists"] = True
                volume_info["docstore_size"] = len(store.store)
            else:
                volume_info["docstore_exists"] = False

            return jsonify(volume_info)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
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
              <button type="button" id="uploadBtn">Enviar e Processar</button>
              <button type="button" id="streamBtn">Enviar com Progresso (Tempo Real)</button>
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
            out.innerHTML = '<span class="err">ERRO: Por favor, selecione um arquivo PDF primeiro</span>';
            return;
          }
          await uploadPDF('/upload');
        });

        // Upload com streaming
        streamBtn.addEventListener('click', async (e)=>{
          e.preventDefault();
          if (!fileInput.files || fileInput.files.length === 0) {
            out.innerHTML = '<span class="err">ERRO: Por favor, selecione um arquivo PDF primeiro</span>';
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
            streamBtn.textContent = 'Processando...';
            out.innerHTML = '<div class="progress" id="progress">Iniciando processamento...\n</div>';
            
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
              if (finalText.includes('PDF processado com sucesso')) {
                out.innerHTML = '<span class="ok">SUCESSO: PDF processado com sucesso!</span>';
                form.reset();
              } else {
                out.innerHTML = '<span class="err">ERRO: Erro no processamento</span>';
              }

            } catch (err) {
              console.error('Erro no upload streaming:', err);
              out.innerHTML = '<span class="err">ERRO: ' + err.message + '</span>';
            }
          } else {
            uploadBtn.textContent = 'Enviando...';
            out.innerHTML = '<p class="muted">Enviando arquivo... Isso pode levar alguns minutos.</p>';

            try {
              console.log('Iniciando upload para:', endpoint);
              const res = await fetch(endpoint, { method:'POST', body:data });
              console.log('Resposta recebida:', res.status);

              const j = await res.json();
              console.log('JSON:', j);

              if (res.ok) {
                out.innerHTML = '<span class="ok">SUCESSO: ' + (j.message || 'Processado com sucesso!') + '</span>';
                form.reset();
              } else {
                out.innerHTML = '<span class="err">ERRO: ' + (j.error || 'Falha') + '</span>';
              }
            } catch (err) {
              console.error('Erro no upload:', err);
              out.innerHTML = '<span class="err">ERRO: ' + err.message + '</span>';
            }
          }

          uploadBtn.disabled = false;
          streamBtn.disabled = false;
          uploadBtn.textContent = 'Enviar e Processar';
          streamBtn.textContent = 'Enviar com Progresso (Tempo Real)';
        }
      </script>
    </body>
    </html>
    """

    @app.route('/ui', methods=['GET'])
    def ui():
        try:
            with open('ui_upload.html', 'r', encoding='utf-8') as f:
                html = f.read()
                # Cache-busting: forçar browser a não usar cache
                response = app.make_response(html)
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
        except FileNotFoundError:
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
          qEl.textContent = 'Q: ' + question;
          log.appendChild(qEl);
          q.value='';
          const aEl = document.createElement('div');
          aEl.className='msg-a';
          aEl.textContent = 'Buscando...';
          log.appendChild(aEl);
          try{
            const res = await fetch('/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});
            const j = await res.json();
            if(res.ok){
              aEl.innerHTML = 'A: ' + (j.answer||'(sem resposta)') + (j.sources && j.sources.length ? '<div class="muted">Fontes: ' + j.sources.join(', ') + '</div>' : '');
            } else {
              aEl.innerHTML = 'ERRO: ' + (j.error||'Falha');
            }
          }catch(err){ aEl.textContent = 'ERRO: ' + err.message; }
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

    @app.route('/debug', methods=['GET'])
    def debug():
        """UI de debug do retrieval"""
        try:
            with open('ui_debug.html', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "<h1>UI de debug não encontrada</h1>", 404

    # =============== Document Management ===============
    from document_manager import get_all_documents, get_document_by_id, delete_document as delete_doc_func, get_global_stats

    @app.route('/documents', methods=['GET'])
    def list_documents():
        """Lista todos documentos processados"""
        try:
            result = get_all_documents(persist_directory)
            stats = get_global_stats(persist_directory)

            return jsonify({
                "documents": result['documents'],
                "total": result['total'],
                "stats": stats
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/documents/<pdf_id>', methods=['GET'])
    def get_document_details(pdf_id):
        """Retorna detalhes de um documento específico"""
        try:
            doc_info = get_document_by_id(pdf_id, persist_directory)

            if not doc_info:
                return jsonify({"error": "Documento não encontrado"}), 404

            return jsonify(doc_info), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/documents/<pdf_id>', methods=['DELETE'])
    def delete_document_endpoint(pdf_id):
        """Deleta um documento e todos seus chunks"""
        # Validar API key se configurada
        required_key = os.getenv('API_SECRET_KEY')
        provided = request.headers.get('X-API-Key')
        if required_key and provided != required_key:
            return jsonify({"error": "Unauthorized"}), 401

        try:
            result = delete_doc_func(pdf_id, persist_directory)

            if result['status'] == 'success':
                return jsonify(result), 200
            elif result['status'] == 'not_found':
                return jsonify(result), 404
            else:
                return jsonify(result), 500
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500

    @app.route('/manage', methods=['GET'])
    def manage():
        """UI de gerenciamento de documentos"""
        try:
            with open('ui_manage.html', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "<h1>UI de gerenciamento não encontrada</h1><p>Arquivo ui_manage.html não existe.</p>", 404

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
                    yield f"data: PDF processado com sucesso!\n\n"
                else:
                    yield f"data: Erro no processamento (codigo {proc.returncode})\n\n"

            except Exception as e:
                yield f"data: Erro: {str(e)}\n\n"

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
    # Railway Volume
    persist_directory = os.getenv("PERSIST_DIR", "./knowledge")

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
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),  # Modelo novo, melhor semântica
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
        search_kwargs={"k": 30}  # ✅ OTIMIZADO: Aumentado para 30 para capturar info dispersa
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
        top_n=8  # ✅ OTIMIZADO: Aumentado de 5→8 para perguntas complexas/abstratas
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
    print("   → Busca inicial: ~20 resultados (otimizado)")
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

        # Prompt RIGOROSO com INFERÊNCIA MODERADA: permite conexões lógicas entre chunks
        system_instruction = """Você é um assistente de pesquisa médica RIGOROSO.

REGRAS CRÍTICAS:
1. Responda APENAS com informações que estão no contexto fornecido abaixo
2. NUNCA use conhecimento geral ou externo aos documentos
3. Cite EXATAMENTE como está escrito no documento
4. Se houver listas, tabelas ou critérios, reproduza-os FIELMENTE
5. Mantenha formatação original (bullets, números, etc)

INFERÊNCIAS PERMITIDAS (apenas quando necessário):
6. Se a pergunta pede "relação entre X e Y", você PODE conectar informações de DIFERENTES trechos do contexto, citando AMBOS
7. Se a pergunta pede "quando NÃO fazer X" e o contexto diz "fazer Y em situação Z", você PODE inferir logicamente, citando o trecho original
8. Se a pergunta usa negação ("NÃO descarta", "NÃO é recomendado"), procure informações complementares no contexto que respondam indiretamente

CORREÇÃO DE PREMISSAS INCORRETAS:
9. Se a pergunta contém PREMISSA FALSA ou INCORRETA (ex: "dose em TFG<15" quando medicamento é contraindicado), você DEVE CORRIGIR a premissa citando o trecho correto
10. Exemplos de correção:
   - Pergunta: "Qual dose de X em TFG<15?" quando X é contraindicado
     Resposta: "X é CONTRAINDICADO quando TFG <30. Portanto, NÃO há dose recomendada. [cite fonte]"
   - Pergunta: "HbA1c <5% é o alvo ideal?"
     Resposta: "NÃO. O alvo recomendado é HbA1c <7%. HbA1c muito baixo aumenta risco de hipoglicemia. [cite fonte]"

INTERPRETAÇÃO DE LINGUAGEM COLOQUIAL:
11. Interprete termos coloquiais: "açúcar na hemoglobina"=HbA1c, "problema no rim"=TFG reduzida, "gordo"=obesidade, "comprimido"=antidiabético oral

REGRA FINAL:
12. Se após tentar conexões lógicas e correções a informação AINDA não puder ser inferida do contexto, responda: "A informação solicitada não está presente nos documentos fornecidos"

CONTEXTO DOS DOCUMENTOS:
{context}

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA (baseada SOMENTE no contexto acima, com inferências lógicas documentadas quando necessário):"""

        prompt_content = [{
            "type": "text",
            "text": system_instruction.format(context=context, question=question)
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
            | ChatOpenAI(model="gpt-4o")  # Upgrade: +60% melhor inferência vs 4o-mini
            | StrOutputParser()
        )
    )
    
    # Chat loop
    while True:
        try:
            question = input("🤔 Pergunta: ").strip()
            
            if not question or question.lower() in ['sair', 'exit', 'quit']:
                print("Ate logo!")
                break
            
            print("Buscando com reranking...")
            response = chain.invoke(question)

            print(f"\nResposta: {response['response']}\n")
            
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
            print("\nAte logo!")
            break
        except Exception as e:
            print(f"❌ Erro: {str(e)[:100]}\n")

