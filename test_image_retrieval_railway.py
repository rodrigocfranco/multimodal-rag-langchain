#!/usr/bin/env python3
"""
🔍 TESTE DE RETRIEVAL DE IMAGENS - RAILWAY
Verifica se imagens estão sendo recuperadas corretamente

Uso: railway run python3 test_image_retrieval_railway.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

PERSIST_DIR = os.getenv("PERSIST_DIR", "./knowledge")

print("=" * 80)
print("🔍 TESTE DE RETRIEVAL DE IMAGENS")
print("=" * 80)

# ===========================================================================
# 1. VERIFICAR SE HÁ IMAGENS NO VECTORSTORE
# ===========================================================================
print("\n[1/4] Verificando imagens no vectorstore...")

try:
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
        persist_directory=PERSIST_DIR
    )

    # Buscar TODAS as imagens
    all_images = vectorstore.similarity_search(
        "",
        k=1000,
        filter={"type": "image"}
    )

    print(f"   ✓ Total de imagens no vectorstore: {len(all_images)}")

    if len(all_images) == 0:
        print("\n   ❌ PROBLEMA: Nenhuma imagem encontrada!")
        print("   → Imagens não foram processadas ou não têm type='image'")
        exit(1)

    # Mostrar sample
    print(f"\n   📋 Amostra de imagens:")
    for i, img in enumerate(all_images[:5], 1):
        source = img.metadata.get('source', 'unknown')
        doc_id = img.metadata.get('doc_id', 'N/A')
        summary = img.page_content[:150].replace('\n', ' ')
        print(f"   [{i}] {source}")
        print(f"       ID: {doc_id}")
        print(f"       Descrição: {summary}...")
        print()

except Exception as e:
    print(f"   ✗ Erro: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

# ===========================================================================
# 2. TESTAR QUERY ESPECÍFICA (a do usuário)
# ===========================================================================
print("\n[2/4] Testando query específica...")

query = "explique a figura 1 do documento manejo de hiperglicemia hospitalar no doente não crítico"
print(f"   Query: '{query}'")

# Buscar com similarity_search (sem filtro)
results_all = vectorstore.similarity_search(query, k=30)
print(f"   ✓ Total de resultados (top-30): {len(results_all)}")

# Contar tipos
types_count = {}
for doc in results_all:
    doc_type = doc.metadata.get('type', 'unknown')
    types_count[doc_type] = types_count.get(doc_type, 0) + 1

print(f"   Distribuição por tipo:")
for t, count in sorted(types_count.items()):
    print(f"      {t}: {count}")

# Verificar se há imagens nos resultados
image_results = [r for r in results_all if r.metadata.get('type') == 'image']
print(f"\n   {'✓' if image_results else '✗'} Imagens nos top-30: {len(image_results)}")

if image_results:
    print(f"\n   📸 Imagens encontradas:")
    for i, img in enumerate(image_results, 1):
        source = img.metadata.get('source', 'unknown')
        summary = img.page_content[:150].replace('\n', ' ')
        print(f"   [{i}] {source}")
        print(f"       Descrição: {summary}...")
else:
    print(f"\n   ❌ PROBLEMA: Nenhuma imagem nos top-30 resultados!")
    print(f"   → Query não está fazendo match com descrições das imagens")

# ===========================================================================
# 3. TESTAR QUERY ALTERNATIVA (mais genérica)
# ===========================================================================
print("\n[3/4] Testando query alternativa...")

query_alt = "figura fluxograma algoritmo imagem hiperglicemia"
print(f"   Query: '{query_alt}'")

results_alt = vectorstore.similarity_search(query_alt, k=30)
image_results_alt = [r for r in results_alt if r.metadata.get('type') == 'image']

print(f"   {'✓' if image_results_alt else '✗'} Imagens nos top-30: {len(image_results_alt)}")

if image_results_alt:
    print(f"\n   📸 Imagens encontradas:")
    for i, img in enumerate(image_results_alt[:3], 1):
        source = img.metadata.get('source', 'unknown')
        summary = img.page_content[:150].replace('\n', ' ')
        print(f"   [{i}] {source}")
        print(f"       Descrição: {summary}...")

# ===========================================================================
# 4. VERIFICAR DOCSTORE
# ===========================================================================
print("\n[4/4] Verificando docstore...")

import pickle

docstore_path = f"{PERSIST_DIR}/docstore.pkl"
if os.path.exists(docstore_path):
    with open(docstore_path, 'rb') as f:
        docstore = pickle.load(f)

    print(f"   ✓ Docstore existe: {len(docstore)} entradas")

    # Contar imagens (base64)
    from base64 import b64decode
    image_count = 0
    for doc_id, content in docstore.items():
        if isinstance(content, str):
            try:
                decoded = b64decode(content[:100])
                if decoded.startswith(b'\xff\xd8\xff') or decoded.startswith(b'\x89PNG'):
                    image_count += 1
            except:
                pass

    print(f"   ✓ Imagens no docstore: {image_count}")

    if image_count != len(all_images):
        print(f"\n   ⚠️  ALERTA: Discrepância!")
        print(f"      Vectorstore: {len(all_images)} imagens")
        print(f"      Docstore: {image_count} imagens")
        print(f"      → Alguns doc_ids podem não estar mapeados corretamente")
else:
    print(f"   ✗ Docstore não encontrado!")

# ===========================================================================
# DIAGNÓSTICO FINAL
# ===========================================================================
print("\n" + "=" * 80)
print("📋 DIAGNÓSTICO")
print("=" * 80)

if len(all_images) == 0:
    print("\n❌ CRÍTICO: Nenhuma imagem processada")
    print("   Solução: Reprocessar PDFs com adicionar_pdf.py")

elif len(image_results) == 0:
    print("\n❌ PROBLEMA: Imagens existem mas não são recuperadas")
    print(f"   • Total de imagens: {len(all_images)}")
    print(f"   • Imagens recuperadas: 0")
    print("\n   Possíveis causas:")
    print("   1. Descrições das imagens não fazem match com a query")
    print("   2. Embeddings das imagens estão muito distantes da query")
    print("   3. Reranker está descartando imagens")
    print("\n   Soluções:")
    print("   • Melhorar descrições das imagens (GPT-4o Vision prompt)")
    print("   • Adicionar keywords explícitas: 'FIGURA', 'ALGORITMO'")
    print("   • Aumentar k no retriever (30 → 50)")
    print("   • Verificar se Cohere rerank está preservando imagens")

elif len(image_results) > 0 and len(image_results_alt) == 0:
    print("\n⚠️  PARCIAL: Imagens recuperadas com query original mas não com alternativa")
    print("   → Descrições são muito específicas (bom!)")

elif len(image_results) > 0:
    print("\n✅ FUNCIONANDO: Imagens sendo recuperadas!")
    print(f"   • Total de imagens: {len(all_images)}")
    print(f"   • Imagens recuperadas: {len(image_results)}")
    print("\n   ⚠️  MAS o sistema respondeu: 'A informação solicitada não está presente'")
    print("\n   Possíveis causas:")
    print("   1. Imagens recuperadas mas DEPOIS do rerank (Cohere)")
    print("   2. GPT-4o não consegue ler as imagens (problema de conversão)")
    print("   3. Prompt do sistema está muito restritivo")
    print("\n   Próximo teste:")
    print("   • Verificar endpoint /debug-retrieval com esta query")
    print("   • Ver se imagens sobrevivem ao rerank")

print("\n" + "=" * 80)
