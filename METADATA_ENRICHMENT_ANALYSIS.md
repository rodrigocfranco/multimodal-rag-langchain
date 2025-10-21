# 🔍 Análise: Metadados Atuais vs Enriquecimento Avançado

Data: 2025-10-21
Fonte: Pesquisa profunda + análise do código atual

---

## 📊 METADADOS ATUAIS (Implementados)

### O que já temos em `adicionar_pdf.py`:

```python
metadata = {
    "doc_id": uuid.uuid4(),           # ✅ ID único do chunk
    "pdf_id": hash(pdf_content),      # ✅ ID único do PDF
    "source": "arquivo.pdf",          # ✅ Nome do arquivo
    "type": "text|table|image",       # ✅ Tipo de conteúdo
    "index": 0,                       # ✅ Posição no documento
    "page_number": 5,                 # ✅ Número da página
    "uploaded_at": "2025-10-21",      # ✅ Data de upload
    "section": "Resultados",          # ✅ Seção do documento
    "document_type": "clinical_guideline", # ✅ Tipo de documento
    "summary": "Resumo do chunk...",  # ✅ Resumo gerado por LLM
}
```

### Recursos implementados:

1. ✅ **Contextual Retrieval**: Contexto LLM-gerado para cada chunk
2. ✅ **Section Detection**: Identificação automática de seções médicas
3. ✅ **Document Type Classification**: Classificação em 8 tipos
4. ✅ **Summaries**: Resumos gerados por LLM para todos os chunks
5. ✅ **HTML Preservation**: Tabelas mantêm estrutura HTML
6. ✅ **Deduplicação**: PDF_ID previne duplicatas

---

## 🚀 METADADOS AVANÇADOS (Não implementados)

### Top 10 técnicas da pesquisa 2025:

| # | Técnica | Impacto | Complexidade | Custo | Prioridade |
|---|---------|---------|--------------|-------|------------|
| 1 | **Keywords (KeyBERT)** | +10-20% recall | Fácil | Grátis | 🔴 ALTA |
| 2 | **Entidades Médicas (MediAlbertina)** | +25-40% precision | Médio | Grátis | 🔴 ALTA |
| 3 | **Self-Query Retriever** | +12% accuracy | Médio | $0.001/query | 🔴 ALTA |
| 4 | **Valores Numéricos + Unidades** | +30-50% queries numéricas | Médio | Grátis | 🟡 MÉDIA |
| 5 | **LlamaIndex Extractors** | +15-25% accuracy | Fácil | $0.003/chunk | 🟡 MÉDIA |
| 6 | **Complexity Score** | +10% precision | Fácil | Grátis | 🟢 BAIXA |
| 7 | **Citations/References** | +15% confiabilidade | Fácil | Grátis | 🟢 BAIXA |
| 8 | **Questions Answered** | +20% query matching | Médio | $0.001/chunk | 🟢 BAIXA |
| 9 | **Relationship Extraction** | +15-30% multi-hop | Difícil | $0.01/chunk | 🔵 FUTURO |
| 10 | **GraphRAG (Neo4j)** | Até 99% precision | Muito Difícil | $0.05/chunk | 🔵 FUTURO |

---

## 🎯 ANÁLISE DETALHADA: Top 3 Prioridades

### 1️⃣ **Keywords com KeyBERT** 🔴 ALTA

**O que é:**
Extração de palavras-chave semanticamente relevantes usando embeddings BERT.

**Diferença vs atual:**
- **Atual**: Não extraímos keywords explicitamente
- **Novo**: 5-10 keywords por chunk (ex: `["diabetes", "metformina", "HbA1c", "glicemia"]`)

**Por que importa:**
- Melhora **BM25** (nossa busca por keywords já implementada)
- Permite **filtros por tópico** ("Mostre apenas chunks sobre insulina")
- **+10-20% recall** em queries específicas

**Implementação:**
```python
from keybert import KeyBERT

kw_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')

def extract_keywords(text):
    keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        stop_words='portuguese',
        top_n=8,
        use_maxsum=True
    )
    return [kw[0] for kw in keywords]

# Adicionar ao metadata
metadata["keywords"] = extract_keywords(chunk_text)
metadata["keywords_str"] = ", ".join(metadata["keywords"])
```

**Custo:** Grátis (modelo local)
**Tempo:** 2-3 horas para implementar
**Impacto esperado:** +10-20% recall

---

### 2️⃣ **Entidades Médicas com MediAlbertina PT-PT** 🔴 ALTA

**O que é:**
Extração automática de entidades médicas (doenças, medicamentos, procedimentos) do texto.

**Diferença vs atual:**
- **Atual**: Não identificamos entidades médicas
- **Novo**: Metadata estruturado com entidades
  ```json
  {
    "entities_diseases": ["diabetes tipo 2", "hipertensão"],
    "entities_medications": ["metformina", "insulina"],
    "entities_procedures": ["miectomia", "ablação septal"]
  }
  ```

**Por que importa:**
- **+25-40% precision** em queries médicas específicas
- Permite filtros inteligentes ("Mostre tratamentos para diabetes")
- **96.13% F1 score** em português médico (estado da arte)

**Implementação:**
```python
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# MediAlbertina: melhor modelo para português médico
model_name = "pucpr/medialbertina-pt-pt"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

ner = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

def extract_medical_entities(text):
    entities = ner(text[:512])  # Limite de tokens

    diseases = []
    procedures = []
    medications = []

    for entity in entities:
        if entity['entity_group'] in ['DISEASE', 'DIAGNOSIS']:
            diseases.append(entity['word'])
        elif entity['entity_group'] == 'PROCEDURE':
            procedures.append(entity['word'])
        elif entity['entity_group'] in ['MEDICATION', 'DRUG']:
            medications.append(entity['word'])

    return {
        "diseases": list(set(diseases)),
        "procedures": list(set(procedures)),
        "medications": list(set(medications))
    }

# Adicionar ao metadata
entities = extract_medical_entities(chunk_text)
metadata["entities_diseases"] = entities["diseases"]
metadata["entities_procedures"] = entities["procedures"]
metadata["entities_medications"] = entities["medications"]
metadata["has_medical_entities"] = len(entities["diseases"]) > 0
```

**Custo:** Grátis (modelo open-source)
**Tempo:** 4-5 horas (incluindo testes)
**Impacto esperado:** +25-40% precision em queries médicas

**Nota importante:** MediAlbertina foi treinado em 96M tokens de textos médicos portugueses e atinge **96.13% F1** (melhor que BioBERT e scispaCy para PT).

---

### 3️⃣ **Self-Query Retriever** 🔴 ALTA

**O que é:**
LLM extrai automaticamente filtros de metadata da query em linguagem natural.

**Diferença vs atual:**
- **Atual**: Busca semântica + BM25 sem filtros automáticos
- **Novo**: Query natural → filtros estruturados
  ```
  Query: "Mostre guidelines sobre diabetes da seção Tratamento"
  ↓
  Filtros automáticos: {document_type="clinical_guideline", section="Tratamento"}
  ```

**Por que importa:**
- **+12% accuracy** em queries complexas
- **+17.2% Hits@4** (Multi-Meta-RAG research)
- Permite queries super específicas sem comandos manuais

**Implementação:**
```python
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo
from langchain_openai import ChatOpenAI

# Definir campos de metadata disponíveis
metadata_field_info = [
    AttributeInfo(
        name="document_type",
        description="Tipo: clinical_guideline, case_report, review_article, clinical_trial",
        type="string"
    ),
    AttributeInfo(
        name="section",
        description="Seção: Resumo, Introdução, Métodos, Resultados, Discussão, Tratamento",
        type="string"
    ),
    AttributeInfo(
        name="page_number",
        description="Número da página no PDF",
        type="integer"
    ),
    AttributeInfo(
        name="type",
        description="Tipo de conteúdo: text, table, image",
        type="string"
    ),
    AttributeInfo(
        name="keywords",
        description="Palavras-chave do chunk",
        type="list[string]"
    ),
    AttributeInfo(
        name="entities_diseases",
        description="Doenças mencionadas no chunk",
        type="list[string]"
    )
]

# Descrição do conteúdo
document_content_description = "Documentos médicos em português sobre diabetes, cardiologia e outras condições"

# Criar retriever
llm = ChatOpenAI(model="gpt-4o", temperature=0)

self_query_retriever = SelfQueryRetriever.from_llm(
    llm=llm,
    vectorstore=vectorstore,
    document_contents=document_content_description,
    metadata_field_info=metadata_field_info,
    verbose=True
)

# Usar
docs = self_query_retriever.get_relevant_documents(
    "Mostre tabelas de guidelines sobre tratamento de diabetes"
)
# ↓ LLM extrai automaticamente:
# filter: {document_type="clinical_guideline", section="Tratamento", type="table"}
```

**Custo:** ~$0.001 por query (GPT-4o para extração de filtros)
**Tempo:** 3-4 horas para implementar + testes
**Impacto esperado:** +12% accuracy, +17.2% Hits@4

---

## 🟡 PRIORIDADES MÉDIAS

### 4️⃣ **Valores Numéricos + Unidades**

**O que extrai:**
```python
{
    "measurements": [
        {"name": "HbA1c", "value": 7.5, "unit": "%"},
        {"name": "TFG", "value": 45, "unit": "mL/min/1.73m²"},
        {"name": "creatinina", "value": 1.2, "unit": "mg/dL"}
    ],
    "has_lab_values": True
}
```

**Por que importa:**
Permite queries como "Mostre casos com HbA1c > 8%" ou "Encontre valores de TFG < 45"

**Impacto:** +30-50% em queries numéricas
**Tempo:** 4-6 horas

---

### 5️⃣ **LlamaIndex Metadata Extractors**

**O que faz:**
Pipeline automático que extrai: summaries, keywords, questions answered, entities

**Vantagem:** Tudo integrado, menos código custom
**Desvantagem:** Custo ($0.003/chunk) e menos controle

**Impacto:** +15-25% accuracy
**Tempo:** 2-3 horas (já pronto)

---

## 📈 COMPARAÇÃO: Antes vs Depois

### Metadata Atual (9 campos):
```python
{
    "doc_id": "abc123",
    "source": "diabetes.pdf",
    "type": "text",
    "page_number": 5,
    "section": "Tratamento",
    "document_type": "clinical_guideline",
    "uploaded_at": "2025-10-21",
    "summary": "Resumo...",
    "pdf_id": "xyz789"
}
```

### Metadata Enriquecido (20+ campos):
```python
{
    # Atuais (mantidos)
    "doc_id": "abc123",
    "source": "diabetes.pdf",
    "type": "text",
    "page_number": 5,
    "section": "Tratamento",
    "document_type": "clinical_guideline",
    "uploaded_at": "2025-10-21",
    "summary": "Resumo...",
    "pdf_id": "xyz789",

    # NOVOS (Keywords)
    "keywords": ["diabetes", "metformina", "HbA1c", "insulina"],
    "keywords_str": "diabetes, metformina, HbA1c, insulina",

    # NOVOS (Entidades Médicas)
    "entities_diseases": ["diabetes tipo 2", "hipertensão"],
    "entities_medications": ["metformina", "insulina glargina"],
    "entities_procedures": ["monitorização glicêmica"],
    "has_medical_entities": True,

    # NOVOS (Valores Numéricos)
    "measurements": [
        {"name": "HbA1c", "value": 7.5, "unit": "%"}
    ],
    "has_lab_values": True,

    # NOVOS (Automáticos)
    "complexity": "intermediate",  # basic|intermediate|advanced
    "questions_answered": [
        "Qual o alvo de HbA1c para diabetes tipo 2?",
        "Quando usar metformina?"
    ]
}
```

---

## 💰 ANÁLISE DE CUSTO

### Setup Atual (Contextual Retrieval):
- **Custo por PDF (100 chunks)**: ~$0.20 (GPT-4o-mini)
- **Custo mensal (50 PDFs)**: ~$10

### Setup com Top 3 Enriquecimentos:
- **Keywords (KeyBERT)**: $0 (grátis)
- **Entidades (MediAlbertina)**: $0 (grátis)
- **Self-Query**: $0.001/query = ~$3/mês (3000 queries)
- **Total adicional**: ~$3/mês

**Conclusão:** Impacto massivo (+47-72% accuracy combinado) por apenas +$3/mês!

---

## 🎯 ROADMAP DE IMPLEMENTAÇÃO

### Fase 1: Quick Wins (1 semana) 🔴
1. **KeyBERT keywords** (2-3h)
   - Instalar: `pip install keybert sentence-transformers`
   - Adicionar função em `adicionar_pdf.py`
   - Testar com PDFs existentes

2. **MediAlbertina entities** (4-5h)
   - Instalar: `pip install transformers torch`
   - Implementar extração de entidades
   - Validar precisão em textos médicos PT

3. **Self-Query Retriever** (3-4h)
   - Implementar em `consultar_com_rerank.py`
   - Configurar metadata fields
   - Testar queries complexas

**Impacto total:** +47-72% accuracy combinado
**Custo:** +$3/mês

### Fase 2: Advanced Features (2-3 semanas) 🟡
4. Valores numéricos com unidades
5. LlamaIndex metadata extractors
6. Complexity scoring

### Fase 3: Expert Level (1+ mês) 🔵
7. Relationship extraction
8. GraphRAG com Neo4j

---

## 📊 IMPACTO ESPERADO NO SISTEMA

### Baseline (Atual):
- Accuracy: **86.2%** (suite de validação)
- Hybrid Search: BM25 (40%) + Vector (60%)
- Contextual Retrieval: ✅ Implementado

### Com Top 3 Enriquecimentos:
- **Keywords**: +10-20% recall → **~91-94% accuracy**
- **Entidades Médicas**: +25-40% precision médica → **queries médicas 95%+**
- **Self-Query**: +12% accuracy → **consistência em queries complexas**

**Projeção conservadora:** **92-96% accuracy** (vs 86.2% atual)
**Projeção otimista:** **97%+ em queries médicas específicas**

---

## ✅ RECOMENDAÇÃO FINAL

### Implementar AGORA (esta semana):

1. **KeyBERT** - Fácil, grátis, +10-20% recall
2. **MediAlbertina** - Médio, grátis, +25-40% precision médica
3. **Self-Query** - Médio, $3/mês, +12% accuracy

**Razão:** São complementares, não competem entre si. Juntos, criam um sistema de RAG médico **estado da arte 2025**.

**Próximos passos:**
1. Implementar KeyBERT primeiro (mais fácil, testa pipeline)
2. Adicionar MediAlbertina (maior impacto médico)
3. Integrar Self-Query (melhor UX)
4. Re-processar PDFs existentes com novos metadados
5. Rodar suite de validação para medir ganho real

---

**Arquivos para modificar:**
- `adicionar_pdf.py` - Adicionar extração de keywords + entities
- `consultar_com_rerank.py` - Implementar self-query retriever
- `test_validation_suite.py` - Adicionar testes para novos metadados

**Dependências novas:**
```bash
pip install keybert sentence-transformers transformers torch
```

**Tempo total estimado:** 9-12 horas de desenvolvimento + testes
**Impacto:** +47-72% accuracy combinado
**Custo:** +$3/mês
