#!/usr/bin/env python3
"""
Processar PDF e Salvar Vectorstore - VERSÃO CORRIGIDA
Corrige problemas de detecção de tabelas e processamento de imagens
"""

import os
import sys
from dotenv import load_dotenv
import time

load_dotenv()

print("=" * 80)
print("💾 PROCESSAR PDF E SALVAR VECTORSTORE (v2 - CORRIGIDO)")
print("=" * 80)
print()

# Verificar argumentos
if len(sys.argv) < 2:
    print("❌ Uso: python processar_e_salvar_v2.py nome_do_arquivo.pdf")
    print()
    print("Exemplo:")
    print("  python processar_e_salvar_v2.py attention.pdf")
    print('  python processar_e_salvar_v2.py "Manejo da terapia antidiabética no DM2.pdf"')
    sys.exit(1)

pdf_filename = sys.argv[1]
output_path = "./content/"
file_path = output_path + pdf_filename

if not os.path.exists(file_path):
    print(f"❌ Arquivo não encontrado: {file_path}")
    sys.exit(1)

# Nome do vectorstore
vectorstore_name = pdf_filename.replace('.pdf', '').replace(' ', '_')
persist_directory = f"./vectorstores/{vectorstore_name}"

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

# CORREÇÃO: Usar estratégia sem chunking primeiro para pegar tabelas diretas
chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image", "Table"],  # 🔥 CORREÇÃO: Adicionar "Table"
    extract_image_block_to_payload=True,
)

print(f"   ✓ {len(chunks)} elementos extraídos")

# ============================================================================
# 2. SEPARAR ELEMENTOS (CORRIGIDO)
# ============================================================================

# Separar tabelas e textos
tables = []
texts = []
images_data = []

# CORREÇÃO: Buscar tabelas tanto diretas quanto dentro de CompositeElements
for chunk in chunks:
    chunk_type = str(type(chunk).__name__)
    
    # Tabela direta
    if "Table" in chunk_type and chunk not in tables:
        tables.append(chunk)
    
    # Texto ou elemento composto
    elif chunk_type in ['CompositeElement', 'NarrativeText', 'Title', 'Text', 'ListItem']:
        texts.append(chunk)
        
        # 🔥 CORREÇÃO: Verificar se tem tabelas embutidas
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            for orig_el in chunk.metadata.orig_elements:
                if "Table" in str(type(orig_el).__name__):
                    if orig_el not in tables:
                        tables.append(orig_el)

# Extrair imagens (CORRIGIDO)
def get_images_base64_v2(chunks):
    """Extrai imagens com validação"""
    images_b64 = []
    for chunk in chunks:
        # Imagem direta
        if "Image" in str(type(chunk).__name__):
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'image_base64'):
                img_data = chunk.metadata.image_base64
                if img_data and len(img_data) > 100:  # Validação mínima
                    images_b64.append(img_data)
        
        # Imagem dentro de CompositeElement
        elif hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            chunk_els = chunk.metadata.orig_elements
            for el in chunk_els:
                if "Image" in str(type(el).__name__):
                    if hasattr(el.metadata, 'image_base64'):
                        img_data = el.metadata.image_base64
                        if img_data and len(img_data) > 100:  # Validação
                            images_b64.append(img_data)
    return images_b64

images = get_images_base64_v2(chunks)

print(f"   ✓ {len(texts)} textos, {len(tables)} tabelas, {len(images)} imagens")

# ============================================================================
# 3. GERAR RESUMOS
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

# Resumir textos
text_summaries = []
for i, text in enumerate(texts):
    try:
        # Pegar texto do elemento
        text_content = text.text if hasattr(text, 'text') else str(text)
        summary = summarize_chain.invoke(text_content)
        text_summaries.append(summary)
        print(f"   Resumindo textos: {i+1}/{len(texts)}", end="\r")
        time.sleep(0.5)
    except Exception as e:
        text_content = text.text if hasattr(text, 'text') else str(text)
        text_summaries.append(text_content[:500])

print(f"\n   ✓ {len(text_summaries)} resumos de texto")

# Resumir tabelas (CORRIGIDO)
table_summaries = []
if len(tables) > 0:
    print(f"   Processando {len(tables)} tabelas...")
    for i, table in enumerate(tables):
        try:
            # Tentar pegar HTML primeiro, senão texto
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
        except Exception as e:
            print(f"\n   ⚠️  Erro na tabela {i+1}: {str(e)[:50]}")
            table_content = table.text if hasattr(table, 'text') else str(table)
            table_summaries.append(table_content[:500])
    print(f"\n   ✓ {len(table_summaries)} resumos de tabelas")

# Resumir imagens (CORRIGIDO COM VALIDAÇÃO)
image_summaries = []
if len(images) > 0:
    print(f"   Processando {len(images)} imagens...")
    
    import base64
    
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
            # 🔥 CORREÇÃO: Validar tamanho da imagem
            image_size_kb = len(image) / 1024
            
            # OpenAI tem limite de ~20MB, mas imagens muito pequenas também falham
            if image_size_kb < 1:  # Menor que 1KB
                print(f"\n   ⚠️  Imagem {i+1} muito pequena ({image_size_kb:.1f}KB), pulando...")
                image_summaries.append(f"Imagem {i+1} (muito pequena para processar)")
                continue
            
            if image_size_kb > 20000:  # Maior que 20MB
                print(f"\n   ⚠️  Imagem {i+1} muito grande ({image_size_kb:.1f}KB), pulando...")
                image_summaries.append(f"Imagem {i+1} (muito grande para processar)")
                continue
            
            # Validar base64
            try:
                base64.b64decode(image[:100])
            except:
                print(f"\n   ⚠️  Imagem {i+1} com base64 inválido, pulando...")
                image_summaries.append(f"Imagem {i+1} (formato inválido)")
                continue
            
            # Processar imagem
            summary = chain.invoke(image)
            image_summaries.append(summary)
            print(f"   Resumindo imagens: {i+1}/{len(images)} ({image_size_kb:.1f}KB)", end="\r")
            time.sleep(0.8)
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n   ⚠️  Erro ao processar imagem {i+1}: {error_msg[:80]}")
            image_summaries.append(f"Imagem {i+1} do documento")
    
    print(f"\n   ✓ {len(image_summaries)} resumos de imagens criados")

# ============================================================================
# 4. CRIAR E SALVAR VECTORSTORE
# ============================================================================
print("\n3️⃣  Criando vectorstore PERSISTENTE...")

import uuid
from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
import pickle

os.makedirs(persist_directory, exist_ok=True)

vectorstore = Chroma(
    collection_name="rag_collection",
    embedding_function=OpenAIEmbeddings(),
    persist_directory=persist_directory
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

# Salvar docstore
docstore_path = f"{persist_directory}/docstore.pkl"
with open(docstore_path, 'wb') as f:
    pickle.dump(dict(store.store), f)
print(f"   ✓ Docstore salvo")

# Salvar metadados
metadata = {
    "pdf_filename": pdf_filename,
    "num_texts": len(texts),
    "num_tables": len(tables),
    "num_images": len(images),
    "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "version": "v2_corrigido"
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
print(f"  • Tabelas: {len(tables)} 🔥 CORRIGIDO")
print(f"  • Imagens: {len(images)}")
print()
print(f"💾 Localização: {persist_directory}")
print()
print("🚀 Próximo passo:")
print(f"  python consultar_vectorstore.py {vectorstore_name}")
print()
print("=" * 80)

