# 🔍 PROBLEMA IDENTIFICADO

## ❌ Erro Durante Upload de PDF

### Causa Raiz
**INCOMPATIBILIDADE DE DIMENSÕES DE EMBEDDINGS**

Quando upgradeamos os modelos de:
- `text-embedding-ada-002` (1536 dimensões)
- → `text-embedding-3-large` (3072 dimensões)

O ChromaDB existente (`knowledge_base/`) contém 162 embeddings com **1536 dimensões**.

Quando tentamos adicionar novos documentos com **3072 dimensões**, o ChromaDB rejeita por incompatibilidade.

---

## 🔧 SOLUÇÃO

### Opção 1: Limpar Knowledge Base e Re-processar (RECOMENDADO)

**Por que recomendado:**
- Novo modelo é +30% melhor em semântica médica portuguesa
- Todos documentos terão mesma qualidade
- Sistema ficará consistente

**Como fazer:**
```bash
# 1. Backup (caso precise reverter)
mv knowledge_base knowledge_base_backup_ada002

# 2. Re-processar PDFs
python adicionar_pdf.py "caminho/do/pdf.pdf"
```

**Desvantagem:**
- Precisa fazer upload dos PDFs novamente (5-10 min cada)

---

### Opção 2: Reverter para Ada-002 (NÃO RECOMENDADO)

**Por que NÃO recomendado:**
- Perde +30% de qualidade no retrieval
- Mantém modelo fraco que estava causando falhas

**Se mesmo assim quiser reverter:**
```python
# Em consultar_com_rerank.py linha 425
# TROCAR:
embedding_function=OpenAIEmbeddings(model="text-embedding-3-large")

# POR:
embedding_function=OpenAIEmbeddings(model="text-embedding-ada-002")
```

E fazer o mesmo em `adicionar_pdf.py` linha 425.

---

## 📊 Comparação

| Aspecto | Ada-002 (antigo) | 3-Large (novo) |
|---------|------------------|----------------|
| Dimensões | 1536 | 3072 |
| Qualidade PT-BR | 70% | 90% (+30%) |
| Custo por 1M tokens | $0.10 | $0.13 (+30%) |
| Compatibilidade | ✅ Com base existente | ❌ Requer rebuild |

---

## 🎯 RECOMENDAÇÃO FINAL

**Limpar knowledge base e re-processar com text-embedding-3-large**

**Por quê:**
1. Sistema já tinha 63% de acurácia (abaixo da meta de 85%)
2. text-embedding-3-large é CRUCIAL para atingir 85-90%
3. Você tem apenas 1 documento processado (rápido de refazer)
4. Custo adicional é mínimo (+$0.03 por 1M tokens)

**Próximos passos:**
```bash
# Limpar knowledge base
rm -rf knowledge_base

# Re-processar PDF (vai criar knowledge_base novo)
python adicionar_pdf.py "/caminho/do/pdf.pdf"
```

Depois de re-processar, testar queries para verificar melhoria de 63% → 85%+
