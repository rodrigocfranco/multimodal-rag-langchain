#!/usr/bin/env python3
"""
Consultar Knowledge Base - Local ou API
Script único para chat terminal e API REST
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ===========================================================================
# MODO: Terminal ou API
# ===========================================================================
modo_api = '--api' in sys.argv or 'API_MODE' in os.environ

if modo_api:
    # ========================================================================
    # MODO API (para n8n)
    # ========================================================================
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    
    # Carregar sistema RAG
    from langchain_chroma import Chroma
    from langchain.storage import InMemoryStore
    from langchain_openai import OpenAIEmbeddings
    from langchain.retrievers.multi_vector import MultiVectorRetriever
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    from langchain_core.messages import HumanMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
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
    
    retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key="doc_id",
    )
    
    def parse_docs(docs):
        b64, text = [], []
        for doc in docs:
            try:
                b64decode(doc)
                b64.append(doc)
            except:
                text.append(doc)
        return {"images": b64, "texts": text}
    
    def build_prompt(kwargs):
        docs = kwargs["context"]
        question = kwargs["question"]
        
        context = ""
        for text in docs["texts"]:
            # Obter source do metadata (pode ser dict ou objeto)
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
                "sources": list(sources)
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok"})
    
    print("=" * 60)
    print("🌐 API rodando em http://localhost:5000")
    print("=" * 60)
    print("\nEndpoints:")
    print("  POST /query  → Fazer pergunta")
    print("  GET  /health → Health check")
    print("\nExemplo:")
    print('  curl -X POST http://localhost:5000/query \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"question": "sua pergunta"}\'')
    print("\n" + "=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

else:
    # ========================================================================
    # MODO TERMINAL (chat interativo)
    # ========================================================================
    persist_directory = "./knowledge_base"
    
    if not os.path.exists(persist_directory):
        print("❌ Knowledge base vazio!")
        print("Primeiro adicione PDFs: python adicionar_pdf.py arquivo.pdf")
        exit(1)
    
    print("📂 Carregando knowledge base...\n")
    
    from langchain_chroma import Chroma
    from langchain.storage import InMemoryStore
    from langchain_openai import OpenAIEmbeddings
    from langchain.retrievers.multi_vector import MultiVectorRetriever
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    from langchain_core.messages import HumanMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
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
    
    retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key="doc_id",
    )
    
    # Metadados
    metadata_path = f"{persist_directory}/metadata.pkl"
    metadata = {}
    if os.path.exists(metadata_path):
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
    
    # Mostrar PDFs
    print("=" * 60)
    print("📚 KNOWLEDGE BASE")
    print("=" * 60)
    if 'pdfs' in metadata:
        for p in metadata['pdfs']:
            print(f"  • {p['filename']} ({p['texts']}T, {p['tables']}Tab, {p['images']}I)")
    print("=" * 60)
    print("\n💡 Faça perguntas - busca em TODOS os PDFs!")
    print("   Digite 'sair' para encerrar\n")
    
    # Pipeline RAG
    def parse_docs(docs):
        b64, text = [], []
        for doc in docs:
            try:
                b64decode(doc)
                b64.append(doc)
            except:
                text.append(doc)
        return {"images": b64, "texts": text}
    
    def build_prompt(kwargs):
        docs = kwargs["context"]
        question = kwargs["question"]
        
        context = ""
        for text in docs["texts"]:
            # Obter source do metadata (pode ser dict ou objeto)
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
            
            print("⏳ Buscando...")
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
            
            if sources:
                print(f"📄 Fontes: {', '.join(sorted(sources))}\n")
            
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n👋 Até logo!")
            break
        except Exception as e:
            print(f"❌ Erro: {str(e)[:100]}\n")

