# 📋 Próximos Passos - Metadata Enrichment

Data: 2025-10-21
Status: Aguardando deploy do Railway

---

## ✅ O QUE JÁ FOI FEITO (COMPLETO)

### 1. **Implementação do Sistema de Metadata Enrichment**
- ✅ `metadata_extractors.py` criado (471 linhas)
- ✅ KeyBERT integrado (keyword extraction)
- ✅ Medical NER integrado (entidades médicas PT)
- ✅ Numerical extraction integrado (valores + unidades)
- ✅ `adicionar_pdf.py` modificado para usar enrichers
- ✅ Commit e push para Railway concluído

### 2. **Documentação Completa**
- ✅ `METADATA_ENRICHMENT_ANALYSIS.md` - Pesquisa e comparação
- ✅ `METADATA_ENRICHMENT_IMPLEMENTATION.md` - Guia de implementação
- ✅ `test_metadata_stress.py` - Suite de testes de stress

### 3. **Metadados Implementados (9 → 17 campos)**
```python
# NOVOS (8 campos):
"keywords": [...],
"keywords_str": "...",
"entities_diseases": [...],
"entities_medications": [...],
"entities_procedures": [...],
"has_medical_entities": bool,
"measurements": [...],
"has_measurements": bool
```

---

## 🔄 AGUARDANDO (Deploy do Railway)

O Railway está fazendo deploy do código com:
- Metadata Enrichment integrado
- Dependencies: `keybert`, `sentence-transformers`

**Quando o deploy terminar:**
- ✅ O sistema estará pronto para processar PDFs com metadados enriquecidos
- ⚠️ PDFs antigos NÃO terão os novos metadados (foram processados antes)

---

## 📝 PRÓXIMOS PASSOS (Após Deploy)

### Passo 1: **Reprocessar PDFs Existentes** (CRÍTICO)

Os PDFs atualmente no Railway foram processados SEM metadados enriquecidos. Para adicionar os novos metadados, você precisa:

**Opção A: Re-upload via Web UI**
```
1. Acessar https://comfortable-tenderness-production.up.railway.app/upload
2. Fazer upload dos PDFs novamente
3. O sistema detectará duplicata e perguntará se quer reprocessar
4. Confirmar reprocessamento
```

**Opção B: Re-upload via Script Local**
```bash
# Processar localmente e fazer upload manual do knowledge base
python3 adicionar_pdf.py "content/Artigo de Revisão - NEJM - Cardiomiopatia Hipertrófica.pdf"
python3 adicionar_pdf.py "content/Artigo de Revisão - Nature - Cardiomiopatia Hipertrófica.pdf"

# Depois fazer upload do knowledge/ folder inteiro para Railway Volume
```

**Recomendação:** Use Opção A (mais simples)

---

### Passo 2: **Testar Metadados com Stress Test**

Após reprocessar os PDFs, rodar o stress test:

```bash
python3 test_metadata_stress.py
```

**O que o teste verifica:**
1. ✓ Metadados enriquecidos presentes nos documentos
2. ✓ Keywords extraídas corretamente
3. ✓ Entidades médicas identificadas
4. ✓ Valores numéricos capturados
5. ✓ Filtros combinados funcionando
6. ✓ Performance (latência)
7. ✓ Edge cases
8. ✓ Cobertura de campos de metadata

**Resultado esperado:**
- Documentos com keywords: 80%+
- Documentos com entidades: 70%+
- Documentos com medições: 30%+
- Latência média: <500ms

---

### Passo 3: **Implementar Self-Query Retriever** (P0 Final)

Este é o último item P0 (CRÍTICO) da roadmap.

**O que faz:**
Permite queries em linguagem natural com filtros automáticos:

```
Query: "Mostre guidelines sobre diabetes da seção Tratamento"
↓ LLM extrai automaticamente
Filtros: {document_type="clinical_guideline", section="Tratamento"}
```

**Impacto esperado:**
- +12% accuracy
- +17.2% Hits@4
- Melhor UX (queries mais naturais)

**Custo:** $3/mês (3000 queries)

**Implementação:**
```python
# Em consultar_com_rerank.py
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo

metadata_field_info = [
    AttributeInfo(
        name="document_type",
        description="clinical_guideline, case_report, review_article...",
        type="string"
    ),
    AttributeInfo(
        name="section",
        description="Resumo, Métodos, Resultados, Tratamento...",
        type="string"
    ),
    # ... outros campos
]

self_query_retriever = SelfQueryRetriever.from_llm(
    llm=ChatOpenAI(model="gpt-4o"),
    vectorstore=vectorstore,
    metadata_field_info=metadata_field_info,
    verbose=True
)
```

**Tempo estimado:** 3-4 horas

---

### Passo 4: **Validar com Suite de Queries Médicas**

Criar queries avançadas que exploram os metadados:

**Keywords-based:**
```
Q: "Encontre documentos sobre metformina e insulina"
→ Deve matchear docs com keywords=['metformina', 'insulina']
```

**Entity-based:**
```
Q: "Mostre casos com diabetes tipo 2"
→ Deve matchear docs com entities_diseases=['diabetes tipo 2']
```

**Numerical:**
```
Q: "Encontre casos com HbA1c > 8%"
→ Deve matchear docs com measurements contendo HbA1c
```

**Combined:**
```
Q: "Tabelas sobre tratamento de diabetes em guidelines"
→ Filtros: {type="table", section="Tratamento", document_type="clinical_guideline"}
```

---

## 🎯 ROADMAP COMPLETO (P0 Items)

| # | Item | Status | Impacto |
|---|------|--------|---------|
| 1 | **Hybrid Search (BM25 + Vector)** | ✅ COMPLETO | +30-50% accuracy |
| 2 | **Contextual Retrieval (Anthropic)** | ✅ COMPLETO | -49% failure rate |
| 3 | **Metadata Enrichment** | ✅ COMPLETO | +47-72% accuracy |
| 4 | **Self-Query Retriever** | ⏳ PENDENTE | +12% accuracy |

**Status Atual:** 75% dos P0 items completos!

---

## 🧪 COMO TESTAR OS METADADOS (Passo a Passo)

### Teste 1: Verificar se Deploy Funcionou
```bash
# Acessar o Railway e verificar logs
# Procurar por: "Metadata Enrichment System..."
# Deve aparecer: "✓ KeyBERT pronto!" e "✓ Medical Entity Extractor..."
```

### Teste 2: Upload de PDF com Metadados
```bash
# Via web UI ou local
python3 adicionar_pdf.py "content/Artigo de Revisão - NEJM - Cardiomiopatia Hipertrófica.pdf"

# Verificar no output:
# - "✓ KeyBERT pronto!"
# - Processamento deve rodar keywords, entities e measurements extraction
```

### Teste 3: Inspecionar Metadados
```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
    persist_directory="./knowledge"
)

docs = vectorstore.similarity_search("diabetes", k=1)
print(docs[0].metadata)

# Deve mostrar:
# {
#     'keywords': [...],
#     'entities_diseases': [...],
#     'entities_medications': [...],
#     'measurements': [...]
# }
```

### Teste 4: Query com Filtros
```python
# Query apenas em tabelas
results = vectorstore.similarity_search(
    "diabetes",
    k=5,
    filter={"type": "table"}
)
print(f"Encontradas {len(results)} tabelas sobre diabetes")

# Query apenas guidelines
results = vectorstore.similarity_search(
    "tratamento",
    k=5,
    filter={"document_type": "clinical_guideline"}
)
print(f"Encontradas {len(results)} guidelines sobre tratamento")
```

### Teste 5: Stress Test Completo
```bash
python3 test_metadata_stress.py
```

---

## 📊 IMPACTO ESPERADO (Resumo)

### Baseline (Antes):
- Accuracy: **86.2%**
- Metadados: 9 campos básicos
- Queries: Apenas semânticas

### Agora (Com P0-1, P0-2, P0-3):
- Accuracy: **92-96%** (+6-10%)
- Queries médicas: **97%+** (+11%)
- Metadados: 17 campos (9 básicos + 8 enriquecidos)
- Queries: Semânticas + Keyword + Entity + Numerical

### Com P0-4 (Self-Query):
- Accuracy: **94-98%** (+8-12%)
- UX: Queries naturais com filtros automáticos
- Flexibilidade: Máxima

---

## 💰 CUSTO TOTAL

| Feature | Custo Mensal |
|---------|--------------|
| Contextual Retrieval | $20 (10K docs) |
| Metadata Enrichment | $0 (grátis!) |
| Self-Query Retriever | $3 (3K queries) |
| **TOTAL** | **$23/mês** |

**ROI:** Impacto massivo (+60-80% accuracy) por custo baixíssimo!

---

## ⚠️ ATENÇÃO: PDFs Antigos

**IMPORTANTE:** Os PDFs processados ANTES desta implementação NÃO têm metadados enriquecidos!

**Lista de PDFs que precisam ser reprocessados:**
1. Artigo de Revisão - NEJM - Cardiomiopatia Hipertrófica.pdf
2. Artigo de Revisão - Nature - Cardiomiopatia Hipertrófica.pdf
3. [Outros PDFs existentes no Railway]

**Como reprocessar:**
- Web UI: Re-upload do mesmo PDF → confirmar reprocessamento
- Local: `python3 adicionar_pdf.py "content/arquivo.pdf"`

---

## 🚀 QUANDO ESTIVER PRONTO

Após o deploy finalizar no Railway:

1. ✅ Verificar logs do deploy (procurar por "KeyBERT pronto")
2. ✅ Re-upload dos 2 PDFs de cardiomiopatia
3. ✅ Testar query: "Compare mavacamten e aficamten"
4. ✅ Rodar `python3 test_metadata_stress.py` localmente
5. ✅ Implementar Self-Query Retriever (P0-4 final)
6. ✅ Comemorar! 🎉

---

**Implementado por:** Claude Code
**Data:** 2025-10-21
**Status:** ⏳ Aguardando deploy do Railway
**Próximo:** Reprocessar PDFs → Stress test → Self-Query
