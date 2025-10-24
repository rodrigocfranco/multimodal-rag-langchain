#!/bin/bash
# Script para processar PDF diretamente no Railway (evita timeout HTTP)

if [ -z "$1" ]; then
    echo "Uso: ./processar_pdf_railway.sh <caminho_do_pdf>"
    echo "Exemplo: ./processar_pdf_railway.sh '/app/content/documento.pdf'"
    exit 1
fi

PDF_PATH="$1"

echo "=============================================="
echo "📄 Processando PDF no Railway"
echo "=============================================="
echo "Arquivo: $PDF_PATH"
echo ""

# Executar via railway run (executa no servidor Railway)
railway run python3 adicionar_pdf.py "$PDF_PATH"

echo ""
echo "=============================================="
echo "✅ Processamento concluído!"
echo "=============================================="
echo ""
echo "Verifique em: https://seu-app.railway.app/manage"
