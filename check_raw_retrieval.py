#!/usr/bin/env python3
"""Verificar se imagens estão no raw retrieval"""

import requests
import json

API_URL = "https://comfortable-tenderness-production.up.railway.app"

response = requests.post(
    f"{API_URL}/debug-retrieval",
    json={"question": "figura 1 hiperglicemia"}
)

data = response.json()

raw_docs = data.get('raw_retrieval', {}).get('docs_full', [])
print(f'=== RAW RETRIEVAL (antes do rerank) ===')
print(f'Total: {len(raw_docs)} documentos\n')

image_count = 0
for i, doc in enumerate(raw_docs):
    doc_type = doc.get('metadata', {}).get('type', 'unknown')
    if doc_type == 'image':
        image_count += 1
        source = doc.get('metadata', {}).get('source', 'unknown')
        content_preview = doc.get('content', '')[:150]
        print(f'[{i+1}] IMAGEM')
        print(f'    Source: {source}')
        print(f'    Content: {content_preview}...\n')

print(f'✓ Imagens no RAW: {image_count}/{len(raw_docs)}')

# Reranked
reranked_docs = data.get('reranked', {}).get('docs_full', [])
image_count_reranked = sum(1 for d in reranked_docs if d.get('metadata', {}).get('type') == 'image')
print(f'✓ Imagens após RERANK: {image_count_reranked}/{len(reranked_docs)}')

if image_count > 0 and image_count_reranked == 0:
    print(f'\n❌ PROBLEMA CONFIRMADO: Cohere Rerank está descartando TODAS as imagens!')
    print(f'\n💡 SOLUÇÃO:')
    print(f'   1. Desabilitar rerank para imagens')
    print(f'   2. OU melhorar descrições das imagens')
    print(f'   3. OU forçar inclusão de imagens após rerank')
elif image_count == 0:
    print(f'\n❌ PROBLEMA: Nenhuma imagem no raw retrieval!')
    print(f'   → Imagens não estão sendo indexadas ou query não faz match')
