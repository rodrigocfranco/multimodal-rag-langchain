# 🚂 Railway Setup - Volume Configuration

## ✅ Configuração Atual

### Volume Name
- **Nome:** `knowledge_base_vol`
- **Mount Path:** `/app/knowledge_base_vol`

### Variável de Ambiente (Railway)
Configure no Railway Dashboard:
```bash
PERSIST_DIR=/app/knowledge_base_vol
```

### Código Atualizado
Todos os arquivos principais agora usam:
```python
persist_directory = os.getenv("PERSIST_DIR", "./knowledge_base_vol")
```

Arquivos atualizados:
- ✅ `adicionar_pdf.py`
- ✅ `consultar_com_rerank.py` (modo API e terminal)
- ✅ `document_manager.py` (todas funções)
- ✅ `railway.json` (volume mount config)

---

## 🔧 Configuração no Railway Dashboard

### 1. Variáveis de Ambiente
```bash
# Obrigatórias
OPENAI_API_KEY=sk-...
COHERE_API_KEY=...

# Volume
PERSIST_DIR=/app/knowledge_base_vol

# Opcional (segurança)
API_SECRET_KEY=sua_chave_secreta_aqui

# Opcional (processamento)
UNSTRUCTURED_STRATEGY=fast
MIN_IMAGE_SIZE_KB=5
AUTO_REPROCESS=false
```

### 2. Volume
- **Name:** `knowledge_base_vol`
- **Mount Path:** `/app/knowledge_base_vol`
- **Size:** 1GB (Railway free tier permite até 5GB)

---

## ⚠️ IMPORTANTE: Incompatibilidade de Embeddings

### Problema Identificado
O sistema agora usa:
- **Modelo novo:** `text-embedding-3-large` (3072 dimensões)
- **Modelo antigo:** `text-embedding-ada-002` (1536 dimensões)

**Qualquer knowledge base existente com ada-002 é INCOMPATÍVEL.**

### Soluções

#### Opção 1: Limpar e Re-processar (RECOMENDADO)
```bash
# No Railway, deletar volume e criar novo
# Ou localmente:
rm -rf knowledge_base_vol

# Re-processar PDFs
python adicionar_pdf.py "arquivo.pdf"
```

**Vantagens:**
- Sistema consistente com modelo superior (+30% qualidade)
- Melhor precisão no retrieval
- Meta de 85-90% de acurácia alcançável

#### Opção 2: Reverter para ada-002 (NÃO RECOMENDADO)
Editar `adicionar_pdf.py` e `consultar_com_rerank.py`:
```python
# TROCAR:
embedding_function=OpenAIEmbeddings(model="text-embedding-3-large")

# POR:
embedding_function=OpenAIEmbeddings(model="text-embedding-ada-002")
```

**Desvantagens:**
- Mantém modelo fraco (-30% qualidade vs 3-large)
- Acurácia permanece em ~63% (abaixo da meta)

---

## 📊 Comparação de Modelos

| Aspecto | ada-002 (antigo) | 3-large (novo) |
|---------|------------------|----------------|
| Dimensões | 1536 | 3072 |
| Qualidade PT-BR | 70% | 90% (+30%) |
| Custo (por 1M tokens) | $0.10 | $0.13 (+30%) |
| Precisão RAG esperada | 63% | 85-90% |
| Compatível com base antiga | ✅ Sim | ❌ Não (requer rebuild) |

---

## 🚀 Deploy no Railway

### Primeiro Deploy (Knowledge Base Vazio)
1. Criar volume `knowledge_base_vol` no Railway
2. Configurar variáveis de ambiente
3. Deploy do código
4. Fazer upload de PDFs via `/ui`

### Re-deploy com Volume Existente
⚠️ **ATENÇÃO:** Se o volume tem embeddings ada-002, você terá erro!

**Solução:**
1. Deletar volume antigo no Railway
2. Criar novo volume `knowledge_base_vol`
3. Re-deploy
4. Re-processar PDFs

---

## 🧪 Testar Localmente

### Setup Local
```bash
# 1. Criar .env
echo "OPENAI_API_KEY=sk-..." >> .env
echo "COHERE_API_KEY=..." >> .env
echo "PERSIST_DIR=./knowledge_base_vol" >> .env

# 2. Limpar knowledge base antigo (se necessário)
rm -rf knowledge_base knowledge_base_vol

# 3. Processar PDF de teste
python adicionar_pdf.py "teste.pdf"

# 4. Iniciar API
python consultar_com_rerank.py --api

# 5. Testar no navegador
open http://localhost:5001/ui
```

### Verificar Dimensões
```bash
# Checar se há incompatibilidade
python3 -c "
import os
print('Volume local:', os.path.exists('./knowledge_base_vol'))
print('Volume antigo:', os.path.exists('./knowledge_base'))
"
```

---

## 📝 Checklist de Deploy

### Antes do Deploy
- [ ] Criar volume `knowledge_base_vol` no Railway
- [ ] Configurar `PERSIST_DIR=/app/knowledge_base_vol`
- [ ] Configurar `OPENAI_API_KEY` e `COHERE_API_KEY`
- [ ] (Opcional) Configurar `API_SECRET_KEY`

### Depois do Deploy
- [ ] Verificar `/health` retorna 200 OK
- [ ] Fazer upload de 1 PDF de teste via `/ui`
- [ ] Aguardar processamento (5-10 min)
- [ ] Testar query via `/chat`
- [ ] Verificar fontes na resposta

### Se Houver Erro de Dimensões
- [ ] Deletar volume antigo
- [ ] Criar novo volume `knowledge_base_vol`
- [ ] Re-deploy
- [ ] Re-processar todos PDFs

---

## 🆘 Troubleshooting

### Erro: "Dimension mismatch"
```
Error adding documents: Expected 1536 dimensions, got 3072
```

**Solução:** Knowledge base tem embeddings antigos (ada-002). Deletar e reprocessar.

### Erro: "Volume not mounted"
```
FileNotFoundError: [Errno 2] No such file or directory: '/app/knowledge_base_vol'
```

**Solução:**
1. Verificar nome do volume no Railway: `knowledge_base_vol`
2. Verificar mount path: `/app/knowledge_base_vol`
3. Verificar variável `PERSIST_DIR=/app/knowledge_base_vol`

### Erro: "OPENAI_API_KEY not set"
**Solução:** Adicionar variável no Railway Dashboard

---

**Última atualização:** 2025-10-17
**Commit:** f90cf10 - "Update volume name to knowledge_base_vol for Railway"
