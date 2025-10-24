#!/bin/bash
# Script para limpar cache do retriever na Railway

API_URL="https://comfortable-tenderness-production.up.railway.app"

echo "=============================================="
echo "🗑️ LIMPANDO CACHE DO RETRIEVER"
echo "=============================================="
echo ""
echo "Conectando a: $API_URL"
echo ""

response=$(curl -X POST "${API_URL}/clear-cache" \
  -H "Content-Type: application/json" \
  -s -w "\n%{http_code}")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo "✅ SUCESSO!"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
else
    echo "❌ ERRO (HTTP $http_code)"
    echo "$body"
fi

echo ""
echo "=============================================="
