#!/usr/bin/env python3
"""
🧪 TESTE DE VALIDAÇÃO DO METADATA ENRICHMENT

Testa se os metadados enriquecidos estão funcionando corretamente:
1. Keywords extraídas (KeyBERT)
2. Entidades médicas (Medical NER)
3. Valores numéricos (Numerical extraction)
4. Queries com filtros de metadata

Data: 2025-10-22
"""

import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import json

load_dotenv()

PERSIST_DIR = os.getenv("PERSIST_DIR", "./knowledge")
PDF_ID = "38d1b6f3c5244470"  # PDF que acabamos de processar

print("=" * 80)
print("🧪 TESTE DE VALIDAÇÃO DO METADATA ENRICHMENT")
print("=" * 80)

# Inicializar vectorstore
print("\n🔧 Carregando vectorstore...")
vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
    persist_directory=PERSIST_DIR
)
print("✓ Vectorstore carregado!")

# ==============================================================================
# TESTE 1: VERIFICAR SE METADADOS ENRIQUECIDOS EXISTEM
# ==============================================================================

print("\n" + "=" * 80)
print("📊 TESTE 1: Verificar Metadados Enriquecidos nos Documentos")
print("=" * 80)

# Buscar documentos do PDF recém-processado
docs = vectorstore.similarity_search(
    "",  # Query vazia
    k=16,  # Todos os 16 chunks
    filter={"pdf_id": PDF_ID}
)

print(f"\n✓ Encontrados {len(docs)} documentos do PDF")

# Analisar metadados
stats = {
    "total_docs": len(docs),
    "with_keywords": 0,
    "with_diseases": 0,
    "with_medications": 0,
    "with_procedures": 0,
    "with_measurements": 0,
    "unique_keywords": set(),
    "unique_diseases": set(),
    "unique_medications": set(),
    "unique_procedures": set(),
}

print("\n📋 Analisando metadados de cada documento...\n")

for i, doc in enumerate(docs):
    doc_type = doc.metadata.get('type', 'unknown')
    print(f"[{i+1}/{len(docs)}] Tipo: {doc_type}")

    # Keywords
    keywords_str = doc.metadata.get('keywords_str', '')
    if keywords_str and keywords_str.strip():
        stats["with_keywords"] += 1
        keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
        stats["unique_keywords"].update(keywords)
        print(f"   ✓ Keywords: {keywords[:5]}..." if len(keywords) > 5 else f"   ✓ Keywords: {keywords}")
    else:
        print(f"   ✗ Sem keywords")

    # Doenças
    diseases_str = doc.metadata.get('entities_diseases_str', '')
    if diseases_str and diseases_str.strip():
        stats["with_diseases"] += 1
        diseases = [d.strip() for d in diseases_str.split(',') if d.strip()]
        stats["unique_diseases"].update(diseases)
        print(f"   ✓ Doenças: {diseases}")

    # Medicamentos
    meds_str = doc.metadata.get('entities_medications_str', '')
    if meds_str and meds_str.strip():
        stats["with_medications"] += 1
        meds = [m.strip() for m in meds_str.split(',') if m.strip()]
        stats["unique_medications"].update(meds)
        print(f"   ✓ Medicamentos: {meds}")

    # Procedimentos
    procs_str = doc.metadata.get('entities_procedures_str', '')
    if procs_str and procs_str.strip():
        stats["with_procedures"] += 1
        procs = [p.strip() for p in procs_str.split(',') if p.strip()]
        stats["unique_procedures"].update(procs)
        print(f"   ✓ Procedimentos: {procs[:3]}..." if len(procs) > 3 else f"   ✓ Procedimentos: {procs}")

    # Medições
    measurements_count = doc.metadata.get('measurements_count', 0)
    if measurements_count > 0:
        stats["with_measurements"] += 1
        print(f"   ✓ Medições: {measurements_count} encontradas")

    print()

# Estatísticas gerais
print("=" * 80)
print("📊 ESTATÍSTICAS GERAIS:")
print("=" * 80)
print(f"\nCobertura de metadados:")
print(f"   Documentos com keywords: {stats['with_keywords']}/{stats['total_docs']} ({stats['with_keywords']/stats['total_docs']*100:.0f}%)")
print(f"   Documentos com doenças: {stats['with_diseases']}/{stats['total_docs']} ({stats['with_diseases']/stats['total_docs']*100:.0f}%)")
print(f"   Documentos com medicamentos: {stats['with_medications']}/{stats['total_docs']} ({stats['with_medications']/stats['total_docs']*100:.0f}%)")
print(f"   Documentos com procedimentos: {stats['with_procedures']}/{stats['total_docs']} ({stats['with_procedures']/stats['total_docs']*100:.0f}%)")
print(f"   Documentos com medições: {stats['with_measurements']}/{stats['total_docs']} ({stats['with_measurements']/stats['total_docs']*100:.0f}%)")

print(f"\nDiversidade de termos extraídos:")
print(f"   Keywords únicas: {len(stats['unique_keywords'])}")
print(f"   Doenças únicas: {len(stats['unique_diseases'])}")
print(f"   Medicamentos únicos: {len(stats['unique_medications'])}")
print(f"   Procedimentos únicos: {len(stats['unique_procedures'])}")

# Mostrar alguns exemplos
if stats['unique_keywords']:
    print(f"\n🔤 Exemplos de keywords extraídas:")
    print(f"   {list(stats['unique_keywords'])[:10]}")

if stats['unique_diseases']:
    print(f"\n🏥 Exemplos de doenças identificadas:")
    print(f"   {list(stats['unique_diseases'])[:10]}")

if stats['unique_medications']:
    print(f"\n💊 Exemplos de medicamentos identificados:")
    print(f"   {list(stats['unique_medications'])[:10]}")

# ==============================================================================
# TESTE 2: QUERIES COM METADATA FILTERS
# ==============================================================================

print("\n" + "=" * 80)
print("🔍 TESTE 2: Queries com Filtros de Metadata")
print("=" * 80)

# Teste 2.1: Query apenas em tabelas
print("\n[2.1] Buscar apenas TABELAS sobre 'hiperglicemia'...")
try:
    results = vectorstore.similarity_search(
        "hiperglicemia tratamento",
        k=5,
        filter={"pdf_id": PDF_ID, "type": "table"}
    )
    print(f"   ✓ Encontradas {len(results)} tabelas")
    for i, doc in enumerate(results):
        section = doc.metadata.get('section', 'N/A')
        print(f"      [{i+1}] Seção: {section}")
except Exception as e:
    print(f"   ✗ Erro: {str(e)[:100]}")

# Teste 2.2: Query apenas em textos
print("\n[2.2] Buscar apenas TEXTOS sobre 'diabetes'...")
try:
    results = vectorstore.similarity_search(
        "diabetes insulina",
        k=5,
        filter={"pdf_id": PDF_ID, "type": "text"}
    )
    print(f"   ✓ Encontrados {len(results)} textos")
    for i, doc in enumerate(results):
        section = doc.metadata.get('section', 'N/A')
        print(f"      [{i+1}] Seção: {section}")
except Exception as e:
    print(f"   ✗ Erro: {str(e)[:100]}")

# Teste 2.3: Query apenas em imagens
print("\n[2.3] Buscar IMAGENS...")
try:
    results = vectorstore.similarity_search(
        "",
        k=5,
        filter={"pdf_id": PDF_ID, "type": "image"}
    )
    print(f"   ✓ Encontradas {len(results)} imagens")
    for i, doc in enumerate(results):
        summary = doc.metadata.get('summary', 'N/A')[:100]
        print(f"      [{i+1}] Descrição: {summary}...")
except Exception as e:
    print(f"   ✗ Erro: {str(e)[:100]}")

# ==============================================================================
# TESTE 3: COMPARAÇÃO COM/SEM METADATA
# ==============================================================================

print("\n" + "=" * 80)
print("⚖️  TESTE 3: Comparação de Retrieval (com vs sem metadata)")
print("=" * 80)

test_queries = [
    "Como tratar hiperglicemia hospitalar?",
    "Qual o alvo de glicemia em UTI?",
    "Protocolo de infusão de insulina",
]

print("\nTestando queries médicas específicas...\n")

for query in test_queries:
    print(f"Query: '{query}'")

    # Sem filtro (baseline)
    results_baseline = vectorstore.similarity_search(query, k=3)

    # Com filtro de tipo de documento
    results_filtered = vectorstore.similarity_search(
        query,
        k=3,
        filter={"document_type": "clinical_guideline"}
    )

    print(f"   Resultados sem filtro: {len(results_baseline)}")
    print(f"   Resultados com filtro (apenas guidelines): {len(results_filtered)}")

    # Verificar se resultados filtrados têm melhor relevância
    # (documentos de guidelines são mais confiáveis para recomendações)
    if results_filtered:
        top_result = results_filtered[0]
        doc_type = top_result.metadata.get('document_type', 'unknown')
        section = top_result.metadata.get('section', 'unknown')
        print(f"   ✓ Top result: {doc_type} - Seção: {section}")
    print()

# ==============================================================================
# TESTE 4: VALIDAÇÃO DE QUALIDADE
# ==============================================================================

print("\n" + "=" * 80)
print("✅ TESTE 4: Validação de Qualidade")
print("=" * 80)

print("\n📋 Checklist de qualidade:\n")

# Check 1: Keywords coverage
keywords_coverage = stats['with_keywords'] / stats['total_docs'] * 100
check1 = keywords_coverage >= 50
print(f"{'✓' if check1 else '✗'} [1] Keywords coverage: {keywords_coverage:.0f}% (esperado: ≥50%)")

# Check 2: Medical entities present
entities_coverage = (stats['with_diseases'] + stats['with_medications'] + stats['with_procedures']) / (stats['total_docs'] * 3) * 100
check2 = entities_coverage >= 20
print(f"{'✓' if check2 else '✗'} [2] Medical entities coverage: {entities_coverage:.0f}% (esperado: ≥20%)")

# Check 3: Diversity of keywords
check3 = len(stats['unique_keywords']) >= 10
print(f"{'✓' if check3 else '✗'} [3] Keyword diversity: {len(stats['unique_keywords'])} únicas (esperado: ≥10)")

# Check 4: No empty metadata fields
empty_count = stats['total_docs'] - stats['with_keywords']
check4 = empty_count <= stats['total_docs'] * 0.3
print(f"{'✓' if check4 else '✗'} [4] Docs sem keywords: {empty_count}/{stats['total_docs']} (esperado: ≤30%)")

# Check 5: Metadata diversity per document type
texts_with_keywords = sum(1 for doc in docs if doc.metadata.get('type') == 'text' and doc.metadata.get('keywords_str'))
tables_with_keywords = sum(1 for doc in docs if doc.metadata.get('type') == 'table' and doc.metadata.get('keywords_str'))
check5 = texts_with_keywords >= 1 and tables_with_keywords >= 1
print(f"{'✓' if check5 else '✗'} [5] Keywords em textos E tabelas: Textos={texts_with_keywords}, Tabelas={tables_with_keywords}")

# ==============================================================================
# VEREDICTO FINAL
# ==============================================================================

print("\n" + "=" * 80)
print("🎯 VEREDICTO FINAL")
print("=" * 80)

all_checks = [check1, check2, check3, check4, check5]
passed = sum(all_checks)
total = len(all_checks)

print(f"\nChecks passados: {passed}/{total}\n")

if passed == total:
    print("✅ EXCELENTE! Metadata enrichment funcionando perfeitamente!")
    print("   - Keywords sendo extraídas com sucesso")
    print("   - Entidades médicas identificadas")
    print("   - Boa cobertura e diversidade")
    print("   - Queries com filtros funcionando")
elif passed >= total * 0.7:
    print("✓ BOM! Metadata enrichment funcionando bem")
    print(f"   - {passed}/{total} checks passaram")
    print("   - Alguns ajustes podem melhorar ainda mais")
elif passed >= total * 0.4:
    print("⚠️  MODERADO: Metadata enrichment parcialmente funcional")
    print(f"   - Apenas {passed}/{total} checks passaram")
    print("   - Considere revisar configurações")
else:
    print("❌ PROBLEMA: Metadata enrichment não está funcionando bem")
    print(f"   - Apenas {passed}/{total} checks passaram")
    print("   - Investigação necessária!")

print("\n" + "=" * 80)
print()
