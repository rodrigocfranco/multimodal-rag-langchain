# 🔬 PESQUISA: Melhores Práticas de RAG 2025

Data: 2025-10-18
Fonte: Pesquisa profunda em documentação oficial, artigos técnicos e implementações de produção

---

## 📚 ÍNDICE

1. [Chunking: Estado da Arte](#chunking)
2. [Embeddings e Retrieval](#embeddings)
3. [Metadata e Hybrid Search](#metadata)
4. [Técnicas Avançadas de RAG](#tecnicas-avancadas)
5. [Avaliação de RAG](#avaliacao)
6. [Análise do Nosso Sistema](#analise-atual)
7. [Recomendações Priorizadas](#recomendacoes)

---

## 1. CHUNKING: Estado da Arte {#chunking}

### 📊 Tamanho Ótimo de Chunks (2025)

**Descobertas da pesquisa:**
- **Consenso geral:** 128-512 tokens por chunk
- **Sweet spot:** ~250 tokens (≈1000 caracteres)
- **Overlap recomendado:** 10-20% do tamanho do chunk
  - NVIDIA encontrou **15% overlap com chunks de 1024 tokens** como ideal
  - Baseline: 512 tokens com 50-100 tokens de overlap

**Quando usar cada tamanho:**
- **Pequenos (128-256 tokens):** Queries factuais, matching de keywords preciso
- **Médios (256-512 tokens):** Uso geral, balanceado
- **Grandes (512-1024 tokens):** Tarefas que requerem contexto amplo, sumarização

### 🏗️ Estratégias Avançadas de Chunking

#### A. **Sentence Window Retrieval** ⭐⭐⭐⭐⭐
**Como funciona:**
1. Embed **chunks pequenos** (1-2 sentenças) para busca precisa
2. No retrieval, retorna **chunks expandidos** com contexto ao redor
3. Usa metadata para tracking (doc_id + índice do chunk)

**Benefícios:**
- Embeddings mais precisos (pequenos chunks capturam semântica melhor)
- LLM recebe contexto suficiente (chunks expandidos)
- Melhor dos dois mundos

**Implementação:**
```python
# Embed sentenças individuais
small_chunks = split_by_sentences(doc)

# Metadata: qual doc, qual posição
metadata = {"doc_id": doc_id, "index": i, "window_size": 3}

# No retrieval: retornar chunk + vizinhos
def retrieve_with_window(chunk_idx, window=3):
    return chunks[chunk_idx-window:chunk_idx+window+1]
```

#### B. **Contextual Retrieval (Anthropic 2024)** ⭐⭐⭐⭐⭐
**Descoberta CRÍTICA:**
- Reduz erros de retrieval em **67%**
- Contextual Embeddings: -35% failure rate (5.7% → 3.7%)
- Contextual Embeddings + BM25: **-49% failure rate** (5.7% → 2.9%)

**Como funciona:**
1. Para cada chunk, usar LLM para gerar **contexto explicativo**
2. Prepend contexto ao chunk antes de embedar
3. Exemplo:
```
Original chunk: "MUITO ALTO: Hipercolesterolemia Familiar"

Contexto gerado: "Este trecho faz parte da TABELA 1 de
estratificação de risco cardiovascular em diabetes tipo 2,
especificamente a categoria de MUITO ALTO risco."

Chunk final embedado:
"[CONTEXTO] Este trecho faz parte da TABELA 1...
[CONTEÚDO] MUITO ALTO: Hipercolesterolemia Familiar"
```

**Benefícios:**
- Chunks não perdem contexto do documento inteiro
- Busca semântica mais precisa
- Especialmente útil para tabelas e listas

#### C. **Parent-Child Chunking (Hierarchical)** ⭐⭐⭐⭐
**Como funciona:**
1. **Child chunks** (pequenos): usados para busca precisa
2. **Parent chunks** (grandes): retornados para o LLM
3. Hierarquia: Documento → Seções → Parágrafos → Sentenças

**Implementação no LangChain:**
- `ParentDocumentRetriever`: busca em child, retorna parent
- Evita perder contexto mantendo chunks pequenos para busca

### 🎯 Chunking para Casos Específicos

#### Tabelas
**CRÍTICO:** Tabelas NÃO devem ser chunkeadas com estratégias normais!

**Estratégias recomendadas:**
1. **Preservar tabela inteira** + HTML/Markdown estruturado
2. **Gerar descrição contextual** via LLM
3. **Embed: descrição + tabela formatada**

```python
# Exemplo de processamento de tabela
table_description = llm.generate(
    f"Descreva esta tabela do documento '{doc_title}':\n{table_html}"
)

table_chunk = f"""
[DESCRIÇÃO]
{table_description}

[TABELA COMPLETA]
{table_text}

[HTML]
{table_html}
"""
```

---

## 2. EMBEDDINGS E RETRIEVAL {#embeddings}

### 🎯 Escolha de Modelo de Embedding

**Para português/multilíngue:**
- ✅ **OpenAI text-embedding-3-large** (3072 dims) - NOSSA ESCOLHA
  - Excelente para português
  - +30% qualidade vs ada-002
  - Custo: moderado

**Alternativas:**
- **Cohere embed-multilingual-v3.0** - Especializado multilíngue
- **Multilingual-e5-large** - Open source, bom custo-benefício

### 🔄 Retrieval Strategies

#### A. **MultiVectorRetriever** (NOSSO ATUAL) ⭐⭐⭐⭐
**Descobertas:**
- **Decouple retrieval from synthesis**
  - Summaries → vectorstore (busca)
  - Original docs → docstore (geração)

**3 Estratégias possíveis:**
1. **Smaller chunks:** ParentDocumentRetriever pattern
2. **Summaries:** Embed resumos, retornar documentos completos
3. **Hypothetical questions:** Embed perguntas que o doc responde

**Problema descoberto:**
- Resumos podem omitir keywords específicos
- **Solução:** Embed resumo + texto original juntos

#### B. **Hybrid Search (BM25 + Vector)** ⭐⭐⭐⭐⭐
**CRÍTICO:** Descoberta importante da pesquisa!

**Como funciona:**
1. **BM25** (keyword-based): filtro inicial rápido
2. **Vector search** (semantic): refinamento contextual
3. **Fusion:** Combinar resultados (Reciprocal Rank Fusion)

**Performance:**
- +20-40% accuracy vs vector search alone
- Especialmente útil para:
  - Termos médicos específicos
  - Nomes de medicamentos
  - Valores numéricos (TFG <30, HbA1c >7%)

**Implementação:**
```python
# LangChain suporta hybrid retrievers
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# BM25 retriever
bm25_retriever = BM25Retriever.from_documents(docs)
bm25_retriever.k = 30

# Vector retriever (nosso atual)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 30})

# Hybrid ensemble
hybrid_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.4, 0.6]  # 40% BM25, 60% vector
)
```

**Impacto esperado no nosso sistema:**
- Melhor retrieval de valores específicos ("3 ou mais fatores")
- Melhor matching de termos médicos exatos
- Combina com Cohere rerank para resultados ótimos

#### C. **Cohere Rerank Optimization** (NOSSO ATUAL) ⭐⭐⭐⭐⭐
**Descobertas:**

**Rerank 3.5 (mais recente):**
- +26.4% melhoria em **cross-lingual search**
- Suporta **100+ idiomas** incluindo português
- **State-of-the-art** em português

**Recomendações:**
- ✅ Estamos usando `rerank-multilingual-v3.0` → CORRETO
- ✅ `top_n=12` → BOM (pesquisa recomenda 8-15)
- ⚠️ Considerar upgrade para Rerank 3.5 quando disponível

**Otimização:**
- Aumentar retrieval inicial: 30 docs → 40-50 docs
- Rerank para top 12-15
- Combinar com BM25 hybrid search

---

## 3. METADATA E HYBRID SEARCH {#metadata}

### 📝 Metadata Enrichment

**Descobertas da pesquisa:**

**Metadata inteligente melhora retrieval em 40-60%!**

**Tipos de metadata recomendados:**

#### A. **Metadata Estruturado** (JÁ TEMOS ✅)
```python
{
    "doc_id": "uuid",
    "pdf_id": "hash",
    "source": "filename.pdf",
    "type": "text|table|image",
    "page_number": 5,
    "document_type": "clinical_guideline",
    "section": "Tratamento",
    "uploaded_at": "timestamp"
}
```

#### B. **Metadata Enriquecido** (FALTA ⚠️)
**Adicionar:**

1. **Keywords extraídos automaticamente**
```python
"keywords": ["diabetes", "hipercolesterolemia", "risco cardiovascular"],
"medical_terms": ["HbA1c", "TFG", "albuminúria"],
"numeric_values": ["<7%", ">300mg/g", "<30ml/min"]
```

2. **Complexity level**
```python
"complexity": "advanced",  # basic|intermediate|advanced
"evidence_level": "1A",    # Para guidelines médicos
```

3. **Related entities** (Graph-based)
```python
"entities": {
    "conditions": ["Diabetes Tipo 2", "Hipercolesterolemia Familiar"],
    "medications": ["Metformina", "iSGLT2", "AR GLP-1"],
    "parameters": ["HbA1c", "TFG", "Albuminúria"]
}
```

### 🔍 Self-Query Retriever

**Descoberta importante:**
- LLM pode **inferir filtros de metadata** automaticamente da query
- Exemplo:
```
Query: "Qual tratamento para diabetes com TFG baixa?"

Auto-detected filters:
- document_type: clinical_guideline
- section: Tratamento
- medical_terms: ["TFG", "insuficiência renal"]
```

**Implementação:**
```python
from langchain.retrievers import SelfQueryRetriever

retriever = SelfQueryRetriever.from_llm(
    llm=llm,
    vectorstore=vectorstore,
    document_contents="Diretrizes médicas de diabetes",
    metadata_field_info=[
        {"name": "section", "type": "string"},
        {"name": "document_type", "type": "string"},
        {"name": "page_number", "type": "integer"}
    ]
)
```

---

## 4. TÉCNICAS AVANÇADAS DE RAG {#tecnicas-avancadas}

### 🚀 HyDE (Hypothetical Document Embeddings) ⭐⭐⭐⭐

**O que é:**
- Gerar **documento hipotético** que responde a query
- Embedar documento hipotético (não a query)
- Buscar documentos similares ao hipotético

**Como funciona:**
```python
# 1. Query do usuário
query = "Quais critérios de muito alto risco cardiovascular em diabetes?"

# 2. LLM gera resposta hipotética
hypothetical_doc = llm.generate(
    f"Escreva um trecho de diretriz médica respondendo: {query}"
)
# Output: "Os critérios de muito alto risco cardiovascular incluem:
# - Hipercolesterolemia Familiar
# - 3 ou mais fatores de risco
# - Albuminúria >300mg/g..."

# 3. Embedar documento hipotético
hyp_embedding = embed(hypothetical_doc)

# 4. Buscar docs similares
similar_docs = vectorstore.similarity_search_by_vector(hyp_embedding)
```

**Benefícios:**
- +15-30% accuracy em queries complexas
- Evita vocabulary mismatch (query vs documento)
- Zero-shot, não precisa fine-tuning

**Quando usar:**
- Queries abstratas ou complexas
- Quando há mismatch de vocabulário
- Documentos técnicos/médicos

### 🧠 Adaptive RAG ⭐⭐⭐⭐⭐

**Conceito:**
- Sistema **decide dinamicamente** a estratégia de retrieval
- **Query routing:** vectorstore vs web search vs knowledge graph
- **Self-correction:** revalida e corrige respostas

**Componentes:**

1. **Query Router:**
```python
def route_query(query):
    query_type = classify_query(query)

    if query_type == "factual_specific":
        return bm25_retriever  # Keywords exatos
    elif query_type == "conceptual":
        return vector_retriever  # Semântico
    elif query_type == "complex_multi_hop":
        return graph_retriever  # Relações entre entidades
```

2. **Self-Evaluation:**
```python
# Após retrieval, avaliar qualidade
relevance_score = evaluate_retrieved_docs(query, docs)

if relevance_score < threshold:
    # Tentar estratégia alternativa
    docs = fallback_retriever.invoke(query)
```

3. **Iterative Refinement:**
```python
# Se resposta insatisfatória, refinar
if answer_quality < threshold:
    refined_query = reformulate_query(query, answer)
    docs = retriever.invoke(refined_query)
    answer = llm.generate(refined_query, docs)
```

**Implementação com LangGraph:**
- LangChain tem suporte nativo para adaptive RAG
- Permite criar workflows complexos com decisões dinâmicas

### 🕸️ GraphRAG (Knowledge Graph) ⭐⭐⭐⭐

**Descoberta importante:**
- GraphRAG **supera baseline RAG** em:
  - **Multi-hop reasoning** (conectar informações de múltiplos documentos)
  - **Summarização complexa**
  - **Descobrir relações** entre entidades que não co-ocorrem

**Exemplo de uso médico:**
```
Query: "Qual relação entre HbA1c alta e escolha de antidiabético?"

GraphRAG pode conectar:
- Node 1: HbA1c ≥7.5% → Indica controle glicêmico inadequado
- Node 2: Controle inadequado → Terapia dupla recomendada
- Node 3: Terapia dupla → Metformina + iSGLT2 ou AR GLP-1
- Edge: HbA1c → Decisão terapêutica → Medicamento

Resposta mais completa e fundamentada!
```

**Trade-offs:**
- ⬆️ Complexidade de implementação
- ⬆️ Custo computacional
- ⬆️ Qualidade em queries complexas
- Melhor para: bases de conhecimento estruturadas, documentos interconectados

**Ferramentas:**
- Neo4j + LangChain
- Microsoft GraphRAG
- LlamaIndex Knowledge Graph

---

## 5. AVALIAÇÃO DE RAG {#avaliacao}

### 📊 RAGAS Framework ⭐⭐⭐⭐⭐

**Descoberta CRÍTICA:** Precisamos avaliar nosso RAG!

**Métricas principais:**

#### A. **Faithfulness (Fidelidade)**
**O que mede:** Resposta é factualmente precisa com base nos documentos?

**Fórmula:**
```
Faithfulness = # statements corretos / # total statements
```

**Exemplo:**
```
Contexto: "Metformina é contraindicada com TFG <30"
Resposta: "Metformina pode ser usada com TFG <30 com ajuste de dose"

Faithfulness = 0 (❌ contradiz o contexto)
```

#### B. **Answer Relevancy (Relevância da Resposta)**
**O que mede:** Resposta é relevante para a pergunta?

**Método:** Gerar queries reversas da resposta, comparar com query original

#### C. **Context Precision (Precisão do Contexto)**
**O que mede:** Documentos relevantes estão bem rankeados?

**Ideal:** Todos chunks relevantes no top-k, não misturados com irrelevantes

#### D. **Context Recall (Recall do Contexto)**
**O que mede:** Todos aspectos relevantes da query foram recuperados?

### 🔧 Implementação RAGAS

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

# Dataset de teste
test_questions = [
    {
        "question": "Quais critérios de muito alto risco?",
        "ground_truth": "Hipercolesterolemia Familiar, 3+ fatores...",
        "answer": "...",  # Gerado pelo RAG
        "contexts": [...] # Chunks recuperados
    }
]

# Avaliar
result = evaluate(
    dataset=test_questions,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)

print(result)
# {
#   "faithfulness": 0.92,
#   "answer_relevancy": 0.88,
#   "context_precision": 0.85,
#   "context_recall": 0.79
# }
```

**Por que é importante:**
- Detectar **hallucinations** (baixa faithfulness)
- Identificar **retrieval ruim** (baixa context precision/recall)
- Medir **impacto de mudanças** antes/depois

---

## 6. ANÁLISE DO NOSSO SISTEMA ATUAL {#analise-atual}

### ✅ O QUE ESTAMOS FAZENDO BEM

| Componente | Nossa Implementação | Best Practice | Status |
|------------|---------------------|---------------|--------|
| **Embeddings** | text-embedding-3-large (3072d) | text-embedding-3-large | ✅ ÓTIMO |
| **Reranker** | Cohere rerank-multilingual-v3.0 | Cohere Rerank 3.5 | ✅ BOM |
| **LLM** | GPT-4o | GPT-4o | ✅ ÓTIMO |
| **Summary LLM** | GPT-4o-mini | GPT-4o-mini/GPT-4o | ✅ BOM |
| **Retriever** | MultiVectorRetriever | MultiVector/Hybrid | ✅ BOM |
| **Metadata** | Estruturado básico | Enriquecido | ⚠️ BÁSICO |
| **Portuguese OCR** | languages=["por"] | Forçar idioma | ✅ BOM |

### ⚠️ GAPS IDENTIFICADOS

| Gap | Impacto | Best Practice | Nossa Situação |
|-----|---------|---------------|----------------|
| **Chunking de tabelas** | 🔴 CRÍTICO | Preservar inteiras | ~~Quebrava tabelas~~ → CORRIGIDO |
| **Hybrid Search** | 🔴 CRÍTICO | BM25 + Vector | Só vector search |
| **Resumos perdem keywords** | 🔴 CRÍTICO | Original + resumo | ~~Só resumo~~ → CORRIGIDO |
| **Contextual retrieval** | 🟠 ALTO | Chunks com contexto | Chunks isolados |
| **Sentence window** | 🟠 ALTO | Small embed, large retrieve | Single-size chunks |
| **HyDE** | 🟡 MÉDIO | Query expansion | Direct query |
| **Adaptive routing** | 🟡 MÉDIO | Dynamic strategy | Fixed strategy |
| **Self-query** | 🟡 MÉDIO | Auto metadata filters | No filtering |
| **Evaluation** | 🟡 MÉDIO | RAGAS metrics | Nenhuma avaliação |
| **GraphRAG** | 🟢 BAIXO | Knowledge graph | N/A |

---

## 7. RECOMENDAÇÕES PRIORIZADAS {#recomendacoes}

### 🚨 P0 - CRÍTICO (Implementar AGORA)

#### 1. **Hybrid Search (BM25 + Vector)** ⭐⭐⭐⭐⭐
**Impacto esperado:** +30-50% accuracy em queries específicas

**Implementação:**
```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# Carregar todos documentos para BM25
all_docs = load_all_documents_from_docstore()

# BM25 retriever
bm25_retriever = BM25Retriever.from_documents(all_docs)
bm25_retriever.k = 40

# Vector retriever (atual)
vector_retriever = base_retriever  # Nosso MultiVectorRetriever

# Hybrid ensemble
hybrid_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.4, 0.6]  # Ajustar empiricamente
)

# Aplicar reranker no resultado híbrido
retriever = ContextualCompressionRetriever(
    base_compressor=cohere_rerank,
    base_retriever=hybrid_retriever
)
```

**Esforço:** 2-3 horas
**Benefícios:**
- ✅ Melhor retrieval de termos médicos exatos
- ✅ Melhor matching de valores numéricos
- ✅ Combina keyword precision + semantic understanding

---

#### 2. **Contextual Retrieval (Anthropic)** ⭐⭐⭐⭐⭐
**Impacto esperado:** -49% failure rate (comprovado pela Anthropic)

**Implementação:**
```python
def add_contextual_prefix(chunk, full_document, pdf_metadata):
    """
    Usar LLM para gerar contexto do chunk dentro do documento
    """
    prompt = f"""
Documento: {pdf_metadata['filename']}
Tipo: {pdf_metadata['document_type']}

Conteúdo completo do documento:
{full_document[:4000]}  # Primeiros 4000 chars

Chunk específico:
{chunk}

Tarefa: Escreva 1-2 sentenças de contexto situando este chunk
dentro do documento. Exemplo: "Este trecho faz parte da seção
de Tratamento da Diretriz de Diabetes 2025, especificamente
sobre escolha de antidiabéticos em pacientes com risco cardiovascular."

Contexto:
"""
    context = llm.generate(prompt, max_tokens=150)

    # Retornar chunk com contexto
    return f"[CONTEXTO]\n{context}\n\n[CONTEÚDO]\n{chunk}"

# Aplicar no processamento
for chunk in chunks:
    contextualized_chunk = add_contextual_prefix(
        chunk,
        full_document,
        pdf_metadata
    )
    # Embedar chunk contextualizado
    embedding = embed(contextualized_chunk)
```

**Esforço:** 4-6 horas
**Trade-offs:**
- ⬆️ Custo: 1 LLM call por chunk (~50 chunks/doc)
- ⬆️ Tempo de processamento: +30-60 segundos por PDF
- ⬆️⬆️ Qualidade de retrieval: -49% erros

**Otimização:**
- Cachear contextos gerados
- Processar em batch (paralelizar)
- Usar GPT-4o-mini para economia

---

#### 3. **Metadata Enriquecido** ⭐⭐⭐⭐
**Impacto esperado:** +20-40% precision com self-query

**Implementação:**
```python
def enrich_metadata(chunk, chunk_metadata):
    """
    Extrair keywords, entidades médicas, valores numéricos
    """
    # 1. Keywords via TF-IDF ou LLM
    keywords = extract_keywords(chunk)

    # 2. Entidades médicas (regex patterns)
    medical_terms = extract_medical_terms(chunk)
    # Patterns: HbA1c, TFG, iSGLT2, AR GLP-1, etc.

    # 3. Valores numéricos
    numeric_values = extract_numeric_patterns(chunk)
    # Patterns: <7%, >300mg/g, ≥7.5%, etc.

    # 4. Atualizar metadata
    enriched_metadata = {
        **chunk_metadata,
        "keywords": keywords,
        "medical_terms": medical_terms,
        "numeric_values": numeric_values,
        "complexity": estimate_complexity(chunk),  # basic/intermediate/advanced
    }

    return enriched_metadata

# Exemplo de self-query depois
retriever = SelfQueryRetriever.from_llm(
    llm=llm,
    vectorstore=vectorstore,
    metadata_field_info=[
        {"name": "section", "type": "string"},
        {"name": "keywords", "type": "list[string]"},
        {"name": "medical_terms", "type": "list[string]"},
    ]
)
```

**Esforço:** 3-4 horas

---

### 🔶 P1 - ALTO (Implementar em 1-2 semanas)

#### 4. **Sentence Window Retrieval** ⭐⭐⭐⭐
**Impacto esperado:** +15-25% relevance, melhor contexto

**Conceito:**
- Embed small (sentences)
- Retrieve large (sentence + neighbors)

**Implementação:**
```python
def create_sentence_windows(text, window_size=3):
    """
    Split em sentenças, mas armazena janelas
    """
    sentences = split_into_sentences(text)

    windows = []
    for i, sentence in enumerate(sentences):
        # Metadata: posição e vizinhos
        window_metadata = {
            "sentence_index": i,
            "total_sentences": len(sentences),
            "window_size": window_size
        }

        # Embedar apenas a sentença
        small_chunk = sentence

        # Armazenar janela inteira no docstore
        window_start = max(0, i - window_size)
        window_end = min(len(sentences), i + window_size + 1)
        large_chunk = " ".join(sentences[window_start:window_end])

        windows.append({
            "small": small_chunk,  # Para embedding
            "large": large_chunk,  # Para retrieval
            "metadata": window_metadata
        })

    return windows
```

**Esforço:** 5-6 horas

---

#### 5. **HyDE (Hypothetical Document Embeddings)** ⭐⭐⭐⭐
**Impacto esperado:** +15-30% em queries complexas

**Implementação:**
```python
from langchain_core.prompts import ChatPromptTemplate

hyde_prompt = ChatPromptTemplate.from_template("""
Você é um especialista em diabetes e cardiologia.

Pergunta do usuário: {question}

Escreva um parágrafo de diretriz médica respondendo esta pergunta.
Use linguagem técnica e seja específico com valores, critérios e recomendações.

Resposta hipotética:
""")

def hyde_retrieval(query):
    # 1. Gerar documento hipotético
    hypothetical_doc = llm.invoke(hyde_prompt.format(question=query))

    # 2. Embedar documento hipotético
    hyp_embedding = embeddings.embed_query(hypothetical_doc)

    # 3. Buscar com embedding do hipotético
    docs = vectorstore.similarity_search_by_vector(
        hyp_embedding,
        k=30
    )

    return docs

# Usar no pipeline
hyde_retriever = create_hyde_retriever(vectorstore, llm)
```

**Esforço:** 2-3 horas

---

#### 6. **RAGAS Evaluation** ⭐⭐⭐⭐
**Impacto:** Visibilidade de qualidade, iteração data-driven

**Implementação:**
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# 1. Criar dataset de teste (10-20 perguntas representativas)
test_dataset = [
    {
        "question": "Quais critérios de muito alto risco cardiovascular?",
        "ground_truth": "Hipercolesterolemia Familiar, 3 ou mais fatores de risco, albuminúria >300mg/g, TFG <30ml/min, retinopatia proliferativa, síndrome coronariana prévia",
        # answer e contexts serão preenchidos pelo RAG
    },
    # ... mais perguntas
]

# 2. Executar RAG para cada pergunta
for item in test_dataset:
    response = chain.invoke(item["question"])
    item["answer"] = response["response"]
    item["contexts"] = [doc.page_content for doc in response["context"]["texts"]]

# 3. Avaliar
results = evaluate(
    dataset=test_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision]
)

print(f"""
📊 RAGAS Scores:
  Faithfulness: {results['faithfulness']:.2f}
  Answer Relevancy: {results['answer_relevancy']:.2f}
  Context Precision: {results['context_precision']:.2f}
""")

# 4. Trackear ao longo do tempo
save_results_to_csv(results, timestamp=now())
```

**Esforço:** 3-4 horas inicial, 30min para cada avaliação depois

---

### 🟡 P2 - MÉDIO (Implementar em 1 mês)

#### 7. **Adaptive RAG with Query Routing** ⭐⭐⭐
**Impacto:** +10-20% em queries diversas

**Conceito:** Diferentes queries → diferentes estratégias

**Implementação:**
```python
def route_query(query):
    """
    Classificar query e escolher estratégia
    """
    query_type = classify_query_type(query)  # Via LLM ou classifier

    if query_type == "factual_specific":
        # Keywords exatos importantes
        return hybrid_retriever  # BM25 + Vector

    elif query_type == "conceptual_understanding":
        # Semântica é mais importante
        return vector_retriever

    elif query_type == "complex_multi_hop":
        # Precisa conectar múltiplos docs
        return hyde_retriever

    elif query_type == "when_not_to_do":
        # Negações, contraindicações
        return contextual_retriever  # Precisa contexto forte

# Usar no pipeline com LangGraph
```

**Esforço:** 6-8 horas

---

#### 8. **Parent-Child Chunking** ⭐⭐⭐
**Impacto:** Melhor contexto sem perder precisão

**Implementação:**
```python
from langchain.retrievers import ParentDocumentRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Child splitter (pequeno, para busca)
child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=30
)

# Parent splitter (grande, para contexto)
parent_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200
)

retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=docstore,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)
```

**Esforço:** 4-5 horas

---

### 🟢 P3 - BAIXO (Explorar depois)

#### 9. **GraphRAG**
**Quando considerar:**
- Se tivermos muitos documentos interconectados
- Se queries frequentes envolvem multi-hop reasoning
- Se relações entre entidades são críticas

**Esforço:** 15-20 horas
**Trade-off:** Alta complexidade vs benefício incremental

---

## 📋 ROADMAP DE IMPLEMENTAÇÃO

### Sprint 1 (Esta semana) - Correções Críticas
- [x] Fix: Tabelas inteiras (sem chunking)
- [x] Fix: Texto original + resumo nos embeddings
- [x] Fix: OCR português
- [ ] Implementar: Hybrid Search (BM25 + Vector)
- [ ] Implementar: Metadata enriquecido básico

**Meta:** Resolver problema de retrieval atual

### Sprint 2 (Próxima semana) - Contextual Retrieval
- [ ] Implementar: Contextual retrieval (Anthropic)
- [ ] Implementar: Self-query retriever
- [ ] Criar: Dataset de teste para RAGAS

**Meta:** Reduzir erros de retrieval em 50%

### Sprint 3 (Semana 3) - Advanced Techniques
- [ ] Implementar: HyDE
- [ ] Implementar: Sentence window retrieval
- [ ] Configurar: RAGAS evaluation pipeline
- [ ] Medir: Baseline metrics

**Meta:** Aumentar accuracy em queries complexas

### Sprint 4 (Semana 4) - Optimization & Evaluation
- [ ] Implementar: Adaptive query routing
- [ ] Otimizar: Parametrização (chunk sizes, overlap, k, top_n)
- [ ] Avaliar: A/B testing de estratégias
- [ ] Documentar: Best config encontrado

**Meta:** Sistema otimizado e mensurável

---

## 🎯 MÉTRICAS DE SUCESSO

| Métrica | Baseline Atual | Meta Sprint 2 | Meta Sprint 4 |
|---------|----------------|---------------|---------------|
| **RAGAS Faithfulness** | ? | >0.90 | >0.95 |
| **RAGAS Answer Relevancy** | ? | >0.85 | >0.92 |
| **Context Precision** | ? | >0.80 | >0.90 |
| **User Satisfaction** | Incompleto | Bom | Excelente |
| **Latência (p95)** | ~3-5s | <6s | <5s |

---

## 💡 PRINCIPAIS TAKEAWAYS

### ✅ O que aprendemos:

1. **Chunking é crítico:** Tabelas NUNCA devem ser chunkeadas
2. **Hybrid > Vector alone:** BM25+Vector supera vector search puro
3. **Contexto é tudo:** Contextual retrieval reduz erros em 49%
4. **Metadata rico:** Enriquecer metadata aumenta precision 40%
5. **Resumos perdem info:** Sempre incluir texto original + resumo
6. **Evaluation é obrigatório:** RAGAS para medir progresso
7. **Portuguese matters:** Cohere Rerank 3.5 é state-of-the-art para português

### 🚀 Quick Wins (Implementar JÁ):

1. ✅ **Tabelas inteiras** - FEITO
2. ✅ **Texto original + resumo** - FEITO
3. ✅ **OCR português** - FEITO
4. ⏳ **Hybrid Search** - EM PROGRESSO
5. ⏳ **Metadata básico enriquecido** - EM PROGRESSO

### 🎓 Long-term Exploration:

- GraphRAG para multi-hop reasoning
- Fine-tuning embeddings para domínio médico
- Custom reranker treinado em pares query-document médicos

---

## 📚 REFERÊNCIAS

### Chunking
- Unstructured: Chunking Best Practices
- NVIDIA: Finding the Best Chunking Strategy
- Databricks: Ultimate Guide to Chunking Strategies

### Embeddings & Retrieval
- Anthropic: Contextual Retrieval (2024)
- LangChain: MultiVectorRetriever Documentation
- Cohere: Rerank 3.5 Release Notes

### Advanced RAG
- HyDE: Hypothetical Document Embeddings
- GraphRAG: Microsoft Research
- Adaptive RAG: LangGraph Documentation

### Evaluation
- RAGAS Framework Documentation
- LangFuse: Evaluation of RAG with RAGAS

---

**Documento criado em:** 2025-10-18
**Última atualização:** 2025-10-18
**Status:** ✅ Pesquisa completa, recomendações priorizadas
