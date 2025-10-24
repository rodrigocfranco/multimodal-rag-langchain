#!/bin/bash
# Remove documento deletado do vectorstore na Railway

echo "=============================================="
echo "🗑️ LIMPANDO DOCUMENTO DELETADO"
echo "=============================================="
echo ""
echo "Executando no Railway..."
echo ""

railway run python3 fix_deleted_doc.py

echo ""
echo "=============================================="
echo "🔄 LIMPANDO CACHE DO RETRIEVER"
echo "=============================================="
echo ""

curl -X POST https://comfortable-tenderness-production.up.railway.app/clear-cache \
  -H "Content-Type: application/json" \
  -s | python3 -m json.tool 2>/dev/null

echo ""
echo "=============================================="
echo "✅ CONCLUÍDO!"
echo "=============================================="
echo ""
echo "Teste novamente no /chat"
echo ""
