#!/usr/bin/env python3
"""
DEBUG: Investigar imagens detectadas no PDF
Salva todas as imagens em uma pasta para inspeção visual
"""

import os
import sys
import base64
from dotenv import load_dotenv
from unstructured.partition.pdf import partition_pdf

load_dotenv()

if len(sys.argv) < 2:
    print("Uso: python debug_images_visual.py arquivo.pdf")
    exit(1)

file_path = sys.argv[1]

if not os.path.exists(file_path):
    print(f"❌ PDF não encontrado: {file_path}")
    exit(1)

print("=" * 70)
print("🔍 DEBUG: Análise de Imagens Detectadas")
print("=" * 70)
print(f"\nArquivo: {file_path}\n")

# Criar pasta de output
output_dir = "./debug_images_output"
os.makedirs(output_dir, exist_ok=True)

# Particionar PDF
print("📦 Particionando PDF...")
chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image", "Table"],
    extract_image_block_to_payload=True,
    languages=["por"],
    chunking_strategy="by_title",
    max_characters=10000,
    combine_text_under_n_chars=4000,
    new_after_n_chars=6000,
)

print(f"✅ Total de elementos: {len(chunks)}\n")

# Analisar tipos de elementos
element_types = {}
for chunk in chunks:
    chunk_type = str(type(chunk).__name__)
    element_types[chunk_type] = element_types.get(chunk_type, 0) + 1

print("📊 TIPOS DE ELEMENTOS")
print("=" * 70)
for elem_type, count in sorted(element_types.items()):
    print(f"  {elem_type}: {count}")

# Extrair TODAS as imagens (sem filtros)
print("\n" + "=" * 70)
print("🖼️  EXTRAINDO TODAS AS IMAGENS")
print("=" * 70)

images_data = []
image_count = 0

for chunk_idx, chunk in enumerate(chunks):
    chunk_type = str(type(chunk))

    # CASO 1: Elementos Image de primeira classe
    if "Image" in chunk_type:
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'image_base64'):
            img_b64 = chunk.metadata.image_base64
            if img_b64 and len(img_b64) > 100:
                image_count += 1
                size_kb = len(img_b64) / 1024

                # Extrair metadados
                page_num = chunk.metadata.page_number if hasattr(chunk.metadata, 'page_number') else '?'

                # Tentar obter dimensões se disponível
                width = chunk.metadata.width if hasattr(chunk.metadata, 'width') else '?'
                height = chunk.metadata.height if hasattr(chunk.metadata, 'height') else '?'

                images_data.append({
                    'index': image_count,
                    'source': 'direct_image_element',
                    'chunk_index': chunk_idx,
                    'page': page_num,
                    'size_kb': size_kb,
                    'width': width,
                    'height': height,
                    'base64': img_b64
                })

    # CASO 2: Imagens dentro de CompositeElements
    elif "CompositeElement" in chunk_type:
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            chunk_els = chunk.metadata.orig_elements
            if chunk_els:
                for el_idx, el in enumerate(chunk_els):
                    if "Image" in str(type(el)):
                        if hasattr(el, 'metadata') and hasattr(el.metadata, 'image_base64'):
                            img_b64 = el.metadata.image_base64
                            if img_b64 and len(img_b64) > 100:
                                image_count += 1
                                size_kb = len(img_b64) / 1024

                                # Extrair metadados
                                page_num = el.metadata.page_number if hasattr(el.metadata, 'page_number') else '?'
                                width = el.metadata.width if hasattr(el.metadata, 'width') else '?'
                                height = el.metadata.height if hasattr(el.metadata, 'height') else '?'

                                images_data.append({
                                    'index': image_count,
                                    'source': 'composite_orig_elements',
                                    'chunk_index': chunk_idx,
                                    'element_index': el_idx,
                                    'page': page_num,
                                    'size_kb': size_kb,
                                    'width': width,
                                    'height': height,
                                    'base64': img_b64
                                })

print(f"\n✅ Total de imagens encontradas: {len(images_data)}\n")

# Salvar todas as imagens
print("💾 Salvando imagens...")
print("=" * 70)

for img_data in images_data:
    idx = img_data['index']
    size_kb = img_data['size_kb']
    page = img_data['page']
    width = img_data['width']
    height = img_data['height']
    source = img_data['source']

    # Decodificar base64
    try:
        img_bytes = base64.b64decode(img_data['base64'])

        # Detectar formato (simples heurística)
        if img_bytes[:4] == b'\x89PNG':
            ext = 'png'
        elif img_bytes[:2] == b'\xff\xd8':
            ext = 'jpg'
        elif img_bytes[:4] == b'GIF8':
            ext = 'gif'
        else:
            ext = 'bin'

        # Nome do arquivo
        filename = f"img_{idx:03d}_p{page}_{size_kb:.1f}KB_{width}x{height}.{ext}"
        filepath = os.path.join(output_dir, filename)

        # Salvar
        with open(filepath, 'wb') as f:
            f.write(img_bytes)

        # Status
        status = "✅"
        if size_kb < 5:
            status = "🔴 <5KB"
        elif size_kb < 20:
            status = "⚠️  5-20KB"
        else:
            status = "✅ >20KB"

        print(f"{status} [{idx:3d}] {filename}")
        print(f"       Source: {source}, Chunk: {img_data['chunk_index']}")

    except Exception as e:
        print(f"❌ [{idx:3d}] ERRO ao decodificar: {str(e)[:50]}")

print("\n" + "=" * 70)
print("📊 ANÁLISE POR TAMANHO")
print("=" * 70)

# Agrupar por faixa de tamanho
size_ranges = {
    '< 5KB (ícones)': [],
    '5-10KB (pequenos)': [],
    '10-20KB (médios)': [],
    '20-50KB (grandes)': [],
    '> 50KB (muito grandes)': []
}

for img in images_data:
    size = img['size_kb']
    if size < 5:
        size_ranges['< 5KB (ícones)'].append(img)
    elif size < 10:
        size_ranges['5-10KB (pequenos)'].append(img)
    elif size < 20:
        size_ranges['10-20KB (médios)'].append(img)
    elif size < 50:
        size_ranges['20-50KB (grandes)'].append(img)
    else:
        size_ranges['> 50KB (muito grandes)'].append(img)

for range_name, imgs in size_ranges.items():
    if imgs:
        print(f"\n{range_name}: {len(imgs)} imagens")
        for img in imgs[:5]:  # Mostrar até 5 exemplos
            print(f"  - Imagem {img['index']:3d}: {img['size_kb']:6.1f}KB, "
                  f"Página {img['page']}, {img['width']}x{img['height']}")
        if len(imgs) > 5:
            print(f"  ... e mais {len(imgs) - 5} imagens")

print("\n" + "=" * 70)
print("💡 RECOMENDAÇÕES")
print("=" * 70)

total_small = len(size_ranges['< 5KB (ícones)']) + len(size_ranges['5-10KB (pequenos)'])
total_medium = len(size_ranges['10-20KB (médios)'])
total_large = len(size_ranges['20-50KB (grandes)']) + len(size_ranges['> 50KB (muito grandes)'])

print(f"\nTotal de imagens: {len(images_data)}")
print(f"  Pequenas (<10KB): {total_small} imagens")
print(f"  Médias (10-20KB): {total_medium} imagens")
print(f"  Grandes (>20KB): {total_large} imagens\n")

if total_small > total_large * 3:
    print("⚠️  MUITAS imagens pequenas detectadas!")
    print("   Provavelmente: ícones, logos, bullets, decoração")
    print(f"\n   RECOMENDAÇÃO: Aumentar MIN_IMAGE_SIZE_KB para 20-30")
    print(f"   Isso filtraria {total_small + total_medium} imagens, mantendo {total_large} reais")
elif total_medium > total_large:
    print("⚠️  Muitas imagens médias (10-20KB) detectadas")
    print(f"   RECOMENDAÇÃO: Aumentar MIN_IMAGE_SIZE_KB para 15-20")
    print(f"   Isso filtraria {total_small + total_medium} imagens, mantendo {total_large} reais")
else:
    print("✅ Distribuição de tamanhos parece razoável")
    print(f"   Filtro atual de 5KB já remove a maioria dos ícones")

print("\n" + "=" * 70)
print(f"✅ Imagens salvas em: {os.path.abspath(output_dir)}")
print("=" * 70)
print("\n💡 PRÓXIMO PASSO:")
print(f"   1. Abra a pasta: {os.path.abspath(output_dir)}")
print(f"   2. Visualize as imagens para identificar padrões")
print(f"   3. Identifique qual tamanho mínimo faz sentido")
print(f"   4. Ajuste MIN_IMAGE_SIZE_KB no código\n")
