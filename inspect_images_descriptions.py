#!/usr/bin/env python3
"""
Inspecionar descrições das imagens para entender o problema
"""

import requests
import json

API_URL = "https://comfortable-tenderness-production.up.railway.app"

print("=" * 80)
print("🔍 INSPEÇÃO DAS DESCRIÇÕES DE IMAGENS")
print("=" * 80)

# Fazer query genérica sobre imagens para forçar busca
response = requests.post(
    f"{API_URL}/debug-retrieval",
    json={"question": "existe algum fluxograma sobre hiperglicemia"}
)

if response.status_code != 200:
    print(f"Erro: {response.status_code}")
    exit(1)

data = response.json()

print(f"\n📊 Resultados da query 'existe algum fluxograma sobre hiperglicemia':")
print(f"   Raw retrieval: {data.get('raw_retrieval', {}).get('count', 0)} documentos")
print(f"   Reranked: {data.get('reranked', {}).get('count', 0)} documentos")

# Analisar documentos rerankeados (os que chegam ao LLM)
reranked_docs = data.get('reranked', {}).get('docs_full', [])

print(f"\n🖼️ Imagens nos resultados RERANKEADOS:")
image_count = 0
for i, doc in enumerate(reranked_docs):
    if doc.get('metadata', {}).get('type') == 'image':
        image_count += 1
        source = doc.get('metadata', {}).get('source', 'unknown')
        content = doc.get('content', '')

        print(f"\n[IMAGEM {image_count}]")
        print(f"   Source: {source}")
        print(f"   Índice: {doc.get('metadata', {}).get('index', 'N/A')}")
        print(f"   Doc ID: {doc.get('metadata', {}).get('doc_id', 'N/A')[:16]}...")
        print(f"\n   Descrição completa:")
        print(f"   {'-' * 76}")

        # Mostrar descrição inteira (pode ser longa)
        lines = content.split('\n')
        for line in lines[:20]:  # Primeiras 20 linhas
            print(f"   {line}")

        if len(lines) > 20:
            print(f"   ... ({len(lines) - 20} linhas adicionais)")

        print(f"   {'-' * 76}")

print(f"\n✓ Total de imagens encontradas: {image_count}")

if image_count == 0:
    print("\n❌ PROBLEMA: Nenhuma imagem chegou aos resultados rerankeados!")
    print("   → O Cohere Rerank está descartando as imagens")
    print("   → OU as imagens não estão sendo forçadas corretamente")

print("\n" + "=" * 80)
