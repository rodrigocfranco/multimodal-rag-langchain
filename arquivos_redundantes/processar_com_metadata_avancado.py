#!/usr/bin/env python3
"""
Processar PDF com METADADOS AVANÇADOS
Sistema de metadados rico para retrieval otimizado
"""

import os
import sys
from dotenv import load_dotenv
import time

load_dotenv()

print("=" * 80)
print("💎 PROCESSAR PDF COM METADADOS AVANÇADOS")
print("=" * 80)
print()

if len(sys.argv) < 2:
    print("❌ Uso: python processar_com_metadata_avancado.py nome_do_arquivo.pdf")
    sys.exit(1)

pdf_filename = sys.argv[1]
output_path = "./content/"
file_path = output_path + pdf_filename

if not os.path.exists(file_path):
    print(f"❌ Arquivo não encontrado: {file_path}")
    sys.exit(1)

vectorstore_name = pdf_filename.replace('.pdf', '').replace(' ', '_') + "_metadata"
persist_directory = f"./vectorstores/{vectorstore_name}"

if os.path.exists(persist_directory):
    resposta = input(f"\n⚠️  Vectorstore '{vectorstore_name}' já existe. Reprocessar? (s/n): ")
    if resposta.lower() != 's':
        print("Processo cancelado.")
        sys.exit(0)

print(f"📄 PDF: {pdf_filename}")
print(f"💾 Vectorstore: {persist_directory}")
print()
print("⏳ Processando com metadados avançados...")
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
    chunking_strategy="by_title",          # ou 'basic'
    max_characters=10000,                  # padrão é 500
    combine_text_under_n_chars=2000,       # padrão é 0
    new_after_n_chars=6000,
)

print(f"   ✓ {len(chunks)} elementos extraídos")

# ============================================================================
# 2. SEPARAR E ENRIQUECER COM METADADOS
# ============================================================================
print("\n2️⃣  Enriquecendo elementos com metadados...")

tables = []
texts = []
images_data = []

# Função para extrair metadados ricos
def extract_rich_metadata(chunk, chunk_index):
    """Extrai metadados avançados do chunk"""
    metadata_dict = {
        "chunk_index": chunk_index,
        "element_type": str(type(chunk).__name__),
        "source_file": pdf_filename,
    }
    
    if hasattr(chunk, 'metadata'):
        # Página
        if hasattr(chunk.metadata, 'page_number'):
            metadata_dict["page_number"] = chunk.metadata.page_number
        
        # Coordenadas (posição no documento)
        if hasattr(chunk.metadata, 'coordinates'):
            coords = chunk.metadata.coordinates
            metadata_dict["has_coordinates"] = True
        
        # Título da seção
        if hasattr(chunk.metadata, 'parent_id'):
            metadata_dict["parent_id"] = chunk.metadata.parent_id
        
        # Tamanho do conteúdo
        if hasattr(chunk, 'text'):
            metadata_dict["content_length"] = len(chunk.text)
            metadata_dict["has_content"] = True
        
        # Tipo específico para filtros
        if "Title" in str(type(chunk).__name__):
            metadata_dict["is_title"] = True
        elif "NarrativeText" in str(type(chunk).__name__):
            metadata_dict["is_narrative"] = True
        elif "ListItem" in str(type(chunk).__name__):
            metadata_dict["is_list"] = True
    
    return metadata_dict

# Processar chunks com metadados
for idx, chunk in enumerate(chunks):
    chunk_type = str(type(chunk).__name__)
    
    # Tabela direta
    if "Table" in chunk_type and chunk not in tables:
        chunk.rich_metadata = extract_rich_metadata(chunk, idx)
        chunk.rich_metadata["content_type"] = "table"
        tables.append(chunk)
    
    # Texto ou elemento composto
    elif chunk_type in ['CompositeElement', 'NarrativeText', 'Title', 'Text', 'ListItem']:
        chunk.rich_metadata = extract_rich_metadata(chunk, idx)
        chunk.rich_metadata["content_type"] = "text"
        texts.append(chunk)
        
        # Buscar tabelas embutidas
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            orig_elements = chunk.metadata.orig_elements
            # 🔥 CORREÇÃO: Verificar se não é None
            if orig_elements is not None:
                for orig_idx, orig_el in enumerate(orig_elements):
                    if "Table" in str(type(orig_el).__name__):
                        if orig_el not in tables:
                            orig_el.rich_metadata = extract_rich_metadata(orig_el, idx)
                            orig_el.rich_metadata["content_type"] = "table"
                            orig_el.rich_metadata["embedded_in"] = idx
                            orig_el.rich_metadata["embedded_position"] = orig_idx
                            tables.append(orig_el)

# Extrair imagens com metadados
def get_images_with_metadata(chunks):
    """Extrai imagens com metadados ricos"""
    images_list = []
    img_counter = 0
    
    for chunk_idx, chunk in enumerate(chunks):
        # Imagem direta
        if "Image" in str(type(chunk).__name__):
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'image_base64'):
                img_data = chunk.metadata.image_base64
                if img_data and len(img_data) > 100:
                    img_metadata = extract_rich_metadata(chunk, chunk_idx)
                    img_metadata["content_type"] = "image"
                    img_metadata["image_index"] = img_counter
                    img_metadata["image_size_kb"] = len(img_data) / 1024
                    
                    images_list.append({
                        'data': img_data,
                        'metadata': img_metadata
                    })
                    img_counter += 1
        
        # Imagem dentro de CompositeElement
        elif hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            chunk_els = chunk.metadata.orig_elements
            # 🔥 CORREÇÃO: Verificar se não é None
            if chunk_els is not None:
                for el_idx, el in enumerate(chunk_els):
                    if "Image" in str(type(el).__name__):
                        if hasattr(el.metadata, 'image_base64'):
                            img_data = el.metadata.image_base64
                            if img_data and len(img_data) > 100:
                                img_metadata = extract_rich_metadata(el, chunk_idx)
                                img_metadata["content_type"] = "image"
                                img_metadata["image_index"] = img_counter
                                img_metadata["image_size_kb"] = len(img_data) / 1024
                                img_metadata["embedded_in"] = chunk_idx
                                img_metadata["embedded_position"] = el_idx
                                
                                images_list.append({
                                    'data': img_data,
                                    'metadata': img_metadata
                                })
                                img_counter += 1
    
    return images_list

images_with_meta = get_images_with_metadata(chunks)
images = [img['data'] for img in images_with_meta]
images_metadata = [img['metadata'] for img in images_with_meta]

print(f"   ✓ {len(texts)} textos, {len(tables)} tabelas, {len(images)} imagens")
print(f"   ✓ Metadados avançados extraídos para todos os elementos")

# ============================================================================
# 3. GERAR RESUMOS
# ============================================================================
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

print("\n3️⃣  Gerando resumos com IA...")

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
        text_content = text.text if hasattr(text, 'text') else str(text)
        summary = summarize_chain.invoke(text_content)
        text_summaries.append(summary)
        print(f"   Resumindo textos: {i+1}/{len(texts)}", end="\r")
        time.sleep(0.5)
    except Exception as e:
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
            image_size_kb = len(image) / 1024
            
            if image_size_kb < 1 or image_size_kb > 20000:
                image_summaries.append(f"Imagem {i+1} (tamanho inválido)")
                continue
            
            try:
                base64.b64decode(image[:100])
            except:
                image_summaries.append(f"Imagem {i+1} (formato inválido)")
                continue
            
            summary = chain.invoke(image)
            image_summaries.append(summary)
            print(f"   Resumindo imagens: {i+1}/{len(images)}", end="\r")
            time.sleep(0.8)
            
        except Exception as e:
            image_summaries.append(f"Imagem {i+1} do documento")
    
    print(f"\n   ✓ {len(image_summaries)} resumos de imagens")

# ============================================================================
# 4. CRIAR VECTORSTORE COM METADADOS AVANÇADOS
# ============================================================================
print("\n4️⃣  Criando vectorstore com metadados AVANÇADOS...")

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

# 🔥 ADICIONAR TEXTOS COM METADADOS RICOS
doc_ids = [str(uuid.uuid4()) for _ in texts]
summary_texts = []

for i, summary in enumerate(text_summaries):
    text_elem = texts[i]
    
    # Metadados avançados
    meta = {
        id_key: doc_ids[i],
        "content_type": "text",
        "element_type": str(type(text_elem).__name__),
        "chunk_index": i,
        "source_file": pdf_filename,
    }
    
    # Adicionar metadados do chunk original
    if hasattr(text_elem, 'rich_metadata'):
        meta.update(text_elem.rich_metadata)
    
    # Metadados do Unstructured
    if hasattr(text_elem, 'metadata'):
        if hasattr(text_elem.metadata, 'page_number'):
            meta["page_number"] = text_elem.metadata.page_number
        if hasattr(text_elem, 'text'):
            meta["char_count"] = len(text_elem.text)
            meta["word_count"] = len(text_elem.text.split())
    
    summary_texts.append(Document(page_content=summary, metadata=meta))

retriever.vectorstore.add_documents(summary_texts)
retriever.docstore.mset(list(zip(doc_ids, texts)))
print(f"   ✓ {len(texts)} textos com metadados avançados")

# 🔥 ADICIONAR TABELAS COM METADADOS RICOS
if len(tables) > 0:
    table_ids = [str(uuid.uuid4()) for _ in tables]
    summary_tables = []
    
    for i, summary in enumerate(table_summaries):
        table_elem = tables[i]
        
        # Metadados avançados para tabelas
        meta = {
            id_key: table_ids[i],
            "content_type": "table",
            "element_type": "Table",
            "table_index": i,
            "source_file": pdf_filename,
        }
        
        # Metadados do chunk
        if hasattr(table_elem, 'rich_metadata'):
            meta.update(table_elem.rich_metadata)
        
        # Metadados específicos de tabela
        if hasattr(table_elem, 'metadata'):
            if hasattr(table_elem.metadata, 'page_number'):
                meta["page_number"] = table_elem.metadata.page_number
            if hasattr(table_elem.metadata, 'text_as_html'):
                meta["has_html"] = True
                meta["html_length"] = len(table_elem.metadata.text_as_html)
            if hasattr(table_elem, 'text'):
                meta["char_count"] = len(table_elem.text)
        
        summary_tables.append(Document(page_content=summary, metadata=meta))
    
    retriever.vectorstore.add_documents(summary_tables)
    retriever.docstore.mset(list(zip(table_ids, tables)))
    print(f"   ✓ {len(tables)} tabelas com metadados avançados")

# 🔥 ADICIONAR IMAGENS COM METADADOS RICOS
if len(images) > 0:
    img_ids = [str(uuid.uuid4()) for _ in images]
    summary_img = []
    
    for i, summary in enumerate(image_summaries):
        # Metadados avançados para imagens
        meta = {
            id_key: img_ids[i],
            "content_type": "image",
            "element_type": "Image",
            "image_index": i,
            "source_file": pdf_filename,
        }
        
        # Adicionar metadados extraídos
        if i < len(images_metadata):
            meta.update(images_metadata[i])
        
        # Tamanho da imagem
        meta["image_size_kb"] = len(images[i]) / 1024
        
        summary_img.append(Document(page_content=summary, metadata=meta))
    
    retriever.vectorstore.add_documents(summary_img)
    retriever.docstore.mset(list(zip(img_ids, images)))
    print(f"   ✓ {len(images)} imagens com metadados avançados")

# Salvar docstore
docstore_path = f"{persist_directory}/docstore.pkl"
with open(docstore_path, 'wb') as f:
    pickle.dump(dict(store.store), f)

# Salvar metadados do documento
doc_metadata = {
    "pdf_filename": pdf_filename,
    "num_texts": len(texts),
    "num_tables": len(tables),
    "num_images": len(images),
    "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "version": "metadata_avancado",
    "metadata_fields": [
        "content_type", "element_type", "page_number", "chunk_index",
        "source_file", "char_count", "word_count", "table_index",
        "image_index", "image_size_kb", "embedded_in", "has_html"
    ]
}

metadata_path = f"{persist_directory}/metadata.pkl"
with open(metadata_path, 'wb') as f:
    pickle.dump(doc_metadata, f)

print("\n" + "=" * 80)
print("✅ VECTORSTORE COM METADADOS AVANÇADOS SALVO!")
print("=" * 80)
print()
print(f"📊 Estatísticas:")
print(f"  • Textos: {len(texts)}")
print(f"  • Tabelas: {len(tables)}")
print(f"  • Imagens: {len(images)}")
print()
print(f"💎 Metadados adicionados:")
print(f"  • content_type (texto/tabela/imagem)")
print(f"  • page_number (número da página)")
print(f"  • char_count / word_count (tamanho)")
print(f"  • chunk_index / table_index / image_index")
print(f"  • element_type (tipo específico)")
print(f"  • embedded_in (se está embutido)")
print()
print(f"💾 Localização: {persist_directory}")
print()
print("🚀 Próximo passo:")
print(f"  python consultar_com_filtros.py {vectorstore_name}")
print()
print("=" * 80)

