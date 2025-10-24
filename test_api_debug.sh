#!/bin/bash
# Teste do endpoint de debug para verificar retrieval de imagens

API_URL="https://comfortable-tenderness-production.up.railway.app"

echo "==================================================================="
echo "🔍 TESTE DE DEBUG-RETRIEVAL - IMAGENS"
echo "==================================================================="

echo ""
echo "[1/3] Testando query sobre figura..."
curl -X POST "${API_URL}/debug-retrieval" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"explique a figura 1 do documento manejo de hiperglicemia hospitalar no doente não crítico\"}" \
  2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Query: {data.get('query', 'N/A')}\")
print(f\"\\nRaw retrieval:\")
print(f\"  Total: {data.get('raw_retrieval', {}).get('count', 0)}\")
print(f\"\\nReranked:\")
reranked = data.get('reranked', {})
print(f\"  Total: {reranked.get('count', 0)}\")

# Verificar se há imagens
docs_full = reranked.get('docs_full', [])
image_count = 0
for doc in docs_full:
    if doc.get('metadata', {}).get('type') == 'image':
        image_count += 1
        print(f\"\\n  📸 IMAGEM ENCONTRADA:\")
        print(f\"     Source: {doc.get('metadata', {}).get('source', 'unknown')}\")
        print(f\"     Content (preview): {doc.get('content', '')[:200]}...\")

print(f\"\\n✓ Total de imagens nos resultados rerankeados: {image_count}\")

if image_count == 0:
    print(f\"\\n❌ PROBLEMA: Nenhuma imagem nos resultados finais!\")
"

echo ""
echo "==================================================================="
echo "[2/3] Testando query genérica sobre imagens..."
curl -X POST "${API_URL}/debug-retrieval" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"figura algoritmo fluxograma imagem\"}" \
  2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
reranked = data.get('reranked', {})
docs_full = reranked.get('docs_full', [])
image_count = sum(1 for doc in docs_full if doc.get('metadata', {}).get('type') == 'image')
print(f\"Imagens recuperadas: {image_count}/{reranked.get('count', 0)}\")
"

echo ""
echo "==================================================================="
echo "[3/3] Verificando total de imagens no sistema..."
curl -X GET "${API_URL}/debug-volume" \
  2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)

# Verificar se teste de busca retornou algo
test_search = data.get('test_search_count', 0)
print(f\"Documentos no vectorstore: {data.get('chroma_count', 'N/A')}\")
print(f\"Teste de busca ('diabetes'): {test_search} resultados\")

# Verificar docstore
print(f\"\\nDocstore:")
print(f\"  Existe: {data.get('docstore_exists', False)}\")
print(f\"  Tamanho: {data.get('docstore_size', 0)} entradas\")
"

echo ""
echo "==================================================================="
