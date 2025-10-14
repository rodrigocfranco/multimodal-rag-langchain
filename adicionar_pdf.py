#!/usr/bin/env python3
"""
Adicionar PDF ao Knowledge Base
Sistema único e simples com metadados otimizados
"""

import os
import sys
from dotenv import load_dotenv
import time

load_dotenv()

if len(sys.argv) < 2:
    print("Uso: python adicionar_pdf.py arquivo.pdf")
    print("   ou: python adicionar_pdf.py content/arquivo.pdf")
    exit(1)

# Aceitar tanto "arquivo.pdf" quanto "content/arquivo.pdf"
input_path = sys.argv[1]

if os.path.exists(input_path):
    # Caminho completo fornecido
    file_path = input_path
    pdf_filename = os.path.basename(input_path)
elif os.path.exists(f"./content/{input_path}"):
    # Só nome do arquivo fornecido
    file_path = f"./content/{input_path}"
    pdf_filename = input_path
else:
    print(f"❌ PDF não encontrado: {input_path}")
    print(f"   Tentou também: ./content/{input_path}")
    exit(1)

print(f"📄 Processando: {pdf_filename}")
print("⏳ Aguarde 5-10 minutos...\n")

# Vectorstore unificado
persist_directory = "./knowledge_base"

# ===========================================================================
# EXTRAIR E PROCESSAR PDF
# ===========================================================================
from unstructured.partition.pdf import partition_pdf

chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image", "Table"],
    extract_image_block_to_payload=True,
    chunking_strategy="by_title",
    max_characters=10000,
    combine_text_under_n_chars=2000,
    new_after_n_chars=6000,
)

print(f"1️⃣  Extraído: {len(chunks)} chunks")

# Separar elementos
tables, texts = [], []

for chunk in chunks:
    chunk_type = str(type(chunk).__name__)
    
    if "Table" in chunk_type and chunk not in tables:
        tables.append(chunk)
    elif chunk_type in ['CompositeElement', 'NarrativeText', 'Title', 'Text', 'ListItem']:
        texts.append(chunk)
        
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            orig_elements = chunk.metadata.orig_elements
            if orig_elements:
                for orig_el in orig_elements:
                    if "Table" in str(type(orig_el).__name__) and orig_el not in tables:
                        tables.append(orig_el)

# Extrair imagens
def get_images(chunks):
    images = []
    for chunk in chunks:
        if "Image" in str(type(chunk).__name__):
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'image_base64'):
                img = chunk.metadata.image_base64
                if img and len(img) > 100:
                    images.append(img)
        
        elif hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            if chunk.metadata.orig_elements:
                for el in chunk.metadata.orig_elements:
                    if "Image" in str(type(el).__name__) and hasattr(el.metadata, 'image_base64'):
                        img = el.metadata.image_base64
                        if img and len(img) > 100:
                            images.append(img)
    return images

images = get_images(chunks)
print(f"   ✓ {len(texts)} textos, {len(tables)} tabelas, {len(images)} imagens\n")

# ===========================================================================
# GERAR RESUMOS COM IA
# ===========================================================================
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

print("2️⃣  Gerando resumos...")

model = ChatGroq(temperature=0.5, model="llama-3.1-8b-instant")
prompt = ChatPromptTemplate.from_template(
    "Summarize concisely: {element}"
)
summarize = {"element": lambda x: x} | prompt | model | StrOutputParser()

# Textos
text_summaries = []
for i, text in enumerate(texts):
    try:
        content = text.text if hasattr(text, 'text') else str(text)
        text_summaries.append(summarize.invoke(content))
        print(f"   Textos: {i+1}/{len(texts)}", end="\r")
        time.sleep(0.5)
    except:
        text_summaries.append(content[:500])
print(f"   ✓ {len(text_summaries)} textos")

# Tabelas
table_summaries = []
if tables:
    for i, table in enumerate(tables):
        try:
            content = table.metadata.text_as_html if hasattr(table, 'metadata') and hasattr(table.metadata, 'text_as_html') else table.text if hasattr(table, 'text') else str(table)
            table_summaries.append(summarize.invoke(content))
            print(f"   Tabelas: {i+1}/{len(tables)}", end="\r")
            time.sleep(0.5)
        except:
            table_summaries.append(content[:500])
    print(f"   ✓ {len(table_summaries)} tabelas")

# Imagens
image_summaries = []
if images:
    import base64
    
    prompt_img = ChatPromptTemplate.from_messages([
        ("user", [
            {"type": "text", "text": "Describe this image:"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{image}"}},
        ])
    ])
    chain_img = prompt_img | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()
    
    for i, img in enumerate(images):
        try:
            size_kb = len(img) / 1024
            if 1 < size_kb < 20000:
                base64.b64decode(img[:100])
                image_summaries.append(chain_img.invoke(img))
                print(f"   Imagens: {i+1}/{len(images)}", end="\r")
                time.sleep(0.8)
            else:
                image_summaries.append(f"Imagem {i+1}")
        except:
            image_summaries.append(f"Imagem {i+1}")
    print(f"   ✓ {len(image_summaries)} imagens\n")

# ===========================================================================
# ADICIONAR AO KNOWLEDGE BASE
# ===========================================================================
print("3️⃣  Adicionando ao knowledge base...")

import uuid
from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
import pickle

os.makedirs(persist_directory, exist_ok=True)

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

# Adicionar com metadados
for i, summary in enumerate(text_summaries):
    doc_id = str(uuid.uuid4())
    doc = Document(
        page_content=summary,
        metadata={
            "doc_id": doc_id,
            "source": pdf_filename,
            "type": "text",
            "index": i
        }
    )
    
    # Adicionar source ao documento original
    original = texts[i]
    
    # Criar metadata dict se não existir
    if not hasattr(original, 'metadata'):
        # Criar um objeto simples com metadata
        class DocWithMetadata:
            def __init__(self, text, metadata):
                self.text = text
                self.metadata = metadata
        original = DocWithMetadata(original.text if hasattr(original, 'text') else str(original), {'source': pdf_filename})
    elif isinstance(original.metadata, dict):
        original.metadata['source'] = pdf_filename
    else:
        # ElementMetadata object
        if not hasattr(original.metadata, 'source'):
            original.metadata.source = pdf_filename
    
    retriever.vectorstore.add_documents([doc])
    retriever.docstore.mset([(doc_id, original)])

for i, summary in enumerate(table_summaries):
    doc_id = str(uuid.uuid4())
    doc = Document(
        page_content=summary,
        metadata={
            "doc_id": doc_id,
            "source": pdf_filename,
            "type": "table",
            "index": i
        }
    )
    
    # Adicionar source à tabela original
    original = tables[i]
    
    # Criar metadata dict se não existir
    if not hasattr(original, 'metadata'):
        # Criar um objeto simples com metadata
        class DocWithMetadata:
            def __init__(self, text, metadata):
                self.text = text
                self.metadata = metadata
        original = DocWithMetadata(original.text if hasattr(original, 'text') else str(original), {'source': pdf_filename})
    elif isinstance(original.metadata, dict):
        original.metadata['source'] = pdf_filename
    else:
        # ElementMetadata object
        if not hasattr(original.metadata, 'source'):
            original.metadata.source = pdf_filename
    
    retriever.vectorstore.add_documents([doc])
    retriever.docstore.mset([(doc_id, original)])

for i, summary in enumerate(image_summaries):
    doc_id = str(uuid.uuid4())
    doc = Document(
        page_content=summary,
        metadata={
            "doc_id": doc_id,
            "source": pdf_filename,
            "type": "image",
            "index": i
        }
    )
    
    # Imagens base64 não têm metadata, só salvar
    retriever.vectorstore.add_documents([doc])
    retriever.docstore.mset([(doc_id, images[i])])

# Salvar
with open(docstore_path, 'wb') as f:
    pickle.dump(dict(store.store), f)

# Metadados
metadata_path = f"{persist_directory}/metadata.pkl"
metadata = {}
if os.path.exists(metadata_path):
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

if 'pdfs' not in metadata:
    metadata['pdfs'] = []

pdf_info = {
    "filename": pdf_filename,
    "texts": len(texts),
    "tables": len(tables),
    "images": len(images),
    "added": time.strftime("%Y-%m-%d %H:%M")
}

existing = [p for p in metadata['pdfs'] if p['filename'] == pdf_filename]
if existing:
    metadata['pdfs'] = [pdf_info if p['filename'] == pdf_filename else p for p in metadata['pdfs']]
else:
    metadata['pdfs'].append(pdf_info)

with open(metadata_path, 'wb') as f:
    pickle.dump(metadata, f)

print(f"   ✓ Adicionado!\n")
print("📚 Knowledge Base:")
for p in metadata['pdfs']:
    print(f"  • {p['filename']} ({p['texts']}T, {p['tables']}Tab, {p['images']}I)")

print(f"\n✅ Pronto! Use: python consultar.py")

