#!/usr/bin/env python3
"""
Consultar Vectorstore com FILTROS AVANÇADOS
Permite filtrar por tipo, página, etc usando metadados
"""

import os
import sys
from dotenv import load_dotenv
import pickle

load_dotenv()

print("=" * 80)
print("💎 CHAT COM FILTROS AVANÇADOS DE METADADOS")
print("=" * 80)
print()

if len(sys.argv) < 2:
    print("❌ Uso: python consultar_com_filtros.py nome_do_vectorstore")
    print()
    print("Exemplo:")
    print("  python consultar_com_filtros.py Manejo_da_terapia_antidiabética_no_DM2_metadata")
    sys.exit(1)

vectorstore_name = sys.argv[1]
persist_directory = f"./vectorstores/{vectorstore_name}"

if not os.path.exists(persist_directory):
    print(f"❌ Vectorstore não encontrado: {persist_directory}")
    sys.exit(1)

print(f"📂 Carregando vectorstore: {vectorstore_name}")
print()

# Carregar vectorstore
from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever

print("⏳ Carregando...")

vectorstore = Chroma(
    collection_name="rag_collection",
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
    print(f"⏰ Processado: {metadata.get('processed_at', 'N/A')}")
    
    if 'metadata_fields' in metadata:
        print(f"\n💎 Metadados disponíveis:")
        for field in metadata['metadata_fields']:
            print(f"  • {field}")
    print()

# ============================================================================
# CONFIGURAR PIPELINE RAG
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
# CHAT INTERATIVO COM FILTROS
# ============================================================================
print("=" * 80)
print("✅ SISTEMA COM METADADOS AVANÇADOS PRONTO!")
print("=" * 80)
print()
print("💡 Comandos disponíveis:")
print("  • Digite sua pergunta normalmente")
print("  • 'info' → Ver estatísticas e metadados")
print("  • 'filtrar:tipo' → Filtrar por tipo (texto/tabela/imagem)")
print("  • 'filtrar:pagina:N' → Filtrar por página N")
print("  • 'meta' → Ver metadados das últimas fontes")
print("  • 'sair' → Encerrar")
print()

conversation_count = 0
last_response = None

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
            print(f"\n📊 Informações:")
            if metadata:
                print(f"  • Arquivo: {metadata.get('pdf_filename', 'N/A')}")
                print(f"  • Textos: {metadata.get('num_texts', 0)}")
                print(f"  • Tabelas: {metadata.get('num_tables', 0)}")
                print(f"  • Imagens: {metadata.get('num_images', 0)}")
                print(f"  • Perguntas feitas: {conversation_count}")
                if 'metadata_fields' in metadata:
                    print(f"\n  💎 Campos de metadados disponíveis:")
                    for field in metadata['metadata_fields']:
                        print(f"    • {field}")
            continue
        
        if question.lower() == 'meta' and last_response:
            print("\n💎 Metadados das últimas fontes consultadas:")
            print("-" * 80)
            for i, text in enumerate(last_response['context']['texts'][:3]):
                if hasattr(text, 'metadata'):
                    print(f"\nFonte {i+1}:")
                    meta = text.metadata if isinstance(text.metadata, dict) else {}
                    for key, value in meta.items():
                        if key != 'orig_elements':  # Não mostrar elementos internos
                            print(f"  • {key}: {value}")
            continue
        
        # Filtros avançados
        search_filter = None
        if question.lower().startswith('filtrar:'):
            parts = question.split(':')
            if len(parts) == 2:
                filter_type = parts[1]
                if filter_type in ['texto', 'text', 'tabela', 'table', 'imagem', 'image']:
                    content_type_map = {
                        'texto': 'text', 'text': 'text',
                        'tabela': 'table', 'table': 'table',
                        'imagem': 'image', 'image': 'image'
                    }
                    search_filter = {"content_type": content_type_map[filter_type]}
                    print(f"\n🔍 Filtrando por: {content_type_map[filter_type]}")
                    question = input("Digite sua pergunta: ").strip()
            elif len(parts) == 3 and parts[1] == 'pagina':
                try:
                    page_num = int(parts[2])
                    search_filter = {"page_number": page_num}
                    print(f"\n🔍 Filtrando por página: {page_num}")
                    question = input("Digite sua pergunta: ").strip()
                except:
                    print("❌ Número de página inválido")
                    continue
        
        if not question:
            continue
        
        # Processar pergunta
        print("\n⏳ Buscando resposta...")
        
        # Se tem filtro, fazer busca filtrada
        if search_filter:
            # Busca com filtro de metadados
            docs_filtered = vectorstore.similarity_search(
                question,
                k=4,
                filter=search_filter
            )
            print(f"   Encontrados {len(docs_filtered)} documentos com filtro")
        
        response = chain_with_sources.invoke(question)
        last_response = response
        
        conversation_count += 1
        
        # Mostrar resposta
        print("\n🤖 Resposta:")
        print("-" * 80)
        print(response['response'])
        print("-" * 80)
        
        # Mostrar fontes com metadados
        num_texts = len(response['context']['texts'])
        num_images = len(response['context']['images'])
        print(f"\n📚 Fontes consultadas: {num_texts} textos, {num_images} imagens")
        
        # Mostrar páginas consultadas
        pages = set()
        for text in response['context']['texts']:
            if hasattr(text, 'metadata'):
                meta = text.metadata if isinstance(text.metadata, dict) else {}
                if 'page_number' in meta:
                    pages.add(meta['page_number'])
        
        if pages:
            print(f"📄 Páginas consultadas: {sorted(pages)}")
        
        print(f"\n💡 Digite 'meta' para ver detalhes dos metadados das fontes")
        
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

