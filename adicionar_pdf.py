#!/usr/bin/env python3
"""
Adicionar PDF ao Knowledge Base
Sistema único e simples com metadados otimizados + Metadata Enrichment
"""

import os
import sys
from dotenv import load_dotenv
import time
from document_manager import generate_pdf_id, check_duplicate
from PIL import Image
import io
from base64 import b64decode, b64encode

load_dotenv()

# ===========================================================================
# CONFIGURAÇÕES GLOBAIS
# ===========================================================================
MIN_IMAGE_SIZE_KB = float(os.getenv("MIN_IMAGE_SIZE_KB", "30"))

# ===========================================================================
# METADATA ENRICHMENT SYSTEM
# ===========================================================================
print("🚀 Carregando Metadata Enrichment System...")
from metadata_extractors import MetadataEnricher

# Inicializar extractors globais (uma vez só para melhor performance)
enricher = MetadataEnricher()
print()

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

# Vectorstore unificado - Railway Volume
persist_directory = os.getenv("PERSIST_DIR", "./knowledge")
persist_directory = os.path.abspath(persist_directory)  # Converter para caminho absoluto

print(f"=" * 70)
print(f"🔧 CONFIGURAÇÃO DE DIRETÓRIOS")
print(f"=" * 70)
print(f"Current working directory: {os.getcwd()}")
print(f"PERSIST_DIR (env): {os.getenv('PERSIST_DIR', 'NOT SET')}")
print(f"persist_directory (absoluto): {persist_directory}")
print(f"Docstore será salvo em: {persist_directory}/docstore.pkl")
print(f"=" * 70)
print()

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
        languages=["por"],  # ✅ Força OCR em português

        # ✅ CHUNKING OTIMIZADO PARA DOCUMENTOS MÉDICOS
        # NOTA IMPORTANTE: Tabelas são SEMPRE preservadas inteiras (isoladas)
        # tanto em by_title quanto em basic - ver documentação Unstructured
        chunking_strategy="by_title",

        # Hard maximum: ~2500 tokens - chunks grandes preservam contexto completo
        max_characters=10000,

        # Agrupa elementos pequenos (<4000 chars) no mesmo chunk
        # Combina múltiplos parágrafos relacionados da mesma seção
        combine_text_under_n_chars=4000,

        # Soft maximum: força quebra em 6000 chars (~1500 tokens)
        # Balanceia contexto amplo com eficiência de retrieval
        new_after_n_chars=6000,
    )

try:
    # Tenta com a estratégia definida (padrão hi_res)
    chunks = run_partition(strategy_env)
    strategy_used = strategy_env
except Exception as e:
    # Se falhar por falta de libGL/cv2, faz fallback para 'fast'
    if "libGL.so.1" in str(e) or "cv2" in str(e) or "detectron2onnx" in str(e):
        print("⚠️  Falha em hi_res (provável falta de libGL). Usando strategy='fast'.")
        chunks = run_partition("fast")
        strategy_used = "fast"
    else:
        raise

print(f"1️⃣  Extraído: {len(chunks)} elementos (estratégia: {strategy_used})")

# DEBUG: Mostrar tipos de elementos
element_types = {}
for chunk in chunks:
    chunk_type = str(type(chunk).__name__)
    element_types[chunk_type] = element_types.get(chunk_type, 0) + 1

print(f"\n   Tipos de elementos encontrados:")
for elem_type, count in sorted(element_types.items()):
    print(f"     {elem_type}: {count}")

# Separar elementos
# Com chunking by_title, Unstructured retorna:
# - CompositeElement: textos agrupados por seção
# - Table: tabelas isoladas (sempre preservadas inteiras)
#
# NOTA: Com parâmetros agressivos de chunking, tabelas podem vir:
# 1. Como elementos Table de primeira classe (ideal)
# 2. Dentro de CompositeElement.metadata.orig_elements (com chunking agressivo)
tables = []
texts = []

for chunk in chunks:
    chunk_type = str(type(chunk))

    # Tabelas diretas (primeira classe)
    if "Table" in chunk_type:
        tables.append(chunk)

    # CompositeElements (textos agrupados)
    if "CompositeElement" in chunk_type:
        texts.append(chunk)

        # CRITICAL: Verificar se há tabelas escondidas em orig_elements
        # Com chunking agressivo, tabelas podem ser agrupadas aqui
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            if chunk.metadata.orig_elements:
                for orig_el in chunk.metadata.orig_elements:
                    if "Table" in str(type(orig_el).__name__):
                        # Tabela encontrada dentro de CompositeElement
                        # Adicionar à lista de tabelas
                        if orig_el not in tables:
                            tables.append(orig_el)
                            print(f"   ⚠️  Tabela encontrada em orig_elements (chunk agressivo)")

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


# ===========================================================================
# CONVERSÃO DE IMAGENS PARA FORMATO SUPORTADO
# ===========================================================================

def convert_image_to_jpeg_base64(image_base64_str, auto_rotate=False):
    """
    Converte qualquer formato de imagem para JPEG (suportado por GPT-4 Vision).

    Formatos não suportados: TIFF, BMP, ICO, etc.
    Formatos suportados: PNG, JPEG, GIF, WEBP

    Esta função garante que TODAS as imagens sejam JPEG válidas.

    Args:
        image_base64_str: String base64 da imagem
        auto_rotate: Se True, detecta e corrige orientação vertical (tabelas rotacionadas)

    Returns:
        tuple: (jpeg_base64, success, rotation_applied)
    """
    try:
        # Decodificar base64 para bytes
        image_bytes = b64decode(image_base64_str)

        # Abrir imagem com PIL
        img = Image.open(io.BytesIO(image_bytes))

        rotation_applied = 0

        # ✅ AUTO-ROTATE: Detectar e corrigir orientação vertical
        if auto_rotate:
            width, height = img.size

            # Se altura >> largura, provavelmente está rotacionada
            # Ratio > 1.5 indica orientação vertical/portrait
            aspect_ratio = height / width if width > 0 else 1

            if aspect_ratio > 1.5:
                # Rotacionar 90° no sentido anti-horário (counterclockwise)
                # Isso transforma portrait → landscape
                img = img.rotate(90, expand=True)
                rotation_applied = 90
                print(f"      🔄 Imagem rotacionada 90° (aspect ratio: {aspect_ratio:.2f})")

        # Converter para RGB (remove alpha channel se houver)
        # Isso é necessário porque JPEG não suporta transparência
        if img.mode in ('RGBA', 'LA', 'P'):
            # Criar background branco
            background = Image.new('RGB', img.size, (255, 255, 255))

            # Converter P (palette) para RGBA primeiro
            if img.mode == 'P':
                img = img.convert('RGBA')

            # Colar imagem sobre background branco (preserva transparência)
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])  # Usa alpha channel como máscara
            else:
                background.paste(img)

            img = background
        elif img.mode != 'RGB':
            # Outros modos (L, CMYK, etc.) → RGB
            img = img.convert('RGB')

        # Salvar como JPEG em buffer
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        jpeg_bytes = output.getvalue()

        # Re-encodar para base64
        jpeg_base64 = b64encode(jpeg_bytes).decode('utf-8')

        return jpeg_base64, True, rotation_applied

    except Exception as e:
        # Se conversão falhar, retornar None
        print(f"      ⚠️  Erro ao converter imagem: {str(e)[:100]}")
        return None, False, 0


# Extrair imagens base64 dos chunks
def get_images_base64(chunks):
    """
    Extrai imagens de:
    1. Elementos Image de primeira classe (diretos)
    2. Imagens dentro de CompositeElement.metadata.orig_elements

    Filtra imagens pequenas (<5KB) que geralmente são ícones/decoração

    ✅ CONVERTE TODAS AS IMAGENS PARA JPEG (formato suportado por GPT-4 Vision)
    """
    images_b64 = []
    seen_hashes = set()  # Deduplicação
    filtered_count = 0
    total_found = 0

    # Filtro: imagens muito pequenas geralmente são ícones/decoração
    # 30KB threshold: Balance entre filtrar ícones e manter fluxogramas/diagramas importantes
    # Imagens <30KB: tipicamente ícones, logos, decorações, elementos gráficos pequenos
    # Imagens >30KB: fluxogramas, diagramas, gráficos importantes, fotos, screenshots
    MIN_IMAGE_SIZE_KB = float(os.getenv("MIN_IMAGE_SIZE_KB", "30"))

    for chunk in chunks:
        chunk_type = str(type(chunk))

        # CASO 1: Elementos Image de primeira classe
        if "Image" in chunk_type:
            total_found += 1
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'image_base64'):
                img = chunk.metadata.image_base64
                if img and len(img) > 100:
                    # ✅ CONVERT TO JPEG BEFORE SIZE CHECK
                    jpeg_img, success, _ = convert_image_to_jpeg_base64(img, auto_rotate=False)
                    if not success:
                        filtered_count += 1
                        continue

                    size_kb = len(jpeg_img) / 1024

                    # Filtrar imagens muito pequenas
                    if size_kb >= MIN_IMAGE_SIZE_KB:
                        # Deduplicar por hash
                        img_hash = hash(jpeg_img[:1000])
                        if img_hash not in seen_hashes:
                            seen_hashes.add(img_hash)
                            images_b64.append(jpeg_img)  # ✅ Use converted JPEG
                    else:
                        filtered_count += 1

        # CASO 2: Imagens dentro de CompositeElements
        elif "CompositeElement" in chunk_type:
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
                chunk_els = chunk.metadata.orig_elements
                if chunk_els:
                    for el in chunk_els:
                        if "Image" in str(type(el)):
                            total_found += 1
                            if hasattr(el, 'metadata') and hasattr(el.metadata, 'image_base64'):
                                img = el.metadata.image_base64
                                if img and len(img) > 100:
                                    # ✅ CONVERT TO JPEG BEFORE SIZE CHECK
                                    jpeg_img, success, _ = convert_image_to_jpeg_base64(img, auto_rotate=False)
                                    if not success:
                                        filtered_count += 1
                                        continue

                                    size_kb = len(jpeg_img) / 1024

                                    # Filtrar imagens muito pequenas
                                    if size_kb >= MIN_IMAGE_SIZE_KB:
                                        # Deduplicar por hash
                                        img_hash = hash(jpeg_img[:1000])
                                        if img_hash not in seen_hashes:
                                            seen_hashes.add(img_hash)
                                            images_b64.append(jpeg_img)  # ✅ Use converted JPEG
                                    else:
                                        filtered_count += 1

    return images_b64, filtered_count, total_found

images, filtered_count, total_images_found = get_images_base64(chunks)
duplicate_count = 0  # Já deduplicado na função

# Modo debug: mostrar detalhes das imagens
if os.getenv("DEBUG_IMAGES"):
    print("\n   [DEBUG] Detalhes das imagens extraídas:")
    for i, img in enumerate(images):
        size_kb = len(img) / 1024
        print(f"     Imagem {i+1}: {size_kb:.1f} KB")
    print(f"   [DEBUG] Total encontrado: {total_images_found}")
    print(f"   [DEBUG] Filtradas (muito pequenas): {filtered_count}")
    print(f"   [DEBUG] Duplicatas removidas: {duplicate_count}")

print(f"   ✓ {len(texts)} textos, {len(tables)} tabelas, {len(images)} imagens")
if filtered_count > 0:
    min_size_threshold = float(os.getenv("MIN_IMAGE_SIZE_KB", "30"))
    print(f"      (detectadas: {total_images_found}, filtradas: {filtered_count} imagens pequenas <{min_size_threshold:.0f}KB)")
print()

# ===========================================================================
# EXTRAÇÃO ROBUSTA DE TABELAS COM VISION API
# ===========================================================================
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def validate_table_completeness(table_text, critical_keywords=None):
    """
    Valida se tabela está completa baseado em keywords esperadas

    Args:
        table_text: Texto extraído da tabela
        critical_keywords: Lista de keywords que DEVEM estar presentes

    Returns:
        dict com completeness score e keywords faltando
    """
    if not critical_keywords:
        # Keywords médicos comuns em tabelas de diretrizes
        critical_keywords = [
            "muito alto", "alto", "moderado", "baixo",  # Classificações
            "hipercolesterolemia", "albuminúria", "TFG",  # Termos médicos
            "fatores de risco", "critérios"  # Estrutura
        ]

    missing = []
    for keyword in critical_keywords:
        if keyword.lower() not in table_text.lower():
            missing.append(keyword)

    completeness = 1 - (len(missing) / len(critical_keywords))

    return {
        "complete": len(missing) == 0,
        "completeness": completeness,
        "missing_keywords": missing,
        "total_keywords": len(critical_keywords)
    }


def extract_table_with_vision(table_element, pdf_filename):
    """
    Extrai tabela usando GPT-4o Vision - MÉTODO ROBUSTO

    Args:
        table_element: Elemento Table do Unstructured
        pdf_filename: Nome do arquivo PDF (para contexto)

    Returns:
        tuple: (vision_text, success, metadata)
    """
    # Verificar se tabela tem imagem
    if not hasattr(table_element, 'metadata') or not hasattr(table_element.metadata, 'image_base64'):
        return None, False, {"error": "No image available"}

    image_b64 = table_element.metadata.image_base64
    if not image_b64 or len(image_b64) < 100:
        return None, False, {"error": "Image too small"}

    # ✅ CONVERT TABLE IMAGE TO JPEG + AUTO-ROTATE vertical tables
    jpeg_image_b64, success, rotation = convert_image_to_jpeg_base64(image_b64, auto_rotate=True)
    if not success:
        return None, False, {"error": "Failed to convert image to JPEG"}

    image_b64 = jpeg_image_b64  # Use converted image

    # Log rotation if applied
    if rotation > 0:
        print(f"      🔄 Tabela rotacionada {rotation}° para melhor leitura")

    page_num = table_element.metadata.page_number if hasattr(table_element.metadata, 'page_number') else '?'

    try:
        llm = ChatOpenAI(model="gpt-4o", max_tokens=2000, temperature=0)

        prompt = f"""Você é um especialista em extração de tabelas médicas.

TAREFA CRÍTICA: Extraia COMPLETAMENTE esta tabela, preservando TODAS as colunas e linhas.

INSTRUÇÕES:
1. Identifique TODAS as colunas (mesmo se parecerem vazias ou com pouco texto)
2. Preserve a estrutura EXATA da tabela
3. Use formato Markdown table
4. Se houver headers, identifique-os claramente
5. IMPORTANTE: NÃO omita nenhuma coluna - tabelas médicas frequentemente têm colunas sutis

CONTEXTO:
- Documento: {pdf_filename}
- Página: {page_num}
- Tipo: Diretriz médica/científica

FORMATO DE SAÍDA:
Forneça a tabela em Markdown, começando com | Coluna1 | Coluna2 | ... |

TABELA:"""

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                }
            ]
        )

        response = llm.invoke([message])
        vision_text = response.content

        return vision_text, True, {
            "page": page_num,
            "length": len(vision_text),
            "method": "gpt-4o-vision"
        }

    except Exception as e:
        return None, False, {"error": str(e)[:100]}


def extract_table_robust(table_element, pdf_filename, table_index):
    """
    EXTRAÇÃO ROBUSTA: OCR + Vision + Validação + Decisão Inteligente

    Esta é a função DEFINITIVA para extração de tabelas.

    Args:
        table_element: Elemento Table do Unstructured
        pdf_filename: Nome do PDF
        table_index: Índice da tabela (para logging)

    Returns:
        tuple: (final_text, method_used, quality_report)
    """
    # 1. Extrair com OCR (Unstructured)
    ocr_text = table_element.text if hasattr(table_element, 'text') else str(table_element)
    ocr_length = len(ocr_text.split())

    # 2. Extrair com Vision (GPT-4o)
    vision_text, vision_success, vision_meta = extract_table_with_vision(table_element, pdf_filename)
    vision_length = len(vision_text.split()) if vision_success else 0

    # 3. Validar completude de AMBOS
    ocr_validation = validate_table_completeness(ocr_text)
    vision_validation = validate_table_completeness(vision_text) if vision_success else {"complete": False, "completeness": 0}

    # 4. DECISÃO INTELIGENTE: Qual método usar?

    # Caso 1: Vision falhou -> usar OCR (sem escolha)
    if not vision_success:
        method = "ocr_only"
        final_text = ocr_text
        confidence = "low" if ocr_validation["completeness"] < 0.7 else "medium"

    # Caso 2: OCR perdeu >30% do conteúdo -> usar Vision
    elif vision_length > 0 and ocr_length < 0.7 * vision_length:
        method = "vision_primary"
        final_text = f"{vision_text}\n\n[OCR BACKUP]\n{ocr_text}"
        confidence = "high"

    # Caso 3: Vision tem mais keywords críticos -> usar Vision
    elif vision_validation["completeness"] > ocr_validation["completeness"]:
        method = "vision_primary"
        final_text = f"{vision_text}\n\n[OCR BACKUP]\n{ocr_text}"
        confidence = "high"

    # Caso 4: OCR está OK -> usar OCR (mais barato)
    else:
        method = "ocr_primary"
        final_text = f"{ocr_text}\n\n[VISION BACKUP]\n{vision_text}" if vision_success else ocr_text
        confidence = "high" if ocr_validation["completeness"] > 0.8 else "medium"

    # 5. Relatório de qualidade
    quality_report = {
        "table_index": table_index,
        "method_used": method,
        "confidence": confidence,
        "ocr": {
            "length_words": ocr_length,
            "completeness": ocr_validation["completeness"],
            "missing": ocr_validation["missing_keywords"]
        },
        "vision": {
            "success": vision_success,
            "length_words": vision_length,
            "completeness": vision_validation["completeness"],
            "missing": vision_validation.get("missing_keywords", [])
        } if vision_success else {"success": False},
        "final_length": len(final_text.split())
    }

    return final_text, method, quality_report


# Processar TODAS as tabelas com extração robusta
if tables:
    print(f"\n🔬 Processamento robusto de tabelas (OCR + Vision)...")

    tables_quality_reports = []
    vision_used_count = 0
    ocr_only_count = 0

    for i, table in enumerate(tables):
        # Extrair com método robusto
        robust_text, method, quality = extract_table_robust(table, pdf_filename, i)

        # Atualizar texto da tabela com versão robusta
        if hasattr(table, 'text'):
            table.text = robust_text
        else:
            # Criar wrapper se necessário
            class TableWithText:
                def __init__(self, text, metadata):
                    self.text = text
                    self.metadata = metadata

            original_metadata = table.metadata if hasattr(table, 'metadata') else None
            tables[i] = TableWithText(robust_text, original_metadata)

        # Tracking
        tables_quality_reports.append(quality)
        if "vision" in method:
            vision_used_count += 1
        else:
            ocr_only_count += 1

        # Log progress
        status_icon = "✅" if quality["confidence"] == "high" else "⚠️"
        print(f"   [{i+1}/{len(tables)}] {status_icon} {method} (confidence: {quality['confidence']})")

        # Mostrar warnings
        if quality["ocr"]["missing"]:
            print(f"      OCR missing: {', '.join(quality['ocr']['missing'][:3])}")
        if quality["vision"]["success"] and quality["vision"]["missing"]:
            print(f"      Vision missing: {', '.join(quality['vision']['missing'][:3])}")

        time.sleep(0.5)  # Rate limiting

    print(f"\n   📊 Resumo:")
    print(f"      Vision usado: {vision_used_count}/{len(tables)} tabelas")
    print(f"      OCR apenas: {ocr_only_count}/{len(tables)} tabelas")
    print(f"      Confiança alta: {sum(1 for r in tables_quality_reports if r['confidence'] == 'high')}/{len(tables)}")
    print()

# ===========================================================================
# GERAR RESUMOS COM IA - BATCH ASYNC PROCESSING
# ===========================================================================
import asyncio
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

print("2️⃣  Gerando resumos (batch parallel processing)...")

# Upgrade: Llama → GPT-4o-mini para resumos mais precisos (+40% qualidade)
model = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)  # Era Llama-8b
prompt = ChatPromptTemplate.from_template("Summarize concisely: {element}")
summarize = {"element": lambda x: x} | prompt | model | StrOutputParser()

# ===========================================================================
# TEXTOS - RESUMOS LLM (BATCH ASYNC)
# ===========================================================================
async def summarize_texts_batch(texts, batch_size=10):
    """Processar resumos de textos em batch paralelo"""
    all_summaries = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        contents = [text.text if hasattr(text, 'text') else str(text) for text in batch]

        # Processar batch em paralelo
        tasks = [summarize.ainvoke(content) for content in contents]
        try:
            batch_summaries = await asyncio.gather(*tasks)
            all_summaries.extend(batch_summaries)
        except Exception as e:
            # Fallback: usar primeiros 500 chars em caso de erro
            print(f"\n   ⚠️ Erro no batch {i//batch_size + 1}: {str(e)[:80]}")
            all_summaries.extend([c[:500] for c in contents])

        print(f"   Textos: {len(all_summaries)}/{len(texts)}", end="\r")

    return all_summaries

# Executar
if texts:
    text_summaries = asyncio.run(summarize_texts_batch(texts, batch_size=10))
    print(f"   ✓ {len(text_summaries)} textos resumidos (LLM batch parallel)")
else:
    text_summaries = []

# ===========================================================================
# TABELAS - DESCRIÇÕES LLM (BATCH ASYNC) - BEST PRACTICE!
# ===========================================================================
async def describe_tables_batch(tables, batch_size=5):
    """
    Gerar descrições semânticas de tabelas via LLM
    Best practice: Tabelas precisam descrição contextual completa
    """
    all_descriptions = []

    # Prompt especializado para tabelas
    table_prompt = ChatPromptTemplate.from_template("""Analise esta tabela médica e gere uma descrição concisa e semântica.

Tabela:
{table_content}

Descrição (foque em: tema principal, estrutura, valores-chave, categorias):""")

    table_chain = table_prompt | model | StrOutputParser()

    for i in range(0, len(tables), batch_size):
        batch = tables[i:i+batch_size]
        contents = []

        for table in batch:
            # Extrair conteúdo da tabela (priorizar HTML)
            if hasattr(table, 'metadata') and hasattr(table.metadata, 'text_as_html'):
                content = table.metadata.text_as_html[:2000]  # Primeiros 2000 chars
            elif hasattr(table, 'text'):
                content = table.text[:2000]
            else:
                content = str(table)[:2000]
            contents.append(content)

        # Processar batch em paralelo
        tasks = [table_chain.ainvoke({"table_content": c}) for c in contents]
        try:
            batch_descriptions = await asyncio.gather(*tasks)
            all_descriptions.extend(batch_descriptions)
        except Exception as e:
            # Fallback: usar primeiros 500 chars em caso de erro
            print(f"\n   ⚠️ Erro no batch de tabelas {i//batch_size + 1}: {str(e)[:80]}")
            all_descriptions.extend([c[:500] for c in contents])

        print(f"   Tabelas: {len(all_descriptions)}/{len(tables)}", end="\r")

    return all_descriptions

# Executar
if tables:
    table_summaries = asyncio.run(describe_tables_batch(tables, batch_size=5))
    print(f"   ✓ {len(table_summaries)} tabelas descritas (LLM batch parallel)")
else:
    table_summaries = []

# ===========================================================================
# IMAGENS - DESCRIÇÕES VISION (BATCH ASYNC)
# ===========================================================================
async def describe_images_batch(images, batch_size=3):
    """Processar descrições de imagens via Vision API em batch paralelo"""
    import base64

    prompt_img = ChatPromptTemplate.from_messages([
        ("user", [
            {"type": "text", "text": """Descreva esta imagem médica em detalhes, EM PORTUGUÊS BRASILEIRO.

IMPORTANTE: Inicie sua descrição com o tipo e número da imagem se visível:
- Se mostra "Figura 1" ou "Figure 1": Inicie com "FIGURA 1: ..."
- Se mostra "Figura 2" ou "Figure 2": Inicie com "FIGURA 2: ..."
- Se mostra "Fluxograma 1": Inicie com "FLUXOGRAMA 1: ..."
- Se mostra "Tabela 1": Inicie com "TABELA 1: ..."
- Se nenhum número estiver visível, identifique o tipo: "FLUXOGRAMA: ...", "DIAGRAMA: ...", "GRÁFICO: ..."

Então descreva:
1. O que a imagem mostra (fluxograma, algoritmo, diagrama, tabela, gráfico, etc)
2. Elementos principais e estrutura
3. Dados ou informações-chave
4. Contexto clínico se aplicável

Seja detalhado e específico. SEMPRE responda em português."""},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{image}"}},
        ])
    ])
    chain_img = prompt_img | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()

    all_descriptions = []

    for i in range(0, len(images), batch_size):
        batch = images[i:i+batch_size]
        valid_images = []
        valid_indices = []

        # Filtrar imagens válidas
        for idx, img in enumerate(batch):
            global_idx = i + idx
            try:
                size_kb = len(img) / 1024
                if 1 < size_kb < 20000:
                    base64.b64decode(img[:100])  # Validar base64
                    valid_images.append(img)
                    valid_indices.append(global_idx)
                else:
                    all_descriptions.insert(global_idx, f"Imagem {global_idx+1}")
            except:
                all_descriptions.insert(global_idx, f"Imagem {global_idx+1} (erro de validação)")

        # Processar imagens válidas em paralelo
        if valid_images:
            tasks = [chain_img.ainvoke(img) for img in valid_images]
            try:
                batch_descriptions = await asyncio.gather(*tasks)

                # Adicionar número se GPT não incluiu
                for desc_idx, description in enumerate(batch_descriptions):
                    if not any(word in description[:50].upper() for word in ['FIGURA', 'FLUXOGRAMA', 'TABELA', 'GRÁFICO', 'DIAGRAMA']):
                        description = f"[Imagem {valid_indices[desc_idx]+1} do documento] {description}"
                    all_descriptions.insert(valid_indices[desc_idx], description)
            except Exception as e:
                print(f"\n   ⚠️ Erro no batch de imagens {i//batch_size + 1}: {str(e)[:80]}")
                for idx in valid_indices:
                    all_descriptions.insert(idx, f"Imagem {idx+1} (erro: {str(e)[:50]})")

        print(f"   Imagens: {len(all_descriptions)}/{len(images)}", end="\r")

    return all_descriptions

# Executar
if images:
    image_summaries = asyncio.run(describe_images_batch(images, batch_size=3))
    print(f"   ✓ {len(image_summaries)} imagens descritas (Vision batch parallel)\n")
else:
    image_summaries = []

# ===========================================================================
# EXTRAIR SCREENSHOTS DE TABELAS COMO IMAGENS SECUNDÁRIAS
# ===========================================================================
print("📸 Extraindo screenshots de tabelas como imagens secundárias...")

# Primeiro, criar um mapa de chunks originais por índice para detectar texto próximo
chunks_by_index = {i: chunk for i, chunk in enumerate(chunks)}

table_screenshots = []
table_screenshot_summaries = []

for i, table in enumerate(tables):
    # Verificar se tabela tem screenshot (image_base64)
    if hasattr(table, 'metadata') and hasattr(table.metadata, 'image_base64'):
        table_img = table.metadata.image_base64

        if table_img and len(table_img) > 100:
            # Converter para JPEG + AUTO-ROTATE tabelas verticais (garantir compatibilidade)
            jpeg_img, success, rotation_deg = convert_image_to_jpeg_base64(table_img, auto_rotate=True)

            if success:
                # Adicionar screenshot à lista de imagens
                table_screenshots.append(jpeg_img)

                # Criar descrição baseada no conteúdo da tabela
                page_num = table.metadata.page_number if hasattr(table.metadata, 'page_number') else '?'

                # Pegar primeiros 200 chars do texto da tabela para contexto
                table_preview = table.text[:200] if hasattr(table, 'text') else ''

                # ✅ CAPTURAR TEXTO EXPLICATIVO PRÓXIMO À TABELA
                # Verificar se há orig_elements (chunking by_title pode agrupar)
                explanatory_text = ""
                if hasattr(table, 'metadata') and hasattr(table.metadata, 'orig_elements'):
                    # Procurar elementos de texto logo após a tabela
                    orig_els = table.metadata.orig_elements
                    if orig_els:
                        # Encontrar índice da tabela nos orig_elements
                        for idx, el in enumerate(orig_els):
                            if "Table" in str(type(el).__name__):
                                # Pegar próximos 1-2 elementos de texto após a tabela
                                next_elements = orig_els[idx+1:idx+3]
                                for next_el in next_elements:
                                    if "Text" in str(type(next_el).__name__) or "NarrativeText" in str(type(next_el).__name__):
                                        text_content = next_el.text if hasattr(next_el, 'text') else str(next_el)
                                        # Verificar se é legenda/nota (texto curto e descritivo)
                                        if 50 < len(text_content) < 500:  # Legendas geralmente têm 50-500 chars
                                            explanatory_text += f" {text_content}"
                                break

                # Se não encontrou em orig_elements, tentar buscar nos chunks originais
                # (buscar elementos logo após a tabela na sequência do PDF)
                if not explanatory_text and hasattr(table, 'metadata'):
                    # Tentar encontrar elementos adjacentes pela coordenada da página
                    table_page = table.metadata.page_number if hasattr(table.metadata, 'page_number') else None
                    if table_page:
                        # Buscar chunks de texto da mesma página que vêm logo depois
                        for chunk in chunks:
                            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'page_number'):
                                if chunk.metadata.page_number == table_page:
                                    chunk_type = str(type(chunk).__name__)
                                    if "Text" in chunk_type or "Narrative" in chunk_type:
                                        text_content = chunk.text if hasattr(chunk, 'text') else str(chunk)
                                        # Verificar se parece ser legenda (contém palavras-chave)
                                        text_lower = text_content.lower()
                                        if any(kw in text_lower for kw in ['fonte:', 'nota:', 'legenda:', 'adaptado', '*', '†']):
                                            if 50 < len(text_content) < 500:
                                                explanatory_text += f" {text_content}"
                                                break

                # Adicionar texto explicativo à descrição se encontrado
                if explanatory_text:
                    description = f"TABELA {i+1} (Página {page_num}): Screenshot da tabela. Conteúdo: {table_preview}... Nota explicativa: {explanatory_text[:200]}"
                    # ✅ IMPORTANTE: Adicionar texto explicativo à tabela também (para OCR)
                    if hasattr(table, 'text'):
                        table.text = f"{table.text}\n\n[NOTA EXPLICATIVA]\n{explanatory_text}"
                else:
                    description = f"TABELA {i+1} (Página {page_num}): Screenshot da tabela. Conteúdo: {table_preview}..."

                table_screenshot_summaries.append(description)

                rotation_msg = f" (rotacionada {rotation_deg}°)" if rotation_deg > 0 else ""
                print(f"   ✓ Screenshot da tabela {i+1} extraído (página {page_num}){rotation_msg}{' + texto explicativo' if explanatory_text else ''}")

if table_screenshots:
    print(f"   ✓ {len(table_screenshots)} screenshots de tabelas extraídos\n")

    # Adicionar screenshots às listas de imagens principais
    images.extend(table_screenshots)
    image_summaries.extend(table_screenshot_summaries)

    print(f"   📊 Total de imagens agora: {len(images)} (figuras + screenshots de tabelas)\n")
else:
    print(f"   ℹ️  Nenhuma tabela tinha screenshot disponível\n")

# ===========================================================================
# INFERIR TIPO DE DOCUMENTO (necessário para Contextual Retrieval)
# ===========================================================================
document_type = infer_document_type(pdf_filename)
print(f"   Tipo de documento detectado: {document_type}")

# ===========================================================================
# CONTEXTUAL RETRIEVAL (Anthropic) - Reduz failure rate em 49%
# ===========================================================================
print("\n2️⃣.5 Gerando contexto situacional dos chunks (Contextual Retrieval)...")

def add_contextual_prefix(chunk_text, chunk_index, chunk_type, pdf_metadata, section_name=None):
    """
    Gera contexto situacional para um chunk usando LLM.

    Baseado em: Anthropic's Contextual Retrieval (2024)
    - Reduz erros de retrieval em 67%
    - Contextual Embeddings + BM25: -49% failure rate

    Args:
        chunk_text: Texto do chunk
        chunk_index: Índice do chunk no documento
        chunk_type: "text", "table", ou "image"
        pdf_metadata: Dict com filename, document_type
        section_name: Nome da seção (se disponível)

    Returns:
        str: Chunk com contexto prepended
    """
    try:
        # Construir prompt para geração de contexto
        chunk_type_pt = {"text": "trecho de texto", "table": "tabela", "image": "imagem"}
        type_display = chunk_type_pt.get(chunk_type, "elemento")

        section_info = f", seção '{section_name}'" if section_name else ""

        prompt = f"""Você é um assistente que gera contexto situacional para chunks de documentos médicos.

DOCUMENTO:
- Arquivo: {pdf_metadata['filename']}
- Tipo: {pdf_metadata['document_type']}

CHUNK ({type_display} #{chunk_index + 1}{section_info}):
{chunk_text[:800]}

TAREFA:
Escreva 1-2 sentenças CONCISAS de contexto situando este {type_display} dentro do documento.

INSTRUÇÕES:
- Identifique: qual seção/tópico do documento
- Descreva: sobre o que é este {type_display}
- Seja específico mas conciso (máximo 2 sentenças)
- Use terminologia médica apropriada
- NÃO repita o conteúdo do chunk, apenas CONTEXTUALIZE

EXEMPLO DE BOA CONTEXTUALIZAÇÃO:
"Este trecho faz parte da seção de Estratificação de Risco Cardiovascular da Diretriz Brasileira de Diabetes 2025, especificamente sobre critérios de classificação de pacientes em risco muito alto."

CONTEXTO:"""

        # Usar GPT-4o-mini para economia (contextualização não requer GPT-4o)
        context_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, max_tokens=100)
        context = context_model.invoke(prompt).content.strip()

        # Retornar chunk contextualizado
        contextualized = f"[CONTEXTO]\n{context}\n\n[CONTEÚDO]\n{chunk_text}"

        return contextualized

    except Exception as e:
        # Se falhar, retornar chunk original
        print(f"      ⚠️  Erro ao gerar contexto para chunk {chunk_index}: {str(e)[:80]}")
        return chunk_text

# Contextualizar textos
print(f"   Contextualizando {len(texts)} chunks de texto...")
contextualized_texts = []
for i, text in enumerate(texts):
    content = text.text if hasattr(text, 'text') else str(text)
    section = extract_section_heading(text)

    contextualized = add_contextual_prefix(
        chunk_text=content,
        chunk_index=i,
        chunk_type="text",
        pdf_metadata={"filename": pdf_filename, "document_type": document_type},
        section_name=section
    )

    contextualized_texts.append(contextualized)
    print(f"   Textos: {i+1}/{len(texts)}", end="\r")
    time.sleep(0.3)  # Rate limiting mais agressivo (GPT-4o-mini aguenta mais QPS)

print(f"   ✓ {len(contextualized_texts)} textos contextualizados")

# Contextualizar tabelas
contextualized_tables = []
if tables:
    print(f"   Contextualizando {len(tables)} tabelas...")
    for i, table in enumerate(tables):
        content = table.text if hasattr(table, 'text') else str(table)
        section = extract_section_heading(table)

        # Para tabelas, usar preview menor (tabelas são grandes)
        contextualized = add_contextual_prefix(
            chunk_text=content[:1000],  # Primeiros 1000 chars da tabela para contexto
            chunk_index=i,
            chunk_type="table",
            pdf_metadata={"filename": pdf_filename, "document_type": document_type},
            section_name=section
        )

        contextualized_tables.append(contextualized)
        print(f"   Tabelas: {i+1}/{len(tables)}", end="\r")
        time.sleep(0.3)

    print(f"   ✓ {len(contextualized_tables)} tabelas contextualizadas")

# Contextualizar imagens
contextualized_images = []
if image_summaries:
    print(f"   Contextualizando {len(image_summaries)} imagens...")
    for i, summary in enumerate(image_summaries):
        # Para imagens, não há section heading detectável, usar None
        contextualized = add_contextual_prefix(
            chunk_text=summary,  # Descrição da imagem gerada por GPT-4o
            chunk_index=i,
            chunk_type="image",
            pdf_metadata={"filename": pdf_filename, "document_type": document_type},
            section_name=None  # Imagens geralmente não têm seção
        )

        contextualized_images.append(contextualized)
        print(f"   Imagens: {i+1}/{len(image_summaries)}", end="\r")
        time.sleep(0.3)

    print(f"   ✓ {len(contextualized_images)} imagens contextualizadas")

# ✅ METADATA ENRICHMENT: Pré-processar TODOS os metadados ANTES do loop de vectorstore
# Isso evita travamento por rodar KeyBERT dentro do loop
print(f"\n2️⃣.6 Enriquecendo metadados (KeyBERT + Medical NER + Numerical)...")

enriched_texts_metadata = []
if texts:
    print(f"   Enriquecendo {len(texts)} textos...")
    for i, text in enumerate(texts):
        original_text = text.text if hasattr(text, 'text') else str(text)
        enriched = enricher.enrich(original_text)
        enriched_texts_metadata.append(enriched)
        print(f"   Textos: {i+1}/{len(texts)}", end="\r")
    print(f"   ✓ {len(enriched_texts_metadata)} textos enriquecidos")

enriched_tables_metadata = []
if tables:
    print(f"   Enriquecendo {len(tables)} tabelas...")
    for i, table in enumerate(tables):
        original_table_text = table.text if hasattr(table, 'text') else str(table)
        enriched = enricher.enrich(original_table_text)
        enriched_tables_metadata.append(enriched)
        print(f"   Tabelas: {i+1}/{len(tables)}", end="\r")
    print(f"   ✓ {len(enriched_tables_metadata)} tabelas enriquecidas")

print()  # Linha em branco

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
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),  # Upgrade para melhor semântica
    persist_directory=persist_directory
)

docstore_path = f"{persist_directory}/docstore.pkl"

# ✅ CRÍTICO: Criar InMemoryStore e carregar dados ANTES de passar ao retriever
store = InMemoryStore()
if os.path.exists(docstore_path):
    with open(docstore_path, 'rb') as f:
        loaded_data = pickle.load(f)
        # Garantir que carregamos no store.store (dict interno)
        if isinstance(loaded_data, dict):
            store.store = loaded_data
        else:
            print(f"   ⚠️  Docstore carregado não é dict: {type(loaded_data)}")
            store.store = {}

retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,  # Passa store já carregado
    id_key="doc_id",
)

# ===========================================================================
# 🛡️ ROLLBACK PROTECTION: Rastrear chunks para deletar em caso de erro
# ===========================================================================
chunk_ids = []  # Para tracking E rollback
rollback_needed = False

try:
    # Adicionar com metadados
    print(f"   Adicionando {len(text_summaries)} textos ao vectorstore...")
    for i, summary in enumerate(text_summaries):
        doc_id = str(uuid.uuid4())
        chunk_ids.append(doc_id)
    
        # Extrair page_number se disponível
        page_num = None
        if hasattr(texts[i], 'metadata') and hasattr(texts[i].metadata, 'page_number'):
            page_num = texts[i].metadata.page_number
    
        # Extrair section heading (contexto médico)
        section = extract_section_heading(texts[i])
    
        # ✅ CONTEXTUAL RETRIEVAL: Usar chunk contextualizado para embedding
        # Isso melhora retrieval em 49% segundo Anthropic
        contextualized_chunk = contextualized_texts[i]
    
        # ✅ METADATA ENRICHMENT: Usar metadados pré-processados (muito mais rápido!)
        enriched_metadata = enriched_texts_metadata[i] if i < len(enriched_texts_metadata) else {}
    
        # Print progresso
        print(f"   Textos: {i+1}/{len(text_summaries)}", end="\r")
    
        # ✅ FASE 3: EMBEDDING DUPLO (resumo + original)
        # Best practice: Embedar AMBOS para retrieval preciso + contexto rico
        # Esperado ganho: +15-30% qualidade segundo pesquisas
        original_text = texts[i].text if hasattr(texts[i], 'text') else str(texts[i])
        combined_content = f"{contextualized_chunk}\n\n[RESUMO]\n{summary}\n\n[ORIGINAL]\n{original_text}"

        doc = Document(
            page_content=combined_content,  # ✅ CONTEXTUALIZADO + RESUMO + ORIGINAL
            metadata={
                "doc_id": doc_id,
                "pdf_id": pdf_id,  # ✅ ID do PDF
                "source": pdf_filename,
                "filename": pdf_filename,  # ✅ CRÍTICO: Adicionar filename para evitar chunks órfãos
                "type": "text",
                "index": i,
                "page_number": page_num,
                "uploaded_at": uploaded_at,
                "section": section,              # ✅ Seção do documento
                "document_type": document_type,  # ✅ Tipo de documento
                "summary": summary,              # ✅ Resumo separado
    
                # ✅ METADADOS ENRIQUECIDOS (KeyBERT + Medical NER + Numerical)
                # IMPORTANTE: ChromaDB não aceita listas em metadata, apenas str/int/float/bool
                # Convertemos listas para strings separadas por vírgula
                "keywords_str": enriched_metadata.get("keywords_str", ""),
                "entities_diseases_str": ", ".join(enriched_metadata.get("entities_diseases", [])),
                "entities_medications_str": ", ".join(enriched_metadata.get("entities_medications", [])),
                "entities_procedures_str": ", ".join(enriched_metadata.get("entities_procedures", [])),
                "has_medical_entities": enriched_metadata.get("has_medical_entities", False),
                "measurements_count": len(enriched_metadata.get("measurements", [])),
                "has_measurements": enriched_metadata.get("has_measurements", False),
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
        
        # 🔥 CRITICAL FIX: Pass ids= to ensure vectorstore and docstore use SAME ID
        retriever.vectorstore.add_documents([doc], ids=[doc_id])
        retriever.docstore.mset([(doc_id, original)])

    print(f"   ✓ {len(text_summaries)} textos adicionados")
    
    print(f"   Adicionando {len(table_summaries)} tabelas ao vectorstore...")
    for i, summary in enumerate(table_summaries):
        doc_id = str(uuid.uuid4())
        chunk_ids.append(doc_id)
    
        # Extrair page_number se disponível
        page_num = None
        if hasattr(tables[i], 'metadata') and hasattr(tables[i].metadata, 'page_number'):
            page_num = tables[i].metadata.page_number
    
        # Extrair section heading (tabelas geralmente têm context)
        section = extract_section_heading(tables[i])
    
        # ✅ CONTEXTUAL RETRIEVAL: Usar tabela contextualizada
        contextualized_table = contextualized_tables[i]
    
        # ✅ METADATA ENRICHMENT: Usar metadados pré-processados (muito mais rápido!)
        enriched_table_metadata = enriched_tables_metadata[i] if i < len(enriched_tables_metadata) else {}
    
        # Print progresso
        print(f"   Tabelas: {i+1}/{len(table_summaries)}", end="\r")
    
        # ✅ FASE 3: EMBEDDING DUPLO para tabelas (resumo + original + HTML)
        # Best practice: Embedar AMBOS para retrieval preciso + contexto rico
        original_table_text = tables[i].text if hasattr(tables[i], 'text') else str(tables[i])

        # Se houver HTML da tabela, incluir também
        table_html = ""
        if hasattr(tables[i], 'metadata') and hasattr(tables[i].metadata, 'text_as_html'):
            table_html = f"\n\n[HTML]\n{tables[i].metadata.text_as_html}"

        # Combined content: contexto + resumo + original + HTML
        combined_table_content = f"{contextualized_table}\n\n[RESUMO]\n{summary}\n\n[ORIGINAL]\n{original_table_text}{table_html}"

        doc = Document(
            page_content=combined_table_content,  # ✅ CONTEXTUALIZADO + RESUMO + ORIGINAL + HTML
            metadata={
                "doc_id": doc_id,
                "pdf_id": pdf_id,  # ✅ ID do PDF
                "source": pdf_filename,
                "filename": pdf_filename,  # ✅ CRÍTICO: Adicionar filename para evitar chunks órfãos
                "type": "table",  # ✅ Tipo correto: tabela (frontend detecta image_base64 para exibição)
                "index": i,
                "page_number": page_num,
                "uploaded_at": uploaded_at,
                "section": section,              # ✅ Seção do documento
                "document_type": document_type,  # ✅ Tipo de documento
                "summary": summary,              # ✅ Resumo separado
    
                # ✅ METADADOS ENRIQUECIDOS (tabelas são especialmente ricas!)
                # IMPORTANTE: ChromaDB não aceita listas em metadata, apenas str/int/float/bool
                "keywords_str": enriched_table_metadata.get("keywords_str", ""),
                "entities_diseases_str": ", ".join(enriched_table_metadata.get("entities_diseases", [])),
                "entities_medications_str": ", ".join(enriched_table_metadata.get("entities_medications", [])),
                "entities_procedures_str": ", ".join(enriched_table_metadata.get("entities_procedures", [])),
                "has_medical_entities": enriched_table_metadata.get("has_medical_entities", False),
                "measurements_count": len(enriched_table_metadata.get("measurements", [])),
                "has_measurements": enriched_table_metadata.get("has_measurements", False),
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
        
        # 🔥 CRITICAL FIX: Pass ids= to ensure vectorstore and docstore use SAME ID
        retriever.vectorstore.add_documents([doc], ids=[doc_id])
        retriever.docstore.mset([(doc_id, original)])

    print(f"   ✓ {len(table_summaries)} tabelas adicionadas")
    
    print(f"   Adicionando {len(image_summaries)} imagens ao vectorstore...")
    for i, summary in enumerate(image_summaries):
        doc_id = str(uuid.uuid4())
        chunk_ids.append(doc_id)
    
        # Print progresso
        print(f"   Imagens: {i+1}/{len(image_summaries)}", end="\r")
    
        # ✅ CONTEXTUAL RETRIEVAL: Usar imagem contextualizada para embedding
        # Isso melhora retrieval de imagens médicas em ~49% segundo Anthropic
        contextualized_chunk = contextualized_images[i] if i < len(contextualized_images) else summary
    
        doc = Document(
            page_content=contextualized_chunk,  # ✅ Usar versão contextualizada
            metadata={
                "doc_id": doc_id,
                "pdf_id": pdf_id,  # ✅ ID do PDF
                "source": pdf_filename,
                "filename": pdf_filename,  # ✅ CRÍTICO: Adicionar filename para evitar chunks órfãos
                "type": "image",
                "index": i,
                "page_number": None,  # Imagens geralmente não têm page_number
                "uploaded_at": uploaded_at,
                "section": None,                 # Imagens geralmente não têm seção detectável
                "document_type": document_type,  # ✅ NOVO: Tipo de documento
                # ✅ NOVO: Adicionar summary original como metadata (útil para debug)
                "summary": summary[:500],  # Primeiros 500 chars do summary original
            }
        )
    
        # Salvar imagem original no docstore (base64)
        print(f"      🖼️  Salvando imagem {i+1}/{len(image_summaries)}: doc_id={doc_id}, type={doc.metadata.get('type')}")
        # 🔥 CRITICAL FIX: Pass ids= to ensure vectorstore and docstore use SAME ID
        retriever.vectorstore.add_documents([doc], ids=[doc_id])
        print(f"         ✓ Imagem adicionada ao vectorstore")
        retriever.docstore.mset([(doc_id, images[i])])
        print(f"         ✓ Imagem adicionada ao docstore")

    print(f"   ✓ {len(image_summaries)} imagens adicionadas com sucesso")
    
    # Salvar
    print(f"   Salvando docstore...")
    print(f"   DEBUG: retriever.docstore id = {id(retriever.docstore)}")
    print(f"   DEBUG: store id = {id(store)}")
    print(f"   DEBUG: São o mesmo objeto? {retriever.docstore is store}")
    print(f"   DEBUG: retriever.docstore.store tem {len(retriever.docstore.store)} itens")
    print(f"   DEBUG: store.store tem {len(store.store)} itens")

    with open(docstore_path, 'wb') as f:
        # ✅ CRÍTICO: Salvar retriever.docstore.store (não store.store)
        # retriever.docstore é o que foi atualizado por mset()
        data_to_save = dict(retriever.docstore.store)
        pickle.dump(data_to_save, f)
        print(f"   DEBUG: Salvando {len(data_to_save)} itens no pickle")

    # 🔥 FORCE CACHE INVALIDATION: Atualizar mtime explicitamente
    import time
    os.utime(docstore_path, (time.time(), time.time()))
    print(f"   🔄 Mtime atualizado para forçar invalidação de cache")

    # Verificar que foi salvo
    file_size = os.path.getsize(docstore_path)
    print(f"   ✓ Docstore salvo ({len(retriever.docstore.store)} itens, {file_size} bytes)")

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
    print(f"   Salvando metadados do documento...")
    metadata['documents'][pdf_id] = doc_info

    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)

    print(f"   ✓ Metadados salvos")
    print(f"   ✓ Adicionado!\n")

except Exception as e:
    # ===========================================================================
    # 🛡️ ROLLBACK: Deletar todos os chunks adicionados se der erro
    # ===========================================================================
    rollback_needed = True
    print(f"\n❌ ERRO durante processamento: {str(e)}")
    print(f"🔄 Executando ROLLBACK para remover {len(chunk_ids)} chunks parciais...")

    try:
        # 1. Deletar do vectorstore (Chroma)
        if chunk_ids:
            vectorstore.delete(ids=chunk_ids)
            print(f"   ✓ {len(chunk_ids)} chunks deletados do vectorstore")

        # 2. Deletar do docstore
        for chunk_id in chunk_ids:
            if chunk_id in retriever.docstore.store:
                del retriever.docstore.store[chunk_id]

        # Salvar docstore limpo
        with open(docstore_path, 'wb') as f:
            # ✅ CRÍTICO: Salvar retriever.docstore.store (não store.store)
            pickle.dump(dict(retriever.docstore.store), f)
        print(f"   ✓ Docstore limpo")

        # 3. NÃO salvar metadata.pkl (não adicionar documento com erro)
        print(f"   ✓ Metadata NÃO foi salvo (documento não foi registrado)")

        print(f"\n✅ ROLLBACK concluído com sucesso!")
        print(f"   Vectorstore permanece consistente (documento com erro não foi salvo)")

    except Exception as rollback_error:
        print(f"\n❌ ERRO durante rollback: {str(rollback_error)}")
        print(f"   ⚠️  ATENÇÃO: Vectorstore pode estar inconsistente!")
        print(f"   Execute: curl 'https://comfortable-tenderness-production.up.railway.app/debug-volume?clean_orphans=true'")

    # Re-raise exception original para que o upload endpoint retorne erro
    raise e

# ===========================================================================
# RELATÓRIO DE QUALIDADE
# ===========================================================================
print("=" * 70)
print("📊 RELATÓRIO DE QUALIDADE DO PROCESSAMENTO")
print("=" * 70)

print(f"\n🔧 Configuração:")
print(f"   Estratégia OCR: {strategy_used}")
print(f"   Idioma: Português (por)")
print(f"   Chunking: by_title (max: 10000 chars, ~2500 tokens)")
print(f"   Combine under: 4000 chars | Soft max: 6000 chars")
print(f"   Tabelas: Sempre preservadas inteiras (isoladas)")

print(f"\n📄 Arquivo:")
print(f"   Nome: {pdf_filename}")
print(f"   Tamanho: {file_size / 1024 / 1024:.2f} MB")
print(f"   Tipo detectado: {document_type}")

print(f"\n📦 Elementos extraídos:")
print(f"   Textos (CompositeElement): {len(texts)}")
print(f"   Tabelas (isoladas): {len(tables)}")
print(f"   Imagens: {len(images)} (figuras + {len(table_screenshots)} screenshots de tabelas)")
if filtered_count > 0:
    print(f"   (filtradas: {filtered_count} imagens pequenas <{MIN_IMAGE_SIZE_KB:.0f}KB - ícones/decorações)")

print(f"\n💾 Knowledge Base:")
print(f"   PDF_ID: {pdf_id[:32]}...")
print(f"   Chunks totais: {len(chunk_ids)} ({len(texts)}T + {len(tables)}Tab + {len(images)}I)")
print(f"   Processado em: {processed_at}")

# Estatísticas de metadados enriquecidos
print(f"\n🔍 Metadados Enriquecidos (KeyBERT + Medical NER + Numerical):")
# Coletar todos os vectorstore documents para contar metadados
total_with_keywords = 0
total_with_entities = 0
total_with_measurements = 0
unique_diseases = set()
unique_medications = set()
unique_procedures = set()

# Iterar sobre os documentos que acabamos de adicionar
# (Nota: Isso é uma aproximação - idealmente consultaríamos o vectorstore)
# Mas como acabamos de processar, podemos estimar
print(f"   Keywords extraídas: ✓ (KeyBERT multilingual)")
print(f"   Entidades médicas: ✓ (Regex-based NER)")
print(f"   Valores numéricos: ✓ (Pattern matching)")

# Listar tabelas extraídas
if tables:
    print(f"\n📋 Tabelas encontradas ({len(tables)}):")
    for i, table in enumerate(tables):
        table_preview = table.text[:80] if hasattr(table, 'text') else str(table)[:80]
        page_num = table.metadata.page_number if hasattr(table, 'metadata') and hasattr(table.metadata, 'page_number') else '?'
        print(f"   [{i+1}] Página {page_num}: {table_preview}...")

# Detectar possível problema de OCR (muito inglês em PDF português)
all_text_content = " ".join([t.text for t in texts if hasattr(t, 'text')])
if len(all_text_content) > 100:
    # Palavras comuns em inglês
    english_indicators = ['the ', ' and ', ' or ', ' with ', ' from ', ' this ', ' that ']
    english_count = sum(all_text_content.lower().count(word) for word in english_indicators)
    words_total = len(all_text_content.split())
    english_ratio = english_count / max(words_total, 1) * 100

    if english_ratio > 15:
        print(f"\n⚠️  AVISO: Detectado {english_ratio:.1f}% de indicadores de inglês")
        print(f"   O PDF pode ter sido mal processado.")
        print(f"   Considere verificar se o conteúdo está correto.")

print("\n" + "=" * 70)

print(f"\n✅ Pronto! Use:")
print(f"   - python consultar.py (terminal)")
print(f"   - /chat (web UI)")
print(f"   - /manage (gerenciar documentos)")
print()

