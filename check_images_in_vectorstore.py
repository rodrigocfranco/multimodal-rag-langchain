#!/usr/bin/env python3
"""Verificar quantas imagens existem no vectorstore"""

import requests
import json

API_URL = "https://comfortable-tenderness-production.up.railway.app"

# Usar endpoint de debug-volume
response = requests.get(f"{API_URL}/debug-volume")
data = response.json()

print("=" * 80)
print("🔍 VERIFICAÇÃO DE IMAGENS NO VECTORSTORE")
print("=" * 80)

print(f"\n📊 Status geral:")
print(f"   ChromaDB count: {data.get('chroma_count', 'N/A')}")
print(f"   Docstore existe: {data.get('docstore_exists', False)}")
print(f"   Docstore size: {data.get('docstore_size', 0)} entradas")

# Fazer busca direta por imagens
print(f"\n🔍 Buscando imagens com filtro type='image'...")

# Como não temos acesso direto ao vectorstore, vamos tentar queries variadas
queries_test = [
    "figura",
    "imagem",
    "fluxograma",
    "algoritmo",
    "diagrama",
    "gráfico"
]

for query in queries_test:
    response = requests.post(
        f"{API_URL}/debug-retrieval",
        json={"question": query}
    )

    if response.status_code == 200:
        result = response.json()
        raw_docs = result.get('raw_retrieval', {}).get('docs_full', [])

        # Contar imagens
        image_count = sum(1 for d in raw_docs if d.get('metadata', {}).get('type') == 'image')

        print(f"   Query '{query}': {image_count} imagens nos top-30")

        if image_count > 0:
            print(f"      ✓ IMAGENS ENCONTRADAS!")
            for d in raw_docs:
                if d.get('metadata', {}).get('type') == 'image':
                    source = d.get('metadata', {}).get('source', 'unknown')
                    summary = d.get('content', '')[:100]
                    print(f"         • {source}: {summary}...")
            break
    else:
        print(f"   Query '{query}': erro {response.status_code}")

print("\n" + "=" * 80)
