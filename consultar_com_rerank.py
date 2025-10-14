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
    from flask import Flask, request, jsonify
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
    
    print("=" * 60)
    print("🌐 API COM RERANKER rodando em http://localhost:5001")
    print("=" * 60)
    print("\n🔥 Reranker: Cohere (melhora precisão em 30-40%)")
    print("\nEndpoints:")
    print("  GET  /        → Página inicial (documentação)")
    print("  GET  /health  → Health check")
    print("  POST /query   → Fazer pergunta (com rerank)")
    print("\n💡 Teste no navegador: http://localhost:5001")
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

