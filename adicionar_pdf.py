#!/usr/bin/env python3
"""
Adicionar PDF ao Knowledge Base
Sistema único e simples com metadados otimizados
"""

import os
import sys
from dotenv import load_dotenv
import time
from document_manager import generate_pdf_id, check_duplicate

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
# GERAR PDF_ID E VERIFICAR DUPLICATA
# ===========================================================================
print("🔍 Gerando ID do documento...")
pdf_id = generate_pdf_id(file_path)
file_size = os.path.getsize(file_path)
uploaded_at = time.strftime("%Y-%m-%d %H:%M:%S")

print(f"   PDF_ID: {pdf_id[:16]}...")
print(f"   Tamanho: {file_size / 1024 / 1024:.2f} MB")

# Verificar se PDF já foi processado
existing_doc = check_duplicate(file_path, persist_directory)
if existing_doc:
    print(f"\n⚠️  Este PDF já foi processado!")
    print(f"   Adicionado em: {existing_doc.get('uploaded_at', 'desconhecido')}")
    print(f"   Chunks: {existing_doc.get('stats', {}).get('total_chunks', 0)}")

    if os.getenv("AUTO_REPROCESS") != "true":
        choice = input("\nReprocessar? (s/N): ")
        if choice.lower() != 's':
            print("❌ Processamento cancelado.")
            exit(0)
        print("\n🔄 Reprocessando documento...\n")
    else:
        print("\n🔄 AUTO_REPROCESS=true, reprocessando automaticamente...\n")
else:
    print("✅ Documento novo, prosseguindo...\n")

# ===========================================================================
# EXTRAIR E PROCESSAR PDF
# ===========================================================================
from unstructured.partition.pdf import partition_pdf

# Permite alternar a estratégia via variável de ambiente e faz fallback automático
strategy_env = os.getenv("UNSTRUCTURED_STRATEGY", "hi_res").strip().lower()

def run_partition(strategy: str):
    return partition_pdf(
        filename=file_path,
        infer_table_structure=True,
        strategy=strategy,
        extract_image_block_types=["Image", "Table"],
        extract_image_block_to_payload=True,
        chunking_strategy="by_title",
        max_characters=10000,
        combine_text_under_n_chars=2000,
        new_after_n_chars=6000,
    )

try:
    # Tenta com a estratégia definida (padrão hi_res)
    chunks = run_partition(strategy_env)
except Exception as e:
    # Se falhar por falta de libGL/cv2, faz fallback para 'fast'
    if "libGL.so.1" in str(e) or "cv2" in str(e) or "detectron2onnx" in str(e):
        print("⚠️  Falha em hi_res (provável falta de libGL). Usando strategy='fast'.")
        chunks = run_partition("fast")
    else:
        raise

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

# ===========================================================================
# FUNÇÕES DE EXTRAÇÃO DE METADATA MÉDICO
# ===========================================================================
def extract_section_heading(text_element):
    """
    Extrai section heading de elementos de texto
    Detecta seções médicas comuns em artigos científicos

    Args:
        text_element: Elemento de texto do Unstructured

    Returns:
        str: Nome da seção (Title case) ou None se não detectado
    """
    # Verificar se elemento tem metadata
    if not hasattr(text_element, 'metadata'):
        return None

    # Unstructured detecta categorias automaticamente
    if hasattr(text_element.metadata, 'category'):
        cat = text_element.metadata.category

        # Se for Title, tentar identificar qual seção
        if cat == 'Title':
            text = text_element.text if hasattr(text_element, 'text') else str(text_element)
            text_lower = text.lower().strip()

            # Seções médicas/científicas comuns (em português e inglês)
            medical_sections = {
                # Português
                'resumo': 'Resumo',
                'abstract': 'Abstract',
                'introdução': 'Introdução',
                'introduction': 'Introduction',
                'contexto': 'Contexto',
                'background': 'Background',
                'objetivos': 'Objetivos',
                'objectives': 'Objectives',
                'métodos': 'Métodos',
                'metodologia': 'Metodologia',
                'methods': 'Methods',
                'methodology': 'Methodology',
                'materiais e métodos': 'Materiais e Métodos',
                'materials and methods': 'Materials and Methods',
                'resultados': 'Resultados',
                'results': 'Results',
                'discussão': 'Discussão',
                'discussion': 'Discussion',
                'conclusão': 'Conclusão',
                'conclusões': 'Conclusão',  # Mapeia para singular
                'conclusion': 'Conclusion',
                'conclusions': 'Conclusion',  # Mapeia para singular
                'referências': 'Referências',
                'references': 'References',
                'bibliografia': 'Bibliografia',
                'agradecimentos': 'Agradecimentos',
                'acknowledgments': 'Acknowledgments',
                'acknowledgements': 'Acknowledgements',
                # Seções médicas específicas
                'relato de caso': 'Relato de Caso',
                'case report': 'Case Report',
                'apresentação do caso': 'Apresentação do Caso',
                'case presentation': 'Case Presentation',
                'achados clínicos': 'Achados Clínicos',
                'clinical findings': 'Clinical Findings',
                'diagnóstico': 'Diagnóstico',
                'diagnosis': 'Diagnosis',
                'diagnóstico diferencial': 'Diagnóstico Diferencial',
                'differential diagnosis': 'Differential Diagnosis',
                'tratamento': 'Tratamento',
                'treatment': 'Treatment',
                'terapêutica': 'Terapêutica',
                'therapeutics': 'Therapeutics',
                'manejo': 'Manejo',
                'management': 'Management',
                'evolução': 'Evolução',
                'outcome': 'Outcome',
                'desfecho': 'Desfecho',
                'follow-up': 'Follow-up',
                'acompanhamento': 'Acompanhamento',
                'complicações': 'Complicações',
                'complications': 'Complications',
                'efeitos adversos': 'Efeitos Adversos',
                'adverse effects': 'Adverse Effects',
            }

            # Procurar match exato ou por substring
            for key, value in medical_sections.items():
                if key in text_lower:
                    return value

    return None


def infer_document_type(filename):
    """
    Infere tipo de documento médico pelo nome do arquivo

    Args:
        filename: Nome do arquivo PDF

    Returns:
        str: Tipo do documento (lowercase com underscore)
    """
    filename_lower = filename.lower()

    # Artigos de revisão
    if any(word in filename_lower for word in ['artigo de revisão', 'review article', 'review -', '- review']):
        return 'review_article'

    # Guidelines / Diretrizes
    if any(word in filename_lower for word in ['guideline', 'diretriz', 'consenso', 'consensus', 'recomendações']):
        return 'clinical_guideline'

    # Relatos de caso
    if any(word in filename_lower for word in ['case report', 'relato de caso', 'case series']):
        return 'case_report'

    # Ensaios clínicos / RCTs
    if any(word in filename_lower for word in ['rct', 'trial', 'ensaio clínico', 'clinical trial', 'randomized']):
        return 'clinical_trial'

    # Meta-análises
    if any(word in filename_lower for word in ['meta-analysis', 'metanálise', 'meta-análise', 'systematic review', 'revisão sistemática']):
        return 'meta_analysis'

    # Estudos de coorte
    if any(word in filename_lower for word in ['cohort', 'coorte', 'prospective study', 'estudo prospectivo']):
        return 'cohort_study'

    # Estudos observacionais
    if any(word in filename_lower for word in ['observational', 'observacional', 'cross-sectional', 'transversal']):
        return 'observational_study'

    # Artigos originais / pesquisa
    if any(word in filename_lower for word in ['original article', 'artigo original', 'research article', 'research paper']):
        return 'original_research'

    # Editoriais / Comentários
    if any(word in filename_lower for word in ['editorial', 'commentary', 'comentário', 'perspective']):
        return 'editorial'

    # Default: artigo médico genérico
    return 'medical_article'


# Extrair imagens (com deduplicação e filtro de tamanho)
def get_images(chunks):
    seen_hashes = set()
    images = []
    filtered_count = 0  # Contar imagens filtradas
    duplicate_count = 0  # Contar duplicatas

    # Filtrar imagens pequenas (ícones, bullets, logos, decorações)
    # PDFs médicos geralmente têm figuras/gráficos maiores que 5KB
    MIN_IMAGE_SIZE_KB = float(os.getenv("MIN_IMAGE_SIZE_KB", "5"))

    for chunk in chunks:
        # Imagens diretas
        if "Image" in str(type(chunk).__name__):
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'image_base64'):
                img = chunk.metadata.image_base64
                if img and len(img) > 100:
                    # Filtrar por tamanho (remover ícones pequenos)
                    size_kb = len(img) / 1024
                    if size_kb >= MIN_IMAGE_SIZE_KB:
                        # Usar hash para deduplicar
                        img_hash = hash(img[:1000])  # Hash dos primeiros 1000 chars
                        if img_hash not in seen_hashes:
                            seen_hashes.add(img_hash)
                            images.append(img)
                        else:
                            duplicate_count += 1
                    else:
                        filtered_count += 1

        # Imagens dentro de elementos compostos
        elif hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            if chunk.metadata.orig_elements:
                for el in chunk.metadata.orig_elements:
                    if "Image" in str(type(el).__name__) and hasattr(el.metadata, 'image_base64'):
                        img = el.metadata.image_base64
                        if img and len(img) > 100:
                            # Filtrar por tamanho
                            size_kb = len(img) / 1024
                            if size_kb >= MIN_IMAGE_SIZE_KB:
                                # Usar hash para deduplicar
                                img_hash = hash(img[:1000])
                                if img_hash not in seen_hashes:
                                    seen_hashes.add(img_hash)
                                    images.append(img)
                                else:
                                    duplicate_count += 1
                            else:
                                filtered_count += 1

    return images, filtered_count, duplicate_count

images, filtered_count, duplicate_count = get_images(chunks)

# Modo debug: mostrar detalhes das imagens
if os.getenv("DEBUG_IMAGES"):
    print("\n   [DEBUG] Detalhes das imagens extraídas:")
    for i, img in enumerate(images):
        size_kb = len(img) / 1024
        print(f"     Imagem {i+1}: {size_kb:.1f} KB")
    print(f"   [DEBUG] Filtradas (muito pequenas): {filtered_count}")
    print(f"   [DEBUG] Duplicatas removidas: {duplicate_count}")

print(f"   ✓ {len(texts)} textos, {len(tables)} tabelas, {len(images)} imagens")
if filtered_count > 0 or duplicate_count > 0:
    print(f"      (filtradas: {filtered_count} pequenas, {duplicate_count} duplicatas)")
print()

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

# Inferir document_type uma vez (baseado no filename)
document_type = infer_document_type(pdf_filename)
print(f"   Tipo detectado: {document_type}")

# Adicionar com metadados
chunk_ids = []  # Para tracking
for i, summary in enumerate(text_summaries):
    doc_id = str(uuid.uuid4())
    chunk_ids.append(doc_id)

    # Extrair page_number se disponível
    page_num = None
    if hasattr(texts[i], 'metadata') and hasattr(texts[i].metadata, 'page_number'):
        page_num = texts[i].metadata.page_number

    # Extrair section heading (contexto médico)
    section = extract_section_heading(texts[i])

    doc = Document(
        page_content=summary,
        metadata={
            "doc_id": doc_id,
            "pdf_id": pdf_id,  # ✅ ID do PDF
            "source": pdf_filename,
            "type": "text",
            "index": i,
            "page_number": page_num,
            "uploaded_at": uploaded_at,
            "section": section,              # ✅ NOVO: Seção do documento
            "document_type": document_type,  # ✅ NOVO: Tipo de documento
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
    chunk_ids.append(doc_id)

    # Extrair page_number se disponível
    page_num = None
    if hasattr(tables[i], 'metadata') and hasattr(tables[i].metadata, 'page_number'):
        page_num = tables[i].metadata.page_number

    # Extrair section heading (tabelas geralmente têm context)
    section = extract_section_heading(tables[i])

    doc = Document(
        page_content=summary,
        metadata={
            "doc_id": doc_id,
            "pdf_id": pdf_id,  # ✅ ID do PDF
            "source": pdf_filename,
            "type": "table",
            "index": i,
            "page_number": page_num,
            "uploaded_at": uploaded_at,
            "section": section,              # ✅ NOVO: Seção do documento
            "document_type": document_type,  # ✅ NOVO: Tipo de documento
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
    chunk_ids.append(doc_id)

    doc = Document(
        page_content=summary,
        metadata={
            "doc_id": doc_id,
            "pdf_id": pdf_id,  # ✅ ID do PDF
            "source": pdf_filename,
            "type": "image",
            "index": i,
            "page_number": None,  # Imagens geralmente não têm page_number
            "uploaded_at": uploaded_at,
            "section": None,                 # Imagens geralmente não têm seção detectável
            "document_type": document_type,  # ✅ NOVO: Tipo de documento
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

# Migrar estrutura antiga se necessário
if 'pdfs' in metadata and 'documents' not in metadata:
    metadata['documents'] = {}
    # Converter estrutura antiga
    for old_pdf in metadata.get('pdfs', []):
        # Não temos pdf_id nos dados antigos, usar filename como chave temporária
        pass

if 'documents' not in metadata:
    metadata['documents'] = {}

processed_at = time.strftime("%Y-%m-%d %H:%M:%S")

# Informações do documento
doc_info = {
    "pdf_id": pdf_id,
    "filename": pdf_filename,
    "original_filename": os.path.basename(file_path),
    "file_size": file_size,
    "hash": pdf_id,
    "uploaded_at": uploaded_at,
    "processed_at": processed_at,
    "stats": {
        "texts": len(texts),
        "tables": len(tables),
        "images": len(images),
        "total_chunks": len(chunk_ids)
    },
    "chunk_ids": chunk_ids,
    "status": "processed",
    "error": None
}

# Atualizar ou adicionar
metadata['documents'][pdf_id] = doc_info

with open(metadata_path, 'wb') as f:
    pickle.dump(metadata, f)

print(f"   ✓ Adicionado!\n")
print("📚 Knowledge Base:")
print(f"   PDF_ID: {pdf_id[:32]}...")
print(f"   Chunks: {len(chunk_ids)} ({len(texts)}T + {len(tables)}Tab + {len(images)}I)")
print(f"   Processado em: {processed_at}")

print(f"\n✅ Pronto! Use:")
print(f"   - python consultar.py (terminal)")
print(f"   - /chat (web UI)")
print(f"   - /manage (gerenciar documentos)")

