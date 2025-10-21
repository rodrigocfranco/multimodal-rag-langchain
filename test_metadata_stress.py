#!/usr/bin/env python3
"""
🧪 METADATA ENRICHMENT STRESS TEST

Testa os metadados enriquecidos com queries desafiadoras:
1. Keywords-based queries (KeyBERT)
2. Medical entity queries (NER)
3. Numerical range queries (values + units)
4. Combined filters (multi-metadata)
5. Edge cases (empty, special chars, multilingual)

Data: 2025-10-21
"""

import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import json

load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

PERSIST_DIR = os.getenv("PERSIST_DIR", "./knowledge")

print("="*80)
print("🧪 METADATA ENRICHMENT STRESS TEST")
print("="*80)

# Inicializar vectorstore
print("\n🔧 Carregando vectorstore...")
vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
    persist_directory=PERSIST_DIR
)
print("✓ Vectorstore carregado!")

# ==============================================================================
# TESTE 1: VERIFICAR METADADOS ENRIQUECIDOS
# ==============================================================================

print("\n" + "="*80)
print("📊 TESTE 1: Verificar Metadados Enriquecidos no Vectorstore")
print("="*80)

# Buscar alguns documentos para inspecionar metadados
docs = vectorstore.similarity_search("diabetes", k=5)

print(f"\n✓ Encontrados {len(docs)} documentos")

has_enriched = False
stats = {
    "total_docs": len(docs),
    "with_keywords": 0,
    "with_entities": 0,
    "with_measurements": 0,
    "unique_keywords": set(),
    "unique_diseases": set(),
    "unique_medications": set(),
    "unique_procedures": set()
}

for i, doc in enumerate(docs):
    print(f"\n[{i+1}] Documento: {doc.metadata.get('source', 'N/A')[:50]}...")
    print(f"    Tipo: {doc.metadata.get('type', 'N/A')}")
    print(f"    Seção: {doc.metadata.get('section', 'N/A')}")

    # Verificar metadados enriquecidos
    if 'keywords' in doc.metadata:
        keywords = doc.metadata.get('keywords', [])
        if keywords:
            stats["with_keywords"] += 1
            stats["unique_keywords"].update(keywords)
            print(f"    ✓ Keywords: {keywords[:3]}...")
            has_enriched = True

    if 'entities_diseases' in doc.metadata:
        diseases = doc.metadata.get('entities_diseases', [])
        if diseases:
            stats["with_entities"] += 1
            stats["unique_diseases"].update(diseases)
            print(f"    ✓ Doenças: {diseases}")

    if 'entities_medications' in doc.metadata:
        meds = doc.metadata.get('entities_medications', [])
        if meds:
            stats["unique_medications"].update(meds)
            print(f"    ✓ Medicamentos: {meds}")

    if 'entities_procedures' in doc.metadata:
        procs = doc.metadata.get('entities_procedures', [])
        if procs:
            stats["unique_procedures"].update(procs)
            print(f"    ✓ Procedimentos: {procs[:3]}...")

    if 'measurements' in doc.metadata:
        measurements = doc.metadata.get('measurements', [])
        if measurements:
            stats["with_measurements"] += 1
            print(f"    ✓ Medições: {len(measurements)} encontradas")

print(f"\n📊 ESTATÍSTICAS GERAIS:")
print(f"   Documentos com keywords: {stats['with_keywords']}/{stats['total_docs']}")
print(f"   Documentos com entidades: {stats['with_entities']}/{stats['total_docs']}")
print(f"   Documentos com medições: {stats['with_measurements']}/{stats['total_docs']}")
print(f"   Keywords únicas: {len(stats['unique_keywords'])}")
print(f"   Doenças únicas: {len(stats['unique_diseases'])}")
print(f"   Medicamentos únicos: {len(stats['unique_medications'])}")
print(f"   Procedimentos únicos: {len(stats['unique_procedures'])}")

if not has_enriched:
    print("\n⚠️  AVISO: Nenhum documento com metadados enriquecidos encontrado!")
    print("   Os PDFs precisam ser reprocessados com o novo adicionar_pdf.py")
    print("   Execute: python3 adicionar_pdf.py 'content/seu-artigo.pdf'")

# ==============================================================================
# TESTE 2: QUERIES BASEADAS EM KEYWORDS
# ==============================================================================

print("\n" + "="*80)
print("🔍 TESTE 2: Queries Baseadas em Keywords (KeyBERT)")
print("="*80)

keyword_queries = [
    "diabetes tipo 2",
    "metformina",
    "HbA1c",
    "insulina",
    "hipertensão arterial",
    "cardiomiopatia"
]

print("\nTestando queries que devem matchear keywords extraídas...\n")

for query in keyword_queries:
    results = vectorstore.similarity_search(query, k=3)

    # Verificar se algum resultado tem a keyword nos metadados
    keyword_matches = 0
    for doc in results:
        doc_keywords = doc.metadata.get('keywords', [])
        if isinstance(doc_keywords, list):
            # Verificar se query está nas keywords (case-insensitive)
            query_lower = query.lower()
            if any(query_lower in kw.lower() for kw in doc_keywords):
                keyword_matches += 1

    status = "✓" if keyword_matches > 0 else "✗"
    print(f"{status} Query: '{query}' → {keyword_matches}/{len(results)} docs com keyword match")

# ==============================================================================
# TESTE 3: QUERIES BASEADAS EM ENTIDADES MÉDICAS
# ==============================================================================

print("\n" + "="*80)
print("🏥 TESTE 3: Queries Baseadas em Entidades Médicas (NER)")
print("="*80)

entity_queries = [
    ("diabetes tipo 2", "entities_diseases"),
    ("hipertensão arterial", "entities_diseases"),
    ("metformina", "entities_medications"),
    ("insulina", "entities_medications"),
    ("HbA1c", "entities_procedures"),
    ("glicemia", "entities_procedures")
]

print("\nTestando queries que devem matchear entidades médicas...\n")

for query, entity_field in entity_queries:
    results = vectorstore.similarity_search(query, k=3)

    # Verificar se algum resultado tem a entidade nos metadados
    entity_matches = 0
    for doc in results:
        entities = doc.metadata.get(entity_field, [])
        if isinstance(entities, list):
            query_lower = query.lower()
            if any(query_lower in ent.lower() for ent in entities):
                entity_matches += 1

    field_name = entity_field.replace('entities_', '').capitalize()
    status = "✓" if entity_matches > 0 else "✗"
    print(f"{status} {field_name}: '{query}' → {entity_matches}/{len(results)} docs com entity match")

# ==============================================================================
# TESTE 4: QUERIES BASEADAS EM VALORES NUMÉRICOS
# ==============================================================================

print("\n" + "="*80)
print("📊 TESTE 4: Queries Baseadas em Valores Numéricos")
print("="*80)

numerical_queries = [
    "HbA1c maior que 7%",
    "TFG menor que 60",
    "creatinina elevada",
    "glicemia de jejum 180 mg/dL",
    "pressão arterial 140/90"
]

print("\nTestando queries numéricas...\n")

for query in numerical_queries:
    results = vectorstore.similarity_search(query, k=3)

    # Verificar se algum resultado tem medições
    docs_with_measurements = 0
    for doc in results:
        measurements = doc.metadata.get('measurements', [])
        if measurements:
            docs_with_measurements += 1

    status = "✓" if docs_with_measurements > 0 else "✗"
    print(f"{status} Query: '{query}' → {docs_with_measurements}/{len(results)} docs com measurements")

# ==============================================================================
# TESTE 5: FILTROS COMBINADOS
# ==============================================================================

print("\n" + "="*80)
print("🎯 TESTE 5: Filtros Combinados (Multi-Metadata)")
print("="*80)

combined_queries = [
    {
        "query": "diabetes",
        "filter": {"type": "text"},
        "description": "Apenas textos sobre diabetes"
    },
    {
        "query": "diabetes",
        "filter": {"type": "table"},
        "description": "Apenas tabelas sobre diabetes"
    },
    {
        "query": "tratamento",
        "filter": {"section": "Tratamento"},
        "description": "Apenas seção Tratamento"
    },
    {
        "query": "diabetes",
        "filter": {"document_type": "clinical_guideline"},
        "description": "Apenas guidelines clínicas"
    }
]

print("\nTestando filtros combinados...\n")

for test in combined_queries:
    try:
        results = vectorstore.similarity_search(
            test["query"],
            k=3,
            filter=test["filter"]
        )
        status = "✓" if len(results) > 0 else "✗"
        print(f"{status} {test['description']}: {len(results)} docs encontrados")
    except Exception as e:
        print(f"✗ {test['description']}: ERRO - {str(e)[:50]}")

# ==============================================================================
# TESTE 6: EDGE CASES
# ==============================================================================

print("\n" + "="*80)
print("⚠️  TESTE 6: Edge Cases e Robustez")
print("="*80)

edge_cases = [
    ("", "Query vazia"),
    ("xxxxxxxxxxxxxxx", "Query sem sentido"),
    ("123456789", "Apenas números"),
    ("@#$%^&*()", "Caracteres especiais"),
    ("a", "Query muito curta"),
    ("diabetes " * 100, "Query muito longa (repetitiva)"),
]

print("\nTestando robustez com edge cases...\n")

for query, description in edge_cases:
    try:
        results = vectorstore.similarity_search(query[:1000], k=1)  # Limitar tamanho
        status = "✓"
        print(f"{status} {description}: OK ({len(results)} results)")
    except Exception as e:
        print(f"✗ {description}: ERRO - {str(e)[:50]}")

# ==============================================================================
# TESTE 7: PERFORMANCE COM METADADOS
# ==============================================================================

print("\n" + "="*80)
print("⚡ TESTE 7: Performance (Latência com Metadados)")
print("="*80)

import time

queries_performance = [
    "diabetes tipo 2",
    "tratamento com metformina",
    "HbA1c elevada"
]

print("\nMedindo latência de queries...\n")

latencies = []
for query in queries_performance:
    start = time.time()
    results = vectorstore.similarity_search(query, k=5)
    latency = (time.time() - start) * 1000  # ms
    latencies.append(latency)

    print(f"  '{query}': {latency:.0f}ms ({len(results)} docs)")

avg_latency = sum(latencies) / len(latencies)
print(f"\n✓ Latência média: {avg_latency:.0f}ms")

if avg_latency < 500:
    print("  ✓ EXCELENTE: Latência < 500ms")
elif avg_latency < 1000:
    print("  ✓ BOM: Latência < 1s")
else:
    print("  ⚠️  ATENÇÃO: Latência alta, considere otimização")

# ==============================================================================
# TESTE 8: COMPARAÇÃO METADATA FIELDS
# ==============================================================================

print("\n" + "="*80)
print("📋 TESTE 8: Análise de Campos de Metadata Disponíveis")
print("="*80)

# Pegar uma amostra maior para análise
sample_docs = vectorstore.similarity_search("", k=20)

metadata_fields = {}
for doc in sample_docs:
    for field in doc.metadata.keys():
        if field not in metadata_fields:
            metadata_fields[field] = 0
        metadata_fields[field] += 1

print(f"\nCampos de metadata encontrados ({len(metadata_fields)} tipos):\n")

# Separar por categoria
basic_fields = ['doc_id', 'pdf_id', 'source', 'type', 'index', 'page_number', 'uploaded_at']
contextual_fields = ['section', 'document_type', 'summary']
enriched_fields = ['keywords', 'keywords_str', 'entities_diseases', 'entities_medications',
                   'entities_procedures', 'has_medical_entities', 'measurements', 'has_measurements']

print("BÁSICOS:")
for field in basic_fields:
    count = metadata_fields.get(field, 0)
    coverage = (count / len(sample_docs)) * 100
    print(f"  {field:20s}: {count:2d}/{len(sample_docs)} ({coverage:.0f}%)")

print("\nCONTEXTUAIS:")
for field in contextual_fields:
    count = metadata_fields.get(field, 0)
    coverage = (count / len(sample_docs)) * 100
    print(f"  {field:20s}: {count:2d}/{len(sample_docs)} ({coverage:.0f}%)")

print("\nENRIQUECIDOS:")
for field in enriched_fields:
    count = metadata_fields.get(field, 0)
    coverage = (count / len(sample_docs)) * 100
    status = "✓" if count > 0 else "✗"
    print(f"  {status} {field:20s}: {count:2d}/{len(sample_docs)} ({coverage:.0f}%)")

# Outros campos não categorizados
other_fields = [f for f in metadata_fields.keys()
                if f not in basic_fields + contextual_fields + enriched_fields]
if other_fields:
    print("\nOUTROS:")
    for field in other_fields:
        count = metadata_fields.get(field, 0)
        print(f"  {field:20s}: {count:2d}/{len(sample_docs)}")

# ==============================================================================
# RELATÓRIO FINAL
# ==============================================================================

print("\n" + "="*80)
print("📊 RELATÓRIO FINAL - METADATA ENRICHMENT STRESS TEST")
print("="*80)

print(f"""
✅ RESUMO DOS TESTES:

1. Verificação de Metadados:
   - Documentos analisados: {stats['total_docs']}
   - Com keywords: {stats['with_keywords']} ({stats['with_keywords']/stats['total_docs']*100:.0f}%)
   - Com entidades: {stats['with_entities']} ({stats['with_entities']/stats['total_docs']*100:.0f}%)
   - Com medições: {stats['with_measurements']} ({stats['with_measurements']/stats['total_docs']*100:.0f}%)

2. Diversidade de Metadados:
   - Keywords únicas: {len(stats['unique_keywords'])}
   - Doenças únicas: {len(stats['unique_diseases'])}
   - Medicamentos únicos: {len(stats['unique_medications'])}
   - Procedimentos únicos: {len(stats['unique_procedures'])}

3. Performance:
   - Latência média: {avg_latency:.0f}ms
   - Status: {'✓ EXCELENTE' if avg_latency < 500 else '✓ BOM' if avg_latency < 1000 else '⚠️ ATENÇÃO'}

4. Cobertura de Campos:
   - Campos básicos: {len([f for f in basic_fields if f in metadata_fields])}/{len(basic_fields)}
   - Campos contextuais: {len([f for f in contextual_fields if f in metadata_fields])}/{len(contextual_fields)}
   - Campos enriquecidos: {len([f for f in enriched_fields if f in metadata_fields])}/{len(enriched_fields)}
""")

if has_enriched:
    print("✅ METADATA ENRICHMENT ESTÁ ATIVO E FUNCIONANDO!")
    print("\n💡 PRÓXIMOS PASSOS:")
    print("   1. Re-processar todos os PDFs antigos para adicionar metadados enriquecidos")
    print("   2. Implementar Self-Query Retriever para filtros automáticos")
    print("   3. Criar dashboard de analytics de metadados")
else:
    print("⚠️  METADATA ENRICHMENT NÃO DETECTADO NOS DOCUMENTOS!")
    print("\n📝 AÇÃO NECESSÁRIA:")
    print("   1. Reprocessar PDFs com: python3 adicionar_pdf.py 'content/artigo.pdf'")
    print("   2. Verificar se metadata_extractors.py está sendo importado")
    print("   3. Re-rodar este teste após reprocessamento")

print("\n" + "="*80)
print("✅ TESTE CONCLUÍDO!")
print("="*80)
print()
