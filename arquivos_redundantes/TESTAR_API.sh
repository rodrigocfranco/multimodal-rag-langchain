#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════════════"
echo "  🧪 TESTE DA API REST - Sistema RAG"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Verificando se a API está rodando..."
echo ""

# Health check
echo "${YELLOW}1. Health Check:${NC}"
curl -s http://localhost:5000/health | python3 -m json.tool
echo ""
echo ""

# Listar vectorstores
echo "${YELLOW}2. Listar Vectorstores:${NC}"
curl -s http://localhost:5000/vectorstores | python3 -m json.tool
echo ""
echo ""

# Query simples
echo "${YELLOW}3. Query Simples (para n8n):${NC}"
echo "Pergunta: 'What is the main topic?'"
curl -s -X POST http://localhost:5000/query-simple \
  -H "Content-Type: application/json" \
  -d '{
    "vectorstore": "attention",
    "question": "What is the main topic?"
  }' | python3 -m json.tool
echo ""
echo ""

# Query completa
echo "${YELLOW}4. Query Completa (com fontes):${NC}"
echo "Pergunta: 'Who are the authors?'"
curl -s -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "vectorstore": "attention",
    "question": "Who are the authors?",
    "include_sources": true
  }' | python3 -m json.tool

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "${GREEN}✅ Testes concluídos!${NC}"
echo "═══════════════════════════════════════════════════════════════════════════"

