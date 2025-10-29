#!/bin/bash
#
# Script para verificar atualizações de dependências
# Uso: ./check_updates.sh
#

set -e

echo "=================================="
echo "🔍 Verificando atualizações..."
echo "=================================="
echo ""

# Verificar se pip-tools está instalado
if ! command -v pip-compile &> /dev/null; then
    echo "⚠️  pip-tools não encontrado. Instalando..."
    pip install pip-tools
fi

echo "📦 Pacotes desatualizados:"
echo ""
pip list --outdated --format=columns

echo ""
echo "=================================="
echo "💡 Dicas:"
echo "=================================="
echo ""
echo "Para atualizar um pacote específico:"
echo "  pip install --upgrade nome-do-pacote"
echo ""
echo "Para atualizar TODOS dentro das restrições do requirements.txt:"
echo "  pip install --upgrade -r requirements.txt"
echo ""
echo "Para ver detalhes de um pacote:"
echo "  pip show nome-do-pacote"
echo ""
echo "⚠️  IMPORTANTE: Teste bem antes de fazer commit!"
echo ""
