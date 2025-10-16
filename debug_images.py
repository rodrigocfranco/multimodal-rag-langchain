#!/usr/bin/env python3
"""
Debug script para investigar extração de imagens
"""

import os
import sys

file_path = '/Users/rcfranco/Desktop/Documentos processados/Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf'

print(f"Analisando: {os.path.basename(file_path)}")
print("=" * 60)

try:
    from unstructured.partition.pdf import partition_pdf

    # Processar PDF
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

    print(f"\nTotal de chunks extraídos: {len(chunks)}\n")

    # Analisar tipos
    type_counts = {}
    images_direct = []
    images_in_orig = []

    for i, chunk in enumerate(chunks):
        chunk_type = str(type(chunk).__name__)
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

        # Verificar imagens diretas
        if "Image" in chunk_type:
            if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'image_base64'):
                img = chunk.metadata.image_base64
                if img and len(img) > 100:
                    size_kb = len(img) / 1024
                    images_direct.append({
                        'index': i,
                        'type': chunk_type,
                        'size_kb': size_kb,
                        'hash': hash(img[:1000])
                    })

        # Verificar imagens em orig_elements
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            if chunk.metadata.orig_elements:
                for j, el in enumerate(chunk.metadata.orig_elements):
                    el_type = str(type(el).__name__)
                    if "Image" in el_type and hasattr(el.metadata, 'image_base64'):
                        img = el.metadata.image_base64
                        if img and len(img) > 100:
                            size_kb = len(img) / 1024
                            images_in_orig.append({
                                'chunk_index': i,
                                'el_index': j,
                                'chunk_type': chunk_type,
                                'el_type': el_type,
                                'size_kb': size_kb,
                                'hash': hash(img[:1000])
                            })

    print("DISTRIBUIÇÃO DE TIPOS:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")

    print(f"\n{'='*60}")
    print(f"IMAGENS DIRETAS: {len(images_direct)}")
    print(f"{'='*60}")
    for img in images_direct:
        print(f"  [{img['index']}] {img['type']} - {img['size_kb']:.1f}KB - hash:{img['hash']}")

    print(f"\n{'='*60}")
    print(f"IMAGENS EM ORIG_ELEMENTS: {len(images_in_orig)}")
    print(f"{'='*60}")
    for img in images_in_orig:
        print(f"  Chunk[{img['chunk_index']}].orig[{img['el_index']}] {img['chunk_type']}→{img['el_type']} - {img['size_kb']:.1f}KB - hash:{img['hash']}")

    # Verificar duplicatas
    all_hashes = [img['hash'] for img in images_direct] + [img['hash'] for img in images_in_orig]
    unique_hashes = set(all_hashes)

    print(f"\n{'='*60}")
    print(f"TOTAL DE IMAGENS (SEM DEDUP): {len(all_hashes)}")
    print(f"TOTAL DE IMAGENS (COM DEDUP): {len(unique_hashes)}")
    print(f"DUPLICATAS REMOVIDAS: {len(all_hashes) - len(unique_hashes)}")
    print(f"{'='*60}")

    # Mostrar quais hashes aparecem mais de uma vez
    from collections import Counter
    hash_counts = Counter(all_hashes)
    duplicates = {h: c for h, c in hash_counts.items() if c > 1}

    if duplicates:
        print(f"\nHASHES DUPLICADOS:")
        for h, count in duplicates.items():
            print(f"  hash:{h} aparece {count}x")

except ImportError:
    print("\nERRO: Módulo 'unstructured' não instalado")
    print("Execute: pip install -r requirements.txt")
except Exception as e:
    print(f"\nERRO: {e}")
    import traceback
    traceback.print_exc()
