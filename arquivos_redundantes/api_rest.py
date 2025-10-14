#!/usr/bin/env python3
"""
API REST para Sistema RAG - Integração com n8n
Expõe o sistema RAG via HTTP para consultas externas
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pickle
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)
CORS(app)  # Permite requisições de qualquer origem

# ============================================================================
# CONFIGURAÇÃO GLOBAL
# ============================================================================
vectorstores_cache = {}

def carregar_vectorstore(vectorstore_name):
    """Carrega vectorstore do disco (com cache)"""
    
    # Verificar cache
    if vectorstore_name in vectorstores_cache:
        return vectorstores_cache[vectorstore_name]
    
    # Carregar do disco
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
    
    persist_directory = f"./vectorstores/{vectorstore_name}"
    
    if not os.path.exists(persist_directory):
        return None
    
    # Carregar vectorstore
    vectorstore = Chroma(
        collection_name="rag_collection",
        embedding_function=OpenAIEmbeddings(),
        persist_directory=persist_directory
    )
    
    # Carregar docstore
    docstore_path = f"{persist_directory}/docstore.pkl"
    store = InMemoryStore()
    if os.path.exists(docstore_path):
        with open(docstore_path, 'rb') as f:
            store.store = pickle.load(f)
    
    id_key = "doc_id"
    
    retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key=id_key,
    )
    
    # Carregar metadados
    metadata_path = f"{persist_directory}/metadata.pkl"
    metadata = {}
    if os.path.exists(metadata_path):
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
    
    # Configurar pipeline RAG
    def parse_docs(docs):
        b64 = []
        text = []
        for doc in docs:
            try:
                b64decode(doc)
                b64.append(doc)
            except:
                text.append(doc)
        return {"images": b64, "texts": text}
    
    def build_prompt(kwargs):
        docs_by_type = kwargs["context"]
        user_question = kwargs["question"]
        
        context_text = ""
        if len(docs_by_type["texts"]) > 0:
            for text_element in docs_by_type["texts"]:
                context_text += text_element.text
        
        prompt_template = f"""
        Answer the question based on the following context.
        Context: {context_text}
        Question: {user_question}
        """
        
        prompt_content = [{"type": "text", "text": prompt_template}]
        
        if len(docs_by_type["images"]) > 0:
            for image in docs_by_type["images"]:
                prompt_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                })
        
        return ChatPromptTemplate.from_messages([HumanMessage(content=prompt_content)])
    
    chain_with_sources = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
    } | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | ChatOpenAI(model="gpt-4o-mini")
            | StrOutputParser()
        )
    )
    
    # Cache
    vectorstores_cache[vectorstore_name] = {
        "chain": chain_with_sources,
        "metadata": metadata,
        "retriever": retriever
    }
    
    return vectorstores_cache[vectorstore_name]

# ============================================================================
# ENDPOINTS DA API
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "API RAG Multimodal está funcionando!",
        "version": "1.0"
    })

@app.route('/vectorstores', methods=['GET'])
def listar_vectorstores():
    """Lista todos os vectorstores disponíveis"""
    
    vectorstores_dir = "./vectorstores"
    
    if not os.path.exists(vectorstores_dir):
        return jsonify({
            "vectorstores": [],
            "count": 0
        })
    
    vectorstores = []
    for vs_name in os.listdir(vectorstores_dir):
        vs_path = os.path.join(vectorstores_dir, vs_name)
        if os.path.isdir(vs_path):
            # Carregar metadados
            metadata_path = os.path.join(vs_path, "metadata.pkl")
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'rb') as f:
                        meta = pickle.load(f)
                    
                    vectorstores.append({
                        "name": vs_name,
                        "pdf_filename": meta.get('pdf_filename', 'N/A'),
                        "num_texts": meta.get('num_texts', 0),
                        "num_tables": meta.get('num_tables', 0),
                        "num_images": meta.get('num_images', 0),
                        "processed_at": meta.get('processed_at', 'N/A')
                    })
                except:
                    vectorstores.append({
                        "name": vs_name,
                        "error": "Metadata not available"
                    })
    
    return jsonify({
        "vectorstores": vectorstores,
        "count": len(vectorstores)
    })

@app.route('/query', methods=['POST'])
def query():
    """
    Fazer query no vectorstore
    
    Body JSON:
    {
        "vectorstore": "nome_do_vectorstore",
        "question": "sua pergunta aqui",
        "include_sources": true  // opcional, padrão true
    }
    """
    
    data = request.get_json()
    
    # Validar input
    if not data or 'vectorstore' not in data or 'question' not in data:
        return jsonify({
            "error": "Campos obrigatórios: 'vectorstore' e 'question'"
        }), 400
    
    vectorstore_name = data['vectorstore']
    question = data['question']
    include_sources = data.get('include_sources', True)
    
    # Carregar vectorstore
    vs_data = carregar_vectorstore(vectorstore_name)
    
    if vs_data is None:
        return jsonify({
            "error": f"Vectorstore '{vectorstore_name}' não encontrado",
            "available_vectorstores": [
                d for d in os.listdir("./vectorstores")
                if os.path.isdir(f"./vectorstores/{d}")
            ] if os.path.exists("./vectorstores") else []
        }), 404
    
    try:
        # Fazer query
        response = vs_data['chain'].invoke(question)
        
        # Preparar resposta
        result = {
            "answer": response['response'],
            "vectorstore": vectorstore_name,
            "pdf_filename": vs_data['metadata'].get('pdf_filename', 'N/A'),
        }
        
        if include_sources:
            # Adicionar informações das fontes
            sources = {
                "num_texts": len(response['context']['texts']),
                "num_images": len(response['context']['images']),
                "texts": [],
                "images": []
            }
            
            # Metadados dos textos
            for i, text in enumerate(response['context']['texts'][:5]):  # Primeiros 5
                text_info = {
                    "index": i,
                    "preview": text.text[:200] + "..." if len(text.text) > 200 else text.text,
                }
                
                # Adicionar metadados se disponíveis
                if hasattr(text, 'metadata'):
                    meta = text.metadata if isinstance(text.metadata, dict) else {}
                    if 'page_number' in meta:
                        text_info['page_number'] = meta['page_number']
                    if 'content_type' in meta:
                        text_info['content_type'] = meta['content_type']
                
                sources['texts'].append(text_info)
            
            # Info das imagens (sem dados base64 por ser muito grande)
            for i, img in enumerate(response['context']['images']):
                sources['images'].append({
                    "index": i,
                    "size_kb": len(img) / 1024
                })
            
            result['sources'] = sources
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/query-simple', methods=['POST'])
def query_simple():
    """
    Query simplificada para n8n
    
    Body JSON:
    {
        "vectorstore": "nome",
        "question": "pergunta"
    }
    
    Retorna apenas a resposta (string)
    """
    
    data = request.get_json()
    
    if not data or 'vectorstore' not in data or 'question' not in data:
        return jsonify({
            "error": "Campos obrigatórios: 'vectorstore' e 'question'"
        }), 400
    
    vectorstore_name = data['vectorstore']
    question = data['question']
    
    vs_data = carregar_vectorstore(vectorstore_name)
    
    if vs_data is None:
        return jsonify({
            "error": f"Vectorstore '{vectorstore_name}' não encontrado"
        }), 404
    
    try:
        response = vs_data['chain'].invoke(question)
        
        return jsonify({
            "answer": response['response']
        })
    
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/info/<vectorstore_name>', methods=['GET'])
def info_vectorstore(vectorstore_name):
    """Obter informações sobre um vectorstore"""
    
    persist_directory = f"./vectorstores/{vectorstore_name}"
    metadata_path = f"{persist_directory}/metadata.pkl"
    
    if not os.path.exists(metadata_path):
        return jsonify({
            "error": f"Vectorstore '{vectorstore_name}' não encontrado"
        }), 404
    
    try:
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        return jsonify(metadata)
    
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

# ============================================================================
# INICIAR SERVIDOR
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("🌐 API REST - Sistema RAG Multimodal")
    print("=" * 80)
    print()
    print("Endpoints disponíveis:")
    print("  • GET  /health                   → Health check")
    print("  • GET  /vectorstores             → Listar vectorstores")
    print("  • GET  /info/<nome>              → Info de um vectorstore")
    print("  • POST /query                    → Query completa (com fontes)")
    print("  • POST /query-simple             → Query simples (só resposta)")
    print()
    print("Para n8n, use: POST /query-simple")
    print()
    print("Servidor rodando em: http://localhost:5000")
    print("=" * 80)
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=False)

