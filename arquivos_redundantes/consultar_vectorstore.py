#!/usr/bin/env python3
"""
Consultar Vectorstore - Chat Rápido
Faz queries no vectorstore SEM reprocessar o PDF!
Muito mais rápido - inicia em segundos!
"""

import os
import sys
from dotenv import load_dotenv
import pickle

load_dotenv()

print("=" * 80)
print("💬 CHAT RÁPIDO - CONSULTAR VECTORSTORE")
print("=" * 80)
print()

# Verificar argumentos
if len(sys.argv) < 2:
    print("❌ Uso: python consultar_vectorstore.py nome_do_vectorstore")
    print()
    print("Exemplo:")
    print("  python consultar_vectorstore.py attention")
    print("  python consultar_vectorstore.py Manejo_da_terapia_antidiabética_no_DM2")
    print()
    print("Vectorstores disponíveis:")
    if os.path.exists("./vectorstores"):
        for vs in os.listdir("./vectorstores"):
            if os.path.isdir(f"./vectorstores/{vs}"):
                print(f"  • {vs}")
    else:
        print("  (nenhum vectorstore encontrado)")
    print()
    print("💡 Primeiro processe um PDF com:")
    print('  python processar_e_salvar.py "seu_arquivo.pdf"')
    sys.exit(1)

vectorstore_name = sys.argv[1]
persist_directory = f"./vectorstores/{vectorstore_name}"

if not os.path.exists(persist_directory):
    print(f"❌ Vectorstore não encontrado: {persist_directory}")
    print()
    print("Vectorstores disponíveis:")
    if os.path.exists("./vectorstores"):
        for vs in os.listdir("./vectorstores"):
            if os.path.isdir(f"./vectorstores/{vs}"):
                print(f"  • {vs}")
    sys.exit(1)

print(f"📂 Carregando vectorstore: {vectorstore_name}")
print()

# ============================================================================
# 1. CARREGAR VECTORSTORE DO DISCO
# ============================================================================
from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever

print("⏳ Carregando (leva apenas alguns segundos)...")

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

print("✓ Vectorstore carregado!")
print()

# Mostrar informações
if metadata:
    print("=" * 80)
    print("📊 INFORMAÇÕES DO DOCUMENTO")
    print("=" * 80)
    print()
    print(f"📄 Arquivo: {metadata.get('pdf_filename', 'N/A')}")
    print(f"📝 Textos: {metadata.get('num_texts', 0)}")
    print(f"📊 Tabelas: {metadata.get('num_tables', 0)}")
    print(f"🖼️  Imagens: {metadata.get('num_images', 0)}")
    print(f"⏰ Processado em: {metadata.get('processed_at', 'N/A')}")
    print()

# ============================================================================
# 2. CONFIGURAR PIPELINE RAG
# ============================================================================
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from base64 import b64decode

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

# ============================================================================
# 3. LOOP DE CHAT INTERATIVO
# ============================================================================
print("=" * 80)
print("✅ SISTEMA PRONTO! Carregou em SEGUNDOS (não reprocessou o PDF)!")
print("=" * 80)
print()
print("💡 Dicas:")
print("  • Digite sua pergunta e pressione Enter")
print("  • Digite 'sair' ou 'exit' para encerrar")
print("  • Digite 'info' para ver estatísticas")
print("  • Digite 'exemplos' para ver perguntas sugeridas")
print()

conversation_count = 0

while True:
    try:
        print("─" * 80)
        question = input("\n🤔 Sua pergunta: ").strip()
        
        if not question:
            continue
        
        # Comandos especiais
        if question.lower() in ['sair', 'exit', 'quit', 'q']:
            print("\n👋 Encerrando chat. Até logo!")
            break
        
        if question.lower() == 'info':
            print(f"\n📊 Estatísticas:")
            if metadata:
                print(f"  • Arquivo: {metadata.get('pdf_filename', 'N/A')}")
                print(f"  • Textos: {metadata.get('num_texts', 0)}")
                print(f"  • Tabelas: {metadata.get('num_tables', 0)}")
                print(f"  • Imagens: {metadata.get('num_images', 0)}")
                print(f"  • Processado: {metadata.get('processed_at', 'N/A')}")
            print(f"  • Perguntas feitas: {conversation_count}")
            print(f"  • Vectorstore: {vectorstore_name}")
            continue
        
        if question.lower() == 'exemplos':
            print("\n💡 Perguntas sugeridas:")
            print("  • What is the main topic of this document?")
            print("  • Summarize the key points")
            print("  • What are the main findings?")
            print("  • Explain the methodology used")
            print("  • What are the conclusions?")
            continue
        
        # Processar pergunta
        print("\n⏳ Buscando resposta...")
        response = chain_with_sources.invoke(question)
        
        conversation_count += 1
        
        # Mostrar resposta
        print("\n🤖 Resposta:")
        print("-" * 80)
        print(response['response'])
        print("-" * 80)
        
        # Mostrar fontes
        num_texts = len(response['context']['texts'])
        num_images = len(response['context']['images'])
        print(f"\n📚 Fontes consultadas: {num_texts} textos, {num_images} imagens")
        
    except KeyboardInterrupt:
        print("\n\n👋 Encerrando chat. Até logo!")
        break
    except Exception as e:
        print(f"\n❌ Erro: {str(e)[:100]}")
        print("Tente outra pergunta.")

print()
print("=" * 80)
print(f"Sessão encerrada. Total de perguntas: {conversation_count}")
print("=" * 80)

