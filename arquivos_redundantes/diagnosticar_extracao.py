#!/usr/bin/env python3
"""
Script de diagnóstico para problemas de extração
"""

import sys
import os
from unstructured.partition.pdf import partition_pdf

print("=" * 80)
print("🔍 DIAGNÓSTICO DE EXTRAÇÃO DE PDF")
print("=" * 80)
print()

if len(sys.argv) < 2:
    print("Uso: python diagnosticar_extracao.py arquivo.pdf")
    sys.exit(1)

pdf_filename = sys.argv[1]
file_path = f"./content/{pdf_filename}"

if not os.path.exists(file_path):
    print(f"❌ Arquivo não encontrado: {file_path}")
    sys.exit(1)

print(f"📄 Analisando: {pdf_filename}")
print()

# Extrair com diferentes configurações
print("Teste 1: Extração padrão")
print("-" * 80)
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

print(f"Total de chunks: {len(chunks)}")
print()

# Analisar tipos de elementos
print("Tipos de elementos encontrados:")
print("-" * 80)
from collections import Counter

types_counter = Counter([str(type(chunk).__name__) for chunk in chunks])
for element_type, count in types_counter.items():
    print(f"  • {element_type}: {count}")

print()

# Detectar tabelas de forma diferente
print("Analisando elementos individuais:")
print("-" * 80)

tables_found = []
texts_found = []
composite_found = []

for i, chunk in enumerate(chunks):
    chunk_type = type(chunk).__name__
    
    # Verificar se é tabela
    if "Table" in chunk_type:
        tables_found.append(i)
        print(f"✅ Chunk {i}: TABELA detectada - Tipo: {chunk_type}")
        if hasattr(chunk, 'text'):
            print(f"   Conteúdo (primeiros 100 chars): {chunk.text[:100]}")
    
    # Verificar CompositeElement
    elif "Composite" in chunk_type:
        composite_found.append(i)
        # Verificar se tem tabelas dentro
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            orig_els = chunk.metadata.orig_elements
            for el in orig_els:
                if "Table" in str(type(el)):
                    print(f"⚠️  Chunk {i}: Composite contém TABELA - Tipo elemento: {type(el).__name__}")
    
    elif chunk_type not in ['CompositeElement', 'Table']:
        print(f"  Chunk {i}: Outro tipo - {chunk_type}")

print()
print("=" * 80)
print("RESUMO")
print("=" * 80)
print(f"📝 Tabelas diretas encontradas: {len(tables_found)}")
print(f"📦 CompositeElements: {len(composite_found)}")
print()

# Teste 2: Extrair com Image para tabelas também
print("Teste 2: Extrair tabelas como imagens")
print("-" * 80)

chunks2 = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image", "Table"],  # Adicionar Table
    extract_image_block_to_payload=True,
)

types_counter2 = Counter([str(type(chunk).__name__) for chunk in chunks2])
print("Tipos com Image+Table:")
for element_type, count in types_counter2.items():
    print(f"  • {element_type}: {count}")

print()

# Verificar imagens
print("=" * 80)
print("ANÁLISE DE IMAGENS")
print("=" * 80)

def get_images_base64(chunks):
    images_b64 = []
    for chunk in chunks:
        if "CompositeElement" in str(type(chunk)):
            if hasattr(chunk.metadata, 'orig_elements'):
                chunk_els = chunk.metadata.orig_elements
                for el in chunk_els:
                    if "Image" in str(type(el)):
                        if hasattr(el.metadata, 'image_base64'):
                            img_data = el.metadata.image_base64
                            images_b64.append({
                                'data': img_data,
                                'size': len(img_data),
                                'type': type(el).__name__
                            })
    return images_b64

images = get_images_base64(chunks)
print(f"Total de imagens: {len(images)}")
print()

for i, img_info in enumerate(images[:3]):  # Primeiras 3
    size_kb = img_info['size'] / 1024
    print(f"Imagem {i+1}:")
    print(f"  • Tamanho: {size_kb:.1f} KB")
    print(f"  • Tipo: {img_info['type']}")
    
    # Verificar se começa com data válida
    img_data = img_info['data']
    if img_data:
        print(f"  • Primeiros 50 chars: {img_data[:50]}")
        
        # Testar decodificação
        import base64
        try:
            decoded = base64.b64decode(img_data[:100])
            print(f"  • Decodificação: ✅ OK")
        except:
            print(f"  • Decodificação: ❌ ERRO")
    print()

print("=" * 80)
print("DIAGNÓSTICO COMPLETO")
print("=" * 80)

