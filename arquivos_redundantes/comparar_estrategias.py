#!/usr/bin/env python3
"""
Comparar Estratégias de Extração
Ver diferença entre extrair com/sem chunking
"""

import sys
from unstructured.partition.pdf import partition_pdf

if len(sys.argv) < 2:
    print("Uso: python comparar_estrategias.py arquivo.pdf")
    sys.exit(1)

pdf_filename = sys.argv[1]
file_path = f"./content/{pdf_filename}"

print("=" * 80)
print("🔍 COMPARAÇÃO DE ESTRATÉGIAS DE EXTRAÇÃO")
print("=" * 80)
print()

# ============================================================================
# ESTRATÉGIA 1: SEM CHUNKING (gera muitos elementos pequenos)
# ============================================================================
print("Estratégia 1: SEM chunking")
print("-" * 80)

chunks1 = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image", "Table"],
    extract_image_block_to_payload=True,
    # SEM chunking_strategy
)

print(f"Total de elementos: {len(chunks1)}")

from collections import Counter
types1 = Counter([type(c).__name__ for c in chunks1])
print("Tipos de elementos:")
for t, count in types1.most_common():
    print(f"  • {t}: {count}")

print()

# ============================================================================
# ESTRATÉGIA 2: COM CHUNKING (agrupa elementos relacionados)
# ============================================================================
print("Estratégia 2: COM chunking by_title")
print("-" * 80)

chunks2 = partition_pdf(
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

print(f"Total de elementos: {len(chunks2)}")

types2 = Counter([type(c).__name__ for c in chunks2])
print("Tipos de elementos:")
for t, count in types2.most_common():
    print(f"  • {t}: {count}")

print()

# ============================================================================
# COMPARAÇÃO
# ============================================================================
print("=" * 80)
print("📊 COMPARAÇÃO")
print("=" * 80)
print()

print(f"SEM chunking:  {len(chunks1)} elementos (muitos pequenos)")
print(f"COM chunking:  {len(chunks2)} elementos (agrupados e maiores)")
print()
print(f"Diferença:     {len(chunks1) - len(chunks2)} elementos a menos com chunking")
print(f"Redução:       {((len(chunks1) - len(chunks2)) / len(chunks1) * 100):.1f}%")
print()

# Analisar tamanhos
print("Tamanho médio dos textos:")
print("-" * 80)

def get_avg_size(chunks):
    sizes = []
    for c in chunks:
        if hasattr(c, 'text'):
            sizes.append(len(c.text))
    return sum(sizes) / len(sizes) if sizes else 0

avg1 = get_avg_size(chunks1)
avg2 = get_avg_size(chunks2)

print(f"SEM chunking:  {avg1:.0f} caracteres por elemento")
print(f"COM chunking:  {avg2:.0f} caracteres por elemento")
print()

# ============================================================================
# RECOMENDAÇÃO
# ============================================================================
print("=" * 80)
print("💡 RECOMENDAÇÃO")
print("=" * 80)
print()

if len(chunks2) < len(chunks1) / 2:
    print("✅ USAR chunking_strategy='by_title'")
    print()
    print("Vantagens:")
    print(f"  • {len(chunks1) - len(chunks2)} elementos a menos para processar")
    print(f"  • Chunks maiores e mais contextualizados")
    print(f"  • Economiza tempo e tokens de API")
    print(f"  • Melhor performance do RAG")
    print()
    print("⚠️  IMPORTANTE: Use os parâmetros de chunking em TODOS os scripts!")
else:
    print("⚠️  Chunking não teve grande impacto neste PDF")

print()
print("=" * 80)

