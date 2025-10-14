#!/usr/bin/env python3
"""
Adicionar PDF ao Vectorstore UNIFICADO
Todos os PDFs ficam no MESMO vectorstore para busca global
"""

import os
import sys
from dotenv import load_dotenv
import time

load_dotenv()

print("=" * 80)
print("📚 ADICIONAR PDF AO VECTORSTORE UNIFICADO")
print("=" * 80)
print()

if len(sys.argv) < 2:
    print("❌ Uso: python adicionar_pdf_ao_vectorstore.py nome_do_arquivo.pdf")
    print()
    print("Exemplo:")
    print("  python adicionar_pdf_ao_vectorstore.py attention.pdf")
    print('  python adicionar_pdf_ao_vectorstore.py "Manejo da terapia antidiabética no DM2.pdf"')
    sys.exit(1)

pdf_filename = sys.argv[1]
output_path = "./content/"
file_path = output_path + pdf_filename

if not os.path.exists(file_path):
    print(f"❌ Arquivo não encontrado: {file_path}")
    sys.exit(1)

# Vectorstore UNIFICADO (mesmo para todos os PDFs)
persist_directory = "./vectorstores/unified_knowledge_base"

print(f"📄 PDF: {pdf_filename}")
print(f"💾 Vectorstore: {persist_directory} (UNIFICADO)")
print()
print("⏳ Processando e adicionando ao knowledge base...")
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
    extract_image_block_types=["Image", "Table"],
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
    chunk_type = str(type(chunk).__name__)
    
    if "Table" in chunk_type and chunk not in tables:
        tables.append(chunk)
    elif chunk_type in ['CompositeElement', 'NarrativeText', 'Title', 'Text', 'ListItem']:
        texts.append(chunk)
        
        # Buscar tabelas embutidas
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            orig_elements = chunk.metadata.orig_elements
            if orig_elements is not None:
                for orig_el in orig_elements:
                    if "Table" in str(type(orig_el).__name__):
                        if orig_el not in tables:
                            tables.append(orig_el)

# Extrair imagens
def get_images_base64(chunks):
    images_b64 = []
    for chunk in chunks:
        if "Image" in str(type(chunk).__name__):
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'image_base64'):
                img_data = chunk.metadata.image_base64
                if img_data and len(img_data) > 100:
                    images_b64.append(img_data)
        
        elif hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            chunk_els = chunk.metadata.orig_elements
            if chunk_els is not None:
                for el in chunk_els:
                    if "Image" in str(type(el).__name__):
                        if hasattr(el.metadata, 'image_base64'):
                            img_data = el.metadata.image_base64
                            if img_data and len(img_data) > 100:
                                images_b64.append(img_data)
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

model = ChatGroq(temperature=0.5, model="llama-3.1-8b-instant")
prompt_text = """
You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.

Respond only with the summary, no additional comment.

Table or text chunk: {element}
"""
prompt = ChatPromptTemplate.from_template(prompt_text)
summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()

# Resumir textos
text_summaries = []
for i, text in enumerate(texts):
    try:
        text_content = text.text if hasattr(text, 'text') else str(text)
        summary = summarize_chain.invoke(text_content)
        text_summaries.append(summary)
        print(f"   Resumindo textos: {i+1}/{len(texts)}", end="\r")
        time.sleep(0.5)
    except:
        text_content = text.text if hasattr(text, 'text') else str(text)
        text_summaries.append(text_content[:500])

print(f"\n   ✓ {len(text_summaries)} resumos de texto")

# Resumir tabelas
table_summaries = []
if len(tables) > 0:
    for i, table in enumerate(tables):
        try:
            if hasattr(table, 'metadata') and hasattr(table.metadata, 'text_as_html'):
                table_content = table.metadata.text_as_html
            elif hasattr(table, 'text'):
                table_content = table.text
            else:
                table_content = str(table)
            
            summary = summarize_chain.invoke(table_content)
            table_summaries.append(summary)
            print(f"   Resumindo tabelas: {i+1}/{len(tables)}", end="\r")
            time.sleep(0.5)
        except:
            table_content = table.text if hasattr(table, 'text') else str(table)
            table_summaries.append(table_content[:500])
    print(f"\n   ✓ {len(table_summaries)} resumos de tabelas")

# Resumir imagens
image_summaries = []
if len(images) > 0:
    import base64
    
    prompt_template = """Describe the image in detail."""
    messages = [
        ("user", [
            {"type": "text", "text": prompt_template},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{image}"}},
        ])
    ]
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()
    
    for i, image in enumerate(images):
        try:
            image_size_kb = len(image) / 1024
            if image_size_kb < 1 or image_size_kb > 20000:
                image_summaries.append(f"Imagem {i+1}")
                continue
            
            try:
                base64.b64decode(image[:100])
            except:
                image_summaries.append(f"Imagem {i+1}")
                continue
            
            summary = chain.invoke(image)
            image_summaries.append(summary)
            print(f"   Resumindo imagens: {i+1}/{len(images)}", end="\r")
            time.sleep(0.8)
        except:
            image_summaries.append(f"Imagem {i+1} de {pdf_filename}")
    
    print(f"\n   ✓ {len(image_summaries)} resumos de imagens")

# ============================================================================
# 3. ADICIONAR AO VECTORSTORE UNIFICADO
# ============================================================================
print("\n3️⃣  Adicionando ao knowledge base unificado...")

import uuid
from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
import pickle

os.makedirs(persist_directory, exist_ok=True)

# Carregar ou criar vectorstore
vectorstore = Chroma(
    collection_name="unified_rag",
    embedding_function=OpenAIEmbeddings(),
    persist_directory=persist_directory
)

# Carregar ou criar docstore
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

# Adicionar textos com metadados de origem
doc_ids = [str(uuid.uuid4()) for _ in texts]
summary_texts = [
    Document(
        page_content=summary,
        metadata={
            id_key: doc_ids[i],
            "source_file": pdf_filename,  # 🔥 Rastreabilidade
            "content_type": "text",
            "chunk_index": i
        }
    ) 
    for i, summary in enumerate(text_summaries)
]
retriever.vectorstore.add_documents(summary_texts)
retriever.docstore.mset(list(zip(doc_ids, texts)))
print(f"   ✓ {len(texts)} textos adicionados")

# Adicionar tabelas
if len(tables) > 0:
    table_ids = [str(uuid.uuid4()) for _ in tables]
    summary_tables = [
        Document(
            page_content=summary,
            metadata={
                id_key: table_ids[i],
                "source_file": pdf_filename,  # 🔥 Rastreabilidade
                "content_type": "table",
                "table_index": i
            }
        ) 
        for i, summary in enumerate(table_summaries)
    ]
    retriever.vectorstore.add_documents(summary_tables)
    retriever.docstore.mset(list(zip(table_ids, tables)))
    print(f"   ✓ {len(tables)} tabelas adicionadas")

# Adicionar imagens
if len(images) > 0:
    img_ids = [str(uuid.uuid4()) for _ in images]
    summary_img = [
        Document(
            page_content=summary,
            metadata={
                id_key: img_ids[i],
                "source_file": pdf_filename,  # 🔥 Rastreabilidade
                "content_type": "image",
                "image_index": i
            }
        ) 
        for i, summary in enumerate(image_summaries)
    ]
    retriever.vectorstore.add_documents(summary_img)
    retriever.docstore.mset(list(zip(img_ids, images)))
    print(f"   ✓ {len(images)} imagens adicionadas")

# Salvar docstore atualizado
with open(docstore_path, 'wb') as f:
    pickle.dump(dict(store.store), f)

# Atualizar metadados do knowledge base
metadata_path = f"{persist_directory}/metadata.pkl"
metadata = {}
if os.path.exists(metadata_path):
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

# Adicionar este PDF aos metadados
if 'pdfs' not in metadata:
    metadata['pdfs'] = []

pdf_info = {
    "filename": pdf_filename,
    "num_texts": len(texts),
    "num_tables": len(tables),
    "num_images": len(images),
    "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
}

# Verificar se já existe
existing = [p for p in metadata['pdfs'] if p['filename'] == pdf_filename]
if existing:
    # Atualizar
    metadata['pdfs'] = [p if p['filename'] != pdf_filename else pdf_info for p in metadata['pdfs']]
    print(f"   ℹ️  PDF '{pdf_filename}' atualizado no knowledge base")
else:
    # Adicionar novo
    metadata['pdfs'].append(pdf_info)
    print(f"   ℹ️  PDF '{pdf_filename}' adicionado ao knowledge base")

# Atualizar contadores totais
metadata['total_pdfs'] = len(metadata['pdfs'])
metadata['total_texts'] = sum(p['num_texts'] for p in metadata['pdfs'])
metadata['total_tables'] = sum(p['num_tables'] for p in metadata['pdfs'])
metadata['total_images'] = sum(p['num_images'] for p in metadata['pdfs'])
metadata['last_updated'] = time.strftime("%Y-%m-%d %H:%M:%S")

with open(metadata_path, 'wb') as f:
    pickle.dump(metadata, f)

print("\n" + "=" * 80)
print("✅ PDF ADICIONADO AO KNOWLEDGE BASE UNIFICADO!")
print("=" * 80)
print()
print(f"📊 Estatísticas deste PDF:")
print(f"  • Textos: {len(texts)}")
print(f"  • Tabelas: {len(tables)}")
print(f"  • Imagens: {len(images)}")
print()
print(f"📚 Knowledge Base Total:")
print(f"  • PDFs: {metadata['total_pdfs']}")
print(f"  • Textos: {metadata['total_texts']}")
print(f"  • Tabelas: {metadata['total_tables']}")
print(f"  • Imagens: {metadata['total_images']}")
print()
print("📄 PDFs no knowledge base:")
for pdf in metadata['pdfs']:
    print(f"  • {pdf['filename']} ({pdf['num_texts']} textos, {pdf['num_tables']} tabelas, {pdf['num_images']} imagens)")
print()
print("🚀 Próximo passo:")
print("  python consultar_knowledge_base.py")
print()
print("💡 Agora você pode fazer perguntas e o sistema busca em TODOS os PDFs!")
print("=" * 80)

