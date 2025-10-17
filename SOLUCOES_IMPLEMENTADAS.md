# 🔧 Soluções Implementadas para Melhorar Respostas da IA

## 📊 Resumo do Problema

**Taxa de sucesso original:** 3/6 perguntas (50%)

**Perguntas que falharam:**
1. ❌ "Qual a relação entre albuminúria e risco cardiovascular?"
2. ❌ "Em quais situações a diretriz recomenda NÃO usar insulina como primeira linha?"
3. ❌ "Existem situações onde glicose em jejum normal NÃO descarta diabetes?"

---

## 🎯 Root Causes Identificadas

### Causa 1: Prompt Extremamente Restritivo
O prompt original proibia **qualquer inferência lógica**, mesmo quando a informação estava presente em múltiplos chunks:

```python
"1. Responda APENAS com informações que estão EXPLICITAMENTE no contexto"
```

**Problema:** Perguntas sobre "relação", negações ("NÃO usar"), e duplas negações ("NÃO descarta") exigem conectar informações dispersas.

### Causa 2: Embeddings Fracos com Negações/Abstrações
- OpenAI embeddings (`text-embedding-3-large`) têm dificuldade com:
  - ❌ Negações: "quando **NÃO** usar"
  - ❌ Abstrações: "**relação** entre X e Y"
  - ❌ Dupla negação: "**NÃO descarta**"

### Causa 3: top_n=8 Insuficiente para Perguntas Complexas
- Reranker retornava apenas os **top 8** chunks
- Perguntas abstratas podem precisar de **10-12 chunks** para encontrar todas as informações relevantes

---

## ✅ Soluções Implementadas

### Solução 1: Novo Prompt com "Inferência Moderada Guiada" 🔥

**Arquivo:** `consultar_com_rerank.py` (linhas 171-187 e 891-908)

**Mudanças:**

```python
# ❌ ANTES (muito restritivo)
"""
REGRAS CRÍTICAS:
1. Responda APENAS com informações que estão EXPLICITAMENTE no contexto
2. Se NÃO estiver no contexto, responda: "A informação não está presente"
3. NUNCA use conhecimento externo
"""

# ✅ DEPOIS (permite inferência lógica documentada)
"""
REGRAS CRÍTICAS:
1. Responda APENAS com informações que estão no contexto fornecido
2. NUNCA use conhecimento geral ou externo aos documentos
3. Cite EXATAMENTE como está escrito no documento

INFERÊNCIAS PERMITIDAS (apenas quando necessário):
6. Se a pergunta pede "relação entre X e Y", você PODE conectar informações de
   DIFERENTES trechos do contexto, citando AMBOS
7. Se a pergunta pede "quando NÃO fazer X" e o contexto diz "fazer Y em situação Z",
   você PODE inferir logicamente, citando o trecho original
8. Se a pergunta usa negação ("NÃO descarta", "NÃO é recomendado"), procure
   informações complementares no contexto que respondam indiretamente

REGRA FINAL:
9. Se após tentar conexões lógicas a informação AINDA não puder ser inferida do
   contexto, responda: "A informação solicitada não está presente nos documentos"
"""
```

**Por que isso ajuda:**
- ✅ Permite conectar "critérios de risco" + "marcador de lesão endotelial" → "relação entre albuminúria e risco CV"
- ✅ Permite inferir "NÃO usar insulina" a partir de "usar iSGLT2 quando HbA1c < 7,5%"
- ✅ Mantém rigor: exige citação dos trechos usados
- ✅ Anti-alucinação: se não houver base lógica, ainda responde "informação não presente"

---

### Solução 2: Aumentar top_n (8 → 10) 📈

**Arquivo:** `consultar_com_rerank.py` (linhas 108-111 e 806-809)

```python
# ❌ ANTES
compressor = CohereRerank(
    model="rerank-multilingual-v3.0",
    top_n=8  # Apenas 8 documentos
)

# ✅ DEPOIS
compressor = CohereRerank(
    model="rerank-multilingual-v3.0",
    top_n=10  # 25% mais contexto
)
```

**Por que isso ajuda:**
- ✅ Mais chunks chegam ao LLM (10 vs 8 = +25% de contexto)
- ✅ Maior probabilidade de incluir chunk com "explicação" da relação
- ✅ Cohere é rápido, não impacta muito a latência

**Trade-offs:**
- ⚠️ Custo Cohere aumenta ~25% (mas ainda barato: ~$1/1000 queries)
- ⚠️ Token count do LLM aumenta ~25% (GPT-4o-mini é barato: ~$0.15/1M tokens)
- ✅ Impacto na latência: ~100-150ms adicionais (aceitável)

---

### Solução 3: Aumentar k do Base Retriever (20 → 25) 🔍

**Arquivo:** `consultar_com_rerank.py` (linhas 63-68 e 760-765)

```python
# ❌ ANTES
base_retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key="doc_id",
    search_kwargs={"k": 20}
)

# ✅ DEPOIS
base_retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key="doc_id",
    search_kwargs={"k": 25}  # +25% de chunks para reranking
)
```

**Por que isso ajuda:**
- ✅ Mais diversidade de chunks antes do reranking
- ✅ Compensa embeddings fracos com negações (busca inicial pega mais variações)
- ✅ ChromaDB não tem indexação HNSW no Railway, então k maior ajuda na cobertura

---

## 🧪 Como Testar as Melhorias

### Teste 1: Perguntas que Falharam Originalmente

**Refazer as 3 perguntas problemáticas:**

```bash
# Iniciar servidor
python consultar_com_rerank.py --api

# Em outro terminal, testar:
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual a relação entre albuminúria e risco cardiovascular segundo a diretriz brasileira de diabetes 2025?"}'

curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Em quais situações a diretriz recomenda NÃO usar insulina como primeira linha no DM2?"}'

curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Existem situações onde glicose em jejum normal NÃO descarta diabetes?"}'
```

**Critério de sucesso:**
- ✅ **Ideal:** Respostas substantivas citando trechos do documento
- ⚠️ **Aceitável:** Resposta parcial com citação correta
- ❌ **Falha:** "A informação não está presente nos documentos"

---

### Teste 2: Verificar que Perguntas Boas NÃO Pioraram

**Refazer as 3 perguntas que funcionavam:**

```bash
# Q2: Contraindicações da metformina
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Quais são as contraindicações absolutas e relativas da metformina mencionadas no documento?"}'

# Q5: Valor exato de TFG
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual o valor EXATO de TFG que define risco cardiovascular muito alto segundo a diretriz?"}'

# Q6: Valores de HbA1c
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Liste TODOS os valores de HbA1c mencionados no documento e seus respectivos contextos de uso"}'
```

**Critério de sucesso:**
- ✅ Respostas devem ser **tão boas ou melhores** que antes
- ❌ Se pioraram, pode indicar que top_n=10 está trazendo ruído

---

### Teste 3: Debug do Retrieval

**Verificar QUANTOS chunks estão sendo retornados:**

```bash
curl -X POST http://localhost:5001/debug-retrieval \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual a relação entre albuminúria e risco cardiovascular?"}'
```

**O que analisar:**
- `raw_retrieval.count`: Deve ser **~25** (k=25)
- `reranked.count`: Deve ser **10** (top_n=10)
- `reranked.docs[].content_preview`: Verificar se há chunks sobre "albuminúria" + "risco CV" + "critérios" + "marcador"

---

## 📊 Resultados Esperados

### Cenário Ideal (90-100% de sucesso)
| Pergunta | Status Antes | Status Esperado Depois |
|----------|-------------|------------------------|
| Q1: Relação albuminúria e risco CV | ❌ | ✅ |
| Q2: Contraindicações metformina | ✅ | ✅ |
| Q3: Quando NÃO usar insulina | ❌ | ✅ |
| Q4: Glicose normal NÃO descarta DM | ❌ | ✅ |
| Q5: Valor exato TFG | ✅ | ✅ |
| Q6: Valores HbA1c | ✅ | ✅ |
| **Taxa de sucesso** | **50%** | **100%** |

### Cenário Realista (70-85% de sucesso)
- Q1 e Q4 resolvidas (prompt de inferência ajuda)
- Q3 ainda pode falhar (negação muito complexa)
- **Taxa de sucesso esperada: 5/6 (83%)**

### Cenário Mínimo Aceitável (67% de sucesso)
- Pelo menos 1 das 3 falhas foi resolvida
- Nenhuma das 3 perguntas boas piorou
- **Taxa de sucesso: 4/6 (67%)**

---

## 🚨 Rollback (se necessário)

Se as mudanças **piorarem** o desempenho geral:

### Reverter Solução 1 (Prompt):
```bash
git diff HEAD~1 consultar_com_rerank.py | grep "system_instruction"
# Copiar prompt antigo de volta
```

### Reverter Soluções 2 e 3 (top_n e k):
```python
# Voltar para:
top_n=8  # Era 10
search_kwargs={"k": 20}  # Era 25
```

---

## 🎯 Próximos Passos Caso as Soluções Não Funcionem

### Solução Avançada 1: Query Expansion
Se Q1 e Q3 ainda falharem, implementar **expansão de query**:
- Usar GPT-4o-mini para gerar 3 reformulações da pergunta
- Buscar com todas as variações
- Rerank todos os resultados
- **Custo:** +$0.001 por query
- **Latência:** +300-500ms

### Solução Avançada 2: Hybrid Search (BM25 + Embeddings)
Para negações e termos exatos:
- Adicionar BM25 (busca lexical) ao lado dos embeddings
- Combinar resultados com Reciprocal Rank Fusion
- **Complexidade:** Alta
- **Ganho esperado:** +10-15% de precisão

### Solução Avançada 3: Chunking Semântico Melhorado
Re-processar PDFs com:
- Chunks maiores (1500 tokens vs 1000)
- Overlap maior (200 tokens vs 100)
- **Custo:** Reprocessar todos os PDFs
- **Ganho esperado:** +5-10% de recall

---

## 📈 Métricas de Sucesso

**Imediato (após deploy):**
- [ ] Taxa de sucesso ≥ 67% (4/6 perguntas)
- [ ] Latência média < 3 segundos
- [ ] Custo por query < $0.01

**Médio prazo (1 semana de uso):**
- [ ] Taxa de satisfação do usuário ≥ 80%
- [ ] Taxa de "informação não presente" < 20%
- [ ] Tempo médio de resposta < 2.5 segundos

**Longo prazo (1 mês):**
- [ ] Taxa de sucesso ≥ 90% em perguntas complexas
- [ ] Zero alucinações detectadas
- [ ] Custo operacional < $50/mês

---

## 🔍 Comandos Úteis para Monitoramento

### Ver logs em produção (Railway)
```bash
railway logs --follow
```

### Testar localmente
```bash
python consultar_com_rerank.py --api
# Abrir http://localhost:5001/chat
```

### Comparar performance antes/depois
```bash
# Salvar respostas antigas
curl ... > respostas_antes.json

# Salvar respostas novas
curl ... > respostas_depois.json

# Comparar
diff respostas_antes.json respostas_depois.json
```

---

**Data de implementação:** 2025-10-17
**Versão do código:** consultar_com_rerank.py (commit atual)
**Status:** ✅ Implementado, aguardando testes
