#!/usr/bin/env python3
"""
Processar PDF e Salvar Vectorstore
Este script processa o PDF UMA VEZ e salva o vectorstore em disco.
Depois você pode fazer queries quantas vezes quiser sem reprocessar!
"""

import os
import sys
from dotenv import load_dotenv
import time

load_dotenv()

print("=" * 80)
print("💾 PROCESSAR PDF E SALVAR VECTORSTORE")
print("=" * 80)
print()

# Verificar argumentos
if len(sys.argv) < 2:
    print("❌ Uso: python processar_e_salvar.py nome_do_arquivo.pdf")
    print()
    print("Exemplo:")
    print("  python processar_e_salvar.py attention.pdf")
    print('  python processar_e_salvar.py "Manejo da terapia antidiabética no DM2.pdf"')
    sys.exit(1)

pdf_filename = sys.argv[1]
output_path = "./content/"
file_path = output_path + pdf_filename

if not os.path.exists(file_path):
    print(f"❌ Arquivo não encontrado: {file_path}")
    sys.exit(1)

# Nome do vectorstore (baseado no nome do arquivo)
vectorstore_name = pdf_filename.replace('.pdf', '').replace(' ', '_')
persist_directory = f"./vectorstores/{vectorstore_name}"

# Verificar se já existe
if os.path.exists(persist_directory):
    resposta = input(f"\n⚠️  Vectorstore '{vectorstore_name}' já existe. Reprocessar? (s/n): ")
    if resposta.lower() != 's':
        print("Processo cancelado.")
        sys.exit(0)
    print("\nReprocessando...")

print(f"📄 PDF: {pdf_filename}")
print(f"💾 Vectorstore: {persist_directory}")
print()
print("⏳ Processando... (isso pode demorar 5-10 minutos)")
print()

# ============================================================================
# 1. EXTRAIR DADOS DO PDF
# ============================================================================
from unstructured.partition.pdf import partition_pdf

print("1️⃣  Extraindo dados do PDF...")
chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image"],
    extract_image_block_to_payload=True,
    chunking_strategy="by_title",
    max_characters=10000,
    combine_text_under_n_chars=2000,
    new_after_n_chars=6000,
)
print(f"   ✓ {len(chunks)} chunks extraídos")

# Separar elementos
tables = []
texts = []
for chunk in chunks:
    if "Table" in str(type(chunk)):
        tables.append(chunk)
    if "CompositeElement" in str(type(chunk)):
        texts.append(chunk)

def get_images_base64(chunks):
    images_b64 = []
    for chunk in chunks:
        if "CompositeElement" in str(type(chunk)):
            if hasattr(chunk.metadata, 'orig_elements'):
                chunk_els = chunk.metadata.orig_elements
                for el in chunk_els:
                    if "Image" in str(type(el)):
                        images_b64.append(el.metadata.image_base64)
    return images_b64

images = get_images_base64(chunks)
print(f"   ✓ {len(texts)} textos, {len(tables)} tabelas, {len(images)} imagens")

# ============================================================================
# 2. GERAR RESUMOS
# ============================================================================
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

print("\n2️⃣  Gerando resumos com IA...")

# Resumir textos
model = ChatGroq(temperature=0.5, model="llama-3.1-8b-instant")
prompt_text = """
You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.

Respond only with the summary, no additional comment.

Table or text chunk: {element}
"""
prompt = ChatPromptTemplate.from_template(prompt_text)
summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()

text_summaries = []
for i, text in enumerate(texts):
    try:
        summary = summarize_chain.invoke(text)
        text_summaries.append(summary)
        print(f"   Resumindo textos: {i+1}/{len(texts)}", end="\r")
        time.sleep(0.5)
    except Exception as e:
        text_summaries.append(text.text[:500])

print(f"\n   ✓ {len(text_summaries)} resumos de texto")

# Resumir tabelas
table_summaries = []
if len(tables) > 0:
    tables_html = [table.metadata.text_as_html for table in tables]
    for i, table_html in enumerate(tables_html):
        try:
            summary = summarize_chain.invoke(table_html)
            table_summaries.append(summary)
            print(f"   Resumindo tabelas: {i+1}/{len(tables_html)}", end="\r")
            time.sleep(0.5)
        except:
            table_summaries.append(table_html[:500])
    print(f"\n   ✓ {len(table_summaries)} resumos de tabelas")

# Resumir imagens
image_summaries = []
if len(images) > 0:
    prompt_template = """Describe the image in detail. For context,
                      the image is part of a document."""
    messages = [
        (
            "user",
            [
                {"type": "text", "text": prompt_template},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,{image}"},
                },
            ],
        )
    ]
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()
    
    for i, image in enumerate(images):
        try:
            summary = chain.invoke(image)
            image_summaries.append(summary)
            print(f"   Resumindo imagens: {i+1}/{len(images)}", end="\r")
            time.sleep(0.8)
        except:
            image_summaries.append(f"Imagem {i+1}")
    print(f"\n   ✓ {len(image_summaries)} resumos de imagens")

# ============================================================================
# 3. CRIAR E SALVAR VECTORSTORE
# ============================================================================
print("\n3️⃣  Criando vectorstore PERSISTENTE...")

import uuid
from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
import pickle

# Criar diretório se não existir
os.makedirs(persist_directory, exist_ok=True)

# Vectorstore com PERSISTÊNCIA
vectorstore = Chroma(
    collection_name="rag_collection",
    embedding_function=OpenAIEmbeddings(),
    persist_directory=persist_directory  # 🔥 SALVAR EM DISCO!
)

store = InMemoryStore()
id_key = "doc_id"

retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key=id_key,
)

# Adicionar textos
doc_ids = [str(uuid.uuid4()) for _ in texts]
summary_texts = [
    Document(page_content=summary, metadata={id_key: doc_ids[i]}) 
    for i, summary in enumerate(text_summaries)
]
retriever.vectorstore.add_documents(summary_texts)
retriever.docstore.mset(list(zip(doc_ids, texts)))
print(f"   ✓ {len(texts)} textos adicionados")

# Adicionar tabelas
if len(tables) > 0:
    table_ids = [str(uuid.uuid4()) for _ in tables]
    summary_tables = [
        Document(page_content=summary, metadata={id_key: table_ids[i]}) 
        for i, summary in enumerate(table_summaries)
    ]
    retriever.vectorstore.add_documents(summary_tables)
    retriever.docstore.mset(list(zip(table_ids, tables)))
    print(f"   ✓ {len(tables)} tabelas adicionadas")

# Adicionar imagens
if len(images) > 0:
    img_ids = [str(uuid.uuid4()) for _ in images]
    summary_img = [
        Document(page_content=summary, metadata={id_key: img_ids[i]}) 
        for i, summary in enumerate(image_summaries)
    ]
    retriever.vectorstore.add_documents(summary_img)
    retriever.docstore.mset(list(zip(img_ids, images)))
    print(f"   ✓ {len(images)} imagens adicionadas")

# Salvar docstore (InMemoryStore) separadamente
docstore_path = f"{persist_directory}/docstore.pkl"
with open(docstore_path, 'wb') as f:
    pickle.dump(dict(store.store), f)
print(f"   ✓ Docstore salvo em {docstore_path}")

# Salvar metadados
metadata = {
    "pdf_filename": pdf_filename,
    "num_texts": len(texts),
    "num_tables": len(tables),
    "num_images": len(images),
    "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
}

metadata_path = f"{persist_directory}/metadata.pkl"
with open(metadata_path, 'wb') as f:
    pickle.dump(metadata, f)

print("\n" + "=" * 80)
print("✅ VECTORSTORE SALVO COM SUCESSO!")
print("=" * 80)
print()
print(f"📊 Estatísticas:")
print(f"  • Textos: {len(texts)}")
print(f"  • Tabelas: {len(tables)}")
print(f"  • Imagens: {len(images)}")
print()
print(f"💾 Localização: {persist_directory}")
print()
print("🚀 Próximo passo:")
print(f"  python consultar_vectorstore.py {vectorstore_name}")
print()
print("💡 Agora você pode fazer queries INFINITAS sem reprocessar!")
print("=" * 80)

