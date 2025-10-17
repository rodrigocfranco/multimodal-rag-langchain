# Análise dos Testes Desafiadores e Soluções

## 📊 Resultados dos Testes

### ✅ Sucesso (50% - 3/6 perguntas)

**Q2: Contraindicações da metformina** ✅
- Retornou lista completa e precisa
- Observação: Não separou "absolutas" vs "relativas", mas trouxe todas as informações

**Q5: Valor EXATO de TFG** ✅
- Resposta perfeita: "<30 ml/min/1.73m2"
- Precisão numérica mantida

**Q6: Valores de HbA1c** ✅
- 9 valores listados com contextos corretos
- **Sistema funcionou MUITO BEM aqui!**

---

### ❌ Falhas (50% - 3/6 perguntas)

**Q1: Relação albuminúria e risco CV** ❌
```
Resposta: "A informação solicitada não está presente nos documentos fornecidos"
```

**Causa:** Pergunta abstrata com palavra-chave vaga ("relação")
- Informação ESTÁ no documento ("albuminúria >300mg/g" como critério de muito alto risco)
- Reranker filtrou porque chunk lista critério, mas não explica "relação"

---

**Q3: Quando NÃO usar insulina como primeira linha** ❌
```
Resposta: "A informação solicitada não está presente"
```

**Causa:** Negação + informação implícita
- Documento diz: "Com HbA1c < 7,5% usar iSGLT2" (implica: NÃO use insulina)
- Retrieval não captura lógica inversa

---

**Q4: Glicose jejum normal não descarta diabetes?** ❌
```
Resposta: "A informação solicitada não está presente"
```

**Causa:** Dupla negação
- Embedding fraco com: "normal NÃO descarta"
- Informação provavelmente está (TOTG, HbA1c como alternativas)

---

## 🔍 Diagnóstico Técnico

### Problema 1: Embeddings Ruins com Negações/Abstrações

**Embeddings (text-embedding-3-large) são FRACOS em:**
- ❌ Negações: "NÃO usar"
- ❌ Abstrações: "relação entre X e Y"
- ❌ Dupla negação: "normal NÃO descarta"
- ❌ Lógica inversa: Query pede "quando NÃO X", documento diz "quando Y"

**Exemplo do problema:**
```
Query: "Qual a relação entre albuminúria e risco cardiovascular?"
Embedding: representa "albuminúria" + "risco" + "relação" (vago)

Chunk: "Critérios de muito alto risco: albuminúria >300mg/g"
Embedding: representa "albuminúria" + "risco" + "critérios" (específico)

Cosine similarity: 0.85 (bom!)
Mas Cohere Reranker vê:
  - Query pede "relação" (explicação)
  - Chunk lista "critérios" (fato)
  → Score: 0.3 (baixo) → FILTRADO!
```

---

### Problema 2: Chunking Fragmenta Contexto

**Cenário:**

**Chunk 1:**
```
"Critérios de muito alto risco cardiovascular: albuminúria >300mg/g"
```

**Chunk 2 (em outra parte do documento):**
```
"A presença de albuminúria é um marcador de lesão endotelial
e está associada a aumento de eventos cardiovasculares"
```

**O que acontece:**
- Query: "Qual a relação entre albuminúria e risco CV?"
- **Chunk 2 seria PERFEITO** (explica a relação!)
- **Mas Chunk 1 tem score maior** (mais keywords)
- **Reranker prioriza Chunk 1** (denso, mas não explica)
- **LLM recebe Chunk 1**, que não responde "relação"

---

### Problema 3: top_n=5 Muito Restritivo

**Cenário:**
- Busca inicial: 20 chunks
- Cohere ranqueia e retorna **TOP 5**
- Se informação está no **6º melhor**, é PERDIDA

**Para perguntas complexas, precisa de MAIS contexto.**

---

## 🛠️ Soluções Implementadas

### ✅ Solução 1: Aumentar top_n (5 → 8)

**Arquivo:** `consultar_com_rerank.py`

**Mudança:**
```python
# ANTES
compressor = CohereRerank(
    model="rerank-multilingual-v3.0",
    top_n=5  # Apenas 5 documentos
)

# DEPOIS (✅ IMPLEMENTADO)
compressor = CohereRerank(
    model="rerank-multilingual-v3.0",
    top_n=8  # ✅ Aumentado para 8 (60% mais contexto)
)
```

**Por quê ajuda:**
- Mais chunks chegam ao LLM
- Maior chance de pegar chunk com "explicação" da relação (Chunk 2)
- Não prejudica muito a latência (Cohere é rápido)

**Trade-off:**
- ✅ Melhor recall (menos "informação não presente")
- ⚠️ Custo Cohere aumenta ~60% (mas ainda barato: $1/1000 queries)
- ⚠️ Token count do LLM aumenta ~60% (GPT-4o-mini é barato)

---

### 🚀 Solução 2: Melhorar Prompt com "Inferência Moderada"

**Status:** PROPOSTA (não implementada ainda)

**Problema atual:**
Prompt proíbe qualquer inferência:
```
"Responda APENAS com informações EXPLICITAMENTE no contexto"
```

Isso é **BOM** para evitar alucinação, mas **RUIM** para:
- Perguntas sobre "relação" (precisa conectar chunks)
- Negações implícitas ("não usar X" quando documento diz "usar Y")

**Solução:**
Adicionar regra para **inferência moderada**:

```python
system_instruction = """Você é um assistente de pesquisa médica RIGOROSO.

REGRAS CRÍTICAS:
1. Responda APENAS com informações que estão no contexto fornecido
2. Se a informação NÃO estiver no contexto, responda: "A informação solicitada não está presente nos documentos fornecidos"
3. NUNCA use conhecimento geral ou externo
4. Cite EXATAMENTE como está escrito no documento
5. Se houver listas, tabelas ou critérios, reproduza-os FIELMENTE
6. Mantenha formatação original (bullets, números, etc)

🆕 INFERÊNCIAS PERMITIDAS:
7. Se a pergunta pede "relação entre X e Y", você PODE conectar informações
   de DIFERENTES chunks do contexto, desde que cite ambos
8. Se a pergunta pede "quando NÃO fazer X" e o documento diz "fazer Y em situação Z",
   você PODE inferir que "NÃO fazer X quando não estiver na situação Z"
9. SEMPRE cite EXATAMENTE os trechos que usou para fazer a inferência

CONTEXTO DOS DOCUMENTOS:
{context}

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA (baseada SOMENTE no contexto acima):"""
```

**Exemplo de uso:**
```
Query: "Qual a relação entre albuminúria e risco cardiovascular?"

Chunks recebidos:
[1] "Critérios de muito alto risco CV: albuminúria >300mg/g"
[2] "Albuminúria é marcador de lesão endotelial associada a eventos CV"

Resposta:
"Segundo o documento, a albuminúria está relacionada ao risco
cardiovascular de duas formas:

1. É um CRITÉRIO de muito alto risco cardiovascular quando >300mg/g [Fonte: chunk 1]
2. É um MARCADOR de lesão endotelial associada a aumento de eventos
   cardiovasculares [Fonte: chunk 2]

Portanto, a presença de albuminúria (especialmente >300mg/g) indica
maior risco cardiovascular."
```

**Trade-off:**
- ✅ Responde perguntas abstratas/relacionais
- ✅ Lida com negações implícitas
- ⚠️ **RISCO:** LLM pode "inferir demais" e alucinar
- ⚠️ Precisa testar cuidadosamente

**Recomendação:** Testar com `top_n=8` primeiro. Se ainda falhar Q1/Q3/Q4, implementar esta solução.

---

### 🔬 Solução 3: Query Expansion (Avançado)

**Status:** PROPOSTA (não implementada)

**Como funciona:**
Antes de fazer embedding search, expandir query para incluir sinônimos/reformulações:

```python
def expand_query(question):
    """Usa GPT-4o-mini para gerar queries alternativas"""
    prompt = f"""
Dada esta pergunta médica:
"{question}"

Gere 3 reformulações que preservem o significado mas usem palavras diferentes.

Exemplos:
- "relação entre X e Y" → "como X afeta Y", "associação entre X e Y", "X está relacionado a Y"
- "quando NÃO usar X" → "contraindicações de X", "situações onde X é inadequado"

Retorne apenas as 3 reformulações, uma por linha.
"""
    # Chamar GPT-4o-mini (barato)
    expansions = gpt_mini.invoke(prompt).split('\n')
    return [question] + expansions  # Query original + 3 variações
```

Então buscar com TODAS as variações:
```python
queries = expand_query("Qual a relação entre albuminúria e risco CV?")
# queries = [
#   "Qual a relação entre albuminúria e risco CV?",
#   "Como albuminúria afeta risco cardiovascular?",
#   "Associação entre albuminúria e eventos cardiovasculares",
#   "Albuminúria está relacionada a risco CV?"
# ]

all_docs = []
for q in queries:
    docs = vectorstore.similarity_search(q, k=5)  # 5 docs por query
    all_docs.extend(docs)

# Remover duplicatas
unique_docs = remove_duplicates(all_docs)  # ~15-18 docs únicos

# Rerank todos
reranked = cohere.rerank(unique_docs, original_question, top_n=8)
```

**Por quê ajuda:**
- Query "associação entre" pode encontrar Chunk 2 (que usa "associada")
- Query "contraindicações" encontra chunks de negação

**Trade-off:**
- ✅ Recall MUITO melhor
- ❌ 4x mais chamadas ao vectorstore (latência +300ms)
- ❌ Mais custos de Cohere rerank
- ❌ Complexidade de implementação

**Recomendação:** Implementar APENAS se Solução 1+2 falharem.

---

## 📈 Roadmap de Melhorias

### Fase 1: Quick Win (✅ FEITO)
- [x] Aumentar `top_n` de 5 → 8
- [ ] Testar com queries Q1, Q3, Q4
- [ ] Validar que não piorou Q2, Q5, Q6

**Expectativa:** Resolver 1-2 das 3 falhas (provavelmente Q1 e Q4)

---

### Fase 2: Prompt Engineering (Se Fase 1 não resolver tudo)
- [ ] Implementar regras de "inferência moderada"
- [ ] Testar com 10 perguntas (as 6 atuais + 4 novas)
- [ ] Validar que não há alucinação

**Expectativa:** Resolver Q3 (negações implícitas)

---

### Fase 3: Query Expansion (Apenas se necessário)
- [ ] Implementar expand_query()
- [ ] Testar latência (<3s aceitável)
- [ ] Validar custo-benefício

**Expectativa:** Resolver 100% das queries (mas pode ser overkill)

---

## 🧪 Como Testar as Melhorias

### Teste 1: Verificar se top_n=8 melhorou

**Usar /debug-retrieval:**
```
Query: "Qual a relação entre albuminúria e risco cardiovascular?"

ANTES (top_n=5):
  reranked.count: 5
  Chunks: [...]

DEPOIS (top_n=8):
  reranked.count: 8
  Chunks: [...]  ← Verificar se Chunk 2 apareceu!
```

---

### Teste 2: Refazer perguntas falhadas

**Q1:** "Qual a relação entre albuminúria e risco cardiovascular?"
- ✅ **Sucesso:** Retorna explicação conectando critérios + marcador
- ❌ **Falha:** Ainda diz "não está presente"

**Q3:** "Em quais situações a diretriz recomenda NÃO usar insulina como primeira linha?"
- ✅ **Sucesso:** Retorna "HbA1c < 7,5%, usar iSGLT2 em monoterapia"
- ❌ **Falha:** Ainda diz "não está presente"

**Q4:** "Existem situações onde glicose em jejum normal NÃO descarta diabetes?"
- ✅ **Sucesso:** Retorna "Sim, diabetes pode ser diagnosticado por HbA1c ou TOTG"
- ❌ **Falha:** Ainda diz "não está presente"

---

### Teste 3: Validar que queries boas não pioraram

**Refazer Q2, Q5, Q6:**
- Devem continuar com respostas perfeitas
- Se pioraram, considerar voltar `top_n=5` e tentar Solução 2

---

## 💡 Recomendação Imediata

**Próximos passos:**

1. ✅ **Deploy top_n=8** (já commitado)
2. ⏳ **Aguardar deploy Railway** (1-2 min)
3. 🧪 **Testar Q1, Q3, Q4** no /chat
4. 📊 **Usar /debug** para entender o que mudou
5. 📝 **Reportar resultados**

**Se top_n=8 resolver 1-2 das falhas:** ✅ Sucesso! Ótimo custo-benefício.

**Se ainda falhar as 3:** Implementar Solução 2 (inferência moderada).

**Se Solução 2 não resolver:** Considerar Solução 3 (query expansion).

---

## 🎯 Meta de Sucesso

**Ideal:** 5/6 ou 6/6 perguntas corretas (83-100%)

**Aceitável:** 4/6 perguntas corretas (67%) - Perguntas muito abstratas podem ser edge cases

**Inaceitável:** <4/6 (67%) - Significa que retrieval está fundamentalmente quebrado

---

**Status atual:** 3/6 (50%) → Precisa de melhoria

**Após top_n=8:** Expectativa 4-5/6 (67-83%)

**Após prompt engineering:** Expectativa 5-6/6 (83-100%)
