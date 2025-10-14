#!/usr/bin/env python3
"""
Consultar Knowledge Base Unificado
Busca em TODOS os PDFs de uma vez!
"""

import os
from dotenv import load_dotenv
import pickle

load_dotenv()

print("=" * 80)
print("💬 CHAT COM KNOWLEDGE BASE UNIFICADO")
print("=" * 80)
print()

persist_directory = "./vectorstores/unified_knowledge_base"

if not os.path.exists(persist_directory):
    print("❌ Knowledge base não encontrado!")
    print()
    print("💡 Primeiro adicione PDFs com:")
    print('  python adicionar_pdf_ao_vectorstore.py "seu_arquivo.pdf"')
    exit(1)

print("📂 Carregando knowledge base unificado...")
print()

# Carregar vectorstore
from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever

vectorstore = Chroma(
    collection_name="unified_rag",
    embedding_function=OpenAIEmbeddings(),
    persist_directory=persist_directory
)

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

print("✓ Knowledge base carregado!")
print()

# Mostrar informações
if metadata:
    print("=" * 80)
    print("📚 KNOWLEDGE BASE UNIFICADO")
    print("=" * 80)
    print()
    print(f"📄 Total de PDFs: {metadata.get('total_pdfs', 0)}")
    print(f"📝 Total de Textos: {metadata.get('total_texts', 0)}")
    print(f"📊 Total de Tabelas: {metadata.get('total_tables', 0)}")
    print(f"🖼️  Total de Imagens: {metadata.get('total_images', 0)}")
    print(f"⏰ Última atualização: {metadata.get('last_updated', 'N/A')}")
    print()
    
    if 'pdfs' in metadata:
        print("📄 PDFs disponíveis:")
        for i, pdf in enumerate(metadata['pdfs'], 1):
            print(f"  {i}. {pdf['filename']}")
            print(f"     └─ {pdf['num_texts']} textos, {pdf['num_tables']} tabelas, {pdf['num_images']} imagens")
    print()

# Configurar pipeline RAG
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
    sources_info = []
    
    if len(docs_by_type["texts"]) > 0:
        for text_element in docs_by_type["texts"]:
            # Adicionar fonte
            source = "Documento desconhecido"
            if hasattr(text_element, 'metadata'):
                meta = text_element.metadata if isinstance(text_element.metadata, dict) else {}
                if 'source_file' in meta:
                    source = meta['source_file']
            
            sources_info.append(source)
            context_text += f"\n[Fonte: {source}]\n{text_element.text}\n"
    
    prompt_template = f"""
    Answer the question based on the following context from multiple documents.
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

# Loop de chat
print("=" * 80)
print("✅ PRONTO! Você pode fazer perguntas sobre QUALQUER PDF do knowledge base!")
print("=" * 80)
print()
print("💡 Dicas:")
print("  • Digite sua pergunta e o sistema busca em TODOS os PDFs")
print("  • Digite 'info' para ver estatísticas")
print("  • Digite 'pdfs' para ver quais PDFs estão disponíveis")
print("  • Digite 'sair' para encerrar")
print()

conversation_count = 0

while True:
    try:
        print("─" * 80)
        question = input("\n🤔 Sua pergunta: ").strip()
        
        if not question:
            continue
        
        if question.lower() in ['sair', 'exit', 'quit', 'q']:
            print("\n👋 Encerrando. Até logo!")
            break
        
        if question.lower() == 'info':
            print(f"\n📊 Estatísticas do Knowledge Base:")
            if metadata:
                print(f"  • Total de PDFs: {metadata.get('total_pdfs', 0)}")
                print(f"  • Total de Textos: {metadata.get('total_texts', 0)}")
                print(f"  • Total de Tabelas: {metadata.get('total_tables', 0)}")
                print(f"  • Total de Imagens: {metadata.get('total_images', 0)}")
                print(f"  • Perguntas feitas: {conversation_count}")
            continue
        
        if question.lower() == 'pdfs':
            print("\n📄 PDFs no knowledge base:")
            if metadata and 'pdfs' in metadata:
                for i, pdf in enumerate(metadata['pdfs'], 1):
                    print(f"  {i}. {pdf['filename']}")
                    print(f"     └─ Adicionado em: {pdf.get('added_at', 'N/A')}")
            continue
        
        # Processar pergunta
        print("\n⏳ Buscando em TODOS os PDFs...")
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
        print(f"\n📚 Fontes consultadas: {num_texts} chunks, {num_images} imagens")
        
        # Identificar PDFs consultados
        sources = set()
        for text in response['context']['texts']:
            if hasattr(text, 'metadata'):
                meta = text.metadata if isinstance(text.metadata, dict) else {}
                if 'source_file' in meta:
                    sources.add(meta['source_file'])
        
        if sources:
            print(f"📄 PDFs consultados:")
            for source in sorted(sources):
                print(f"  • {source}")
        
    except KeyboardInterrupt:
        print("\n\n👋 Encerrando. Até logo!")
        break
    except Exception as e:
        print(f"\n❌ Erro: {str(e)[:100]}")

print()
print("=" * 80)
print(f"Sessão encerrada. Total de perguntas: {conversation_count}")
print("=" * 80)

