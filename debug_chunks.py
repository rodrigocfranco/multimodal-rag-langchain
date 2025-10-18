#!/usr/bin/env python3
"""
DEBUG: Investigar tipos de elementos retornados pelo partition_pdf
"""

import os
import sys
from dotenv import load_dotenv
from unstructured.partition.pdf import partition_pdf

load_dotenv()

if len(sys.argv) < 2:
    print("Uso: python debug_chunks.py arquivo.pdf")
    exit(1)

file_path = sys.argv[1]

print("=" * 70)
print("🔍 DEBUG: Tipos de Elementos Retornados")
print("=" * 70)
print(f"\nArquivo: {file_path}\n")

# Particionar com os MESMOS parâmetros do adicionar_pdf.py
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
print("=" * 70)
print("📊 TIPOS DE ELEMENTOS")
print("=" * 70)

element_types = {}
for chunk in chunks:
    chunk_type = str(type(chunk).__name__)
    element_types[chunk_type] = element_types.get(chunk_type, 0) + 1

for elem_type, count in sorted(element_types.items()):
    print(f"  {elem_type}: {count}")

# Procurar por tabelas
print("\n" + "=" * 70)
print("🔍 BUSCANDO TABELAS")
print("=" * 70)

tables_found = []
for i, chunk in enumerate(chunks):
    chunk_type = str(type(chunk).__name__)

    # Buscar tabelas diretas
    if "Table" in chunk_type:
        tables_found.append({
            "index": i,
            "type": chunk_type,
            "source": "direct",
            "preview": str(chunk)[:200]
        })

    # Buscar tabelas em orig_elements
    if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
        if chunk.metadata.orig_elements:
            for j, orig_el in enumerate(chunk.metadata.orig_elements):
                orig_type = str(type(orig_el).__name__)
                if "Table" in orig_type:
                    tables_found.append({
                        "index": i,
                        "type": orig_type,
                        "source": f"orig_elements[{j}]",
                        "preview": str(orig_el)[:200]
                    })

if tables_found:
    print(f"\n✅ Encontradas {len(tables_found)} tabelas:\n")
    for table in tables_found:
        print(f"  Chunk {table['index']} ({table['type']}) - source: {table['source']}")
        print(f"  Preview: {table['preview'][:150]}...")
        print()
else:
    print("\n❌ NENHUMA TABELA ENCONTRADA!\n")

# Mostrar amostra de chunks
print("=" * 70)
print("📄 AMOSTRA DE CHUNKS (primeiros 3)")
print("=" * 70)

for i, chunk in enumerate(chunks[:3]):
    print(f"\n--- CHUNK {i} ---")
    print(f"Tipo: {type(chunk).__name__}")

    if hasattr(chunk, 'text'):
        print(f"Texto (primeiros 300 chars): {chunk.text[:300]}...")

    if hasattr(chunk, 'metadata'):
        print(f"Metadata:")
        if hasattr(chunk.metadata, 'page_number'):
            print(f"  page_number: {chunk.metadata.page_number}")
        if hasattr(chunk.metadata, 'category'):
            print(f"  category: {chunk.metadata.category}")
        if hasattr(chunk.metadata, 'orig_elements'):
            orig_count = len(chunk.metadata.orig_elements) if chunk.metadata.orig_elements else 0
            print(f"  orig_elements: {orig_count} elementos")

            if orig_count > 0:
                orig_types = [str(type(el).__name__) for el in chunk.metadata.orig_elements]
                print(f"  tipos em orig_elements: {set(orig_types)}")

print("\n" + "=" * 70)
print("🏁 DEBUG COMPLETO")
print("=" * 70)
