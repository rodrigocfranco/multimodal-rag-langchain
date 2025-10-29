# Plano de Testes e Validação - Outubro 2025

## 🎯 Objetivo
Validar todas as implementações e ajustes realizados no sistema RAG multimodal.

---

## 📋 Checklist de Mudanças Implementadas

### ✅ Infraestrutura
- [x] ChromaDB 0.5.x → 1.3.0 (Rust engine)
- [x] LangChain 1.0.x → 0.3.x (compatibilidade Cohere)
- [x] Cohere Rerank v3.0 → v3.5 (unified multilingual)
- [x] Volume Railway: /app/knowledge → /app/base
- [x] Healthcheck inteligente implementado
- [x] Dependabot configurado

### ✅ Features
- [x] LLM Query Generation (+30-40% recall)
- [x] KeyBERT keyword extraction
- [x] BM25 + Vector hybrid search
- [x] Cohere Rerank v3.5 (4096 tokens context)

---

## 🧪 Testes a Realizar

### 1. **Teste de Healthcheck e Inicialização** ⚡
**Objetivo:** Verificar se o sistema inicia corretamente no Railway

**Como testar:**
```bash
# Verificar healthcheck
curl https://comfortable-tenderness-production.up.railway.app/health

# Resposta esperada:
{
  "status": "ok",
  "reranker": "cohere",
  "persist_dir": "/app/base",
  "ready": true
}
```

**Critérios de Sucesso:**
- ✅ Status 200
- ✅ `ready: true`
- ✅ `persist_dir: "/app/base"`
- ✅ Responde em <2 segundos

---

### 2. **Teste de Compatibilidade ChromaDB 1.3.0** 💾
**Objetivo:** Validar que ChromaDB 1.3.0 funciona corretamente

**Como testar:**
```bash
# Verificar volume e vectorstore
curl https://comfortable-tenderness-production.up.railway.app/debug-volume

# Fazer upload de PDF de teste
curl -X POST https://comfortable-tenderness-production.up.railway.app/upload \
  -F "pdf=@documento_teste.pdf"
```

**Critérios de Sucesso:**
- ✅ Volume montado em /app/base
- ✅ ChromaDB cria collection sem erros
- ✅ PDF processado com sucesso
- ✅ Embeddings criados corretamente

---

### 3. **Teste de Cohere Rerank v3.5** 🔥
**Objetivo:** Validar upgrade do reranker e suas melhorias

**Como testar:**
```bash
# Query complexa que se beneficia de v3.5
curl -X POST https://comfortable-tenderness-production.up.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o tratamento da síndrome de lise tumoral segundo critérios de cairo-bishop em pacientes graves com insuficiência renal?"
  }'
```

**O que observar nos logs do Railway:**
- ✅ Modelo usado: `rerank-v3.5`
- ✅ Contexto maior (até 4096 tokens)
- ✅ Melhor ranking de documentos relevantes
- ✅ Resposta coerente e completa

**Critérios de Sucesso:**
- ✅ Resposta relevante baseada em múltiplos documentos
- ✅ Compreensão de constraints implícitas ("graves", "com insuficiência")
- ✅ Tempo de resposta <10 segundos

---

### 4. **Teste de LLM Query Generation** 🤖
**Objetivo:** Verificar se múltiplas queries estão sendo geradas

**Como testar:**
```bash
# Query que se beneficia de reformulação
curl -X POST https://comfortable-tenderness-production.up.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Como tratar DM tipo 2 descompensado?"
  }'
```

**Verificar nos logs do Railway:**
```
🚀 LLM QUERY GENERATION
Original query: Como tratar DM tipo 2 descompensado?
Generated queries:
1. Tratamento diabetes mellitus tipo 2 descompensado
2. Diabetes tipo 2 com hiperglicemia controle
3. DM2 descompensado manejo terapêutico
```

**Critérios de Sucesso:**
- ✅ 3-5 queries alternativas geradas
- ✅ Expansão de abreviações (DM → diabetes mellitus)
- ✅ Termos técnicos adicionados
- ✅ Recall melhorado (mais documentos relevantes)

---

### 5. **Teste de KeyBERT Keyword Extraction** 🔑
**Objetivo:** Validar extração de palavras-chave

**Como testar:**
```bash
curl -X POST https://comfortable-tenderness-production.up.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Protocolo de sepse grave com choque séptico em UTI"
  }'
```

**Verificar nos logs:**
```
🔑 Keywords extraídas (KeyBERT): ['sepse grave', 'choque séptico', 'protocolo UTI']
```

**Critérios de Sucesso:**
- ✅ Top 3 keywords extraídas
- ✅ Keywords relevantes ao contexto médico
- ✅ Melhor precisão na busca

---

### 6. **Teste de Hybrid Search (BM25 + Vector)** 🔍
**Objetivo:** Validar busca híbrida funcionando

**Como testar:**
```bash
# Query com termos técnicos exatos
curl -X POST https://comfortable-tenderness-production.up.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Critérios de Cairo-Bishop para síndrome de lise tumoral"
  }'
```

**O que observar:**
- ✅ BM25 encontra "Cairo-Bishop" (match exato)
- ✅ Vector search encontra conceitos relacionados
- ✅ Ensemble combina resultados (40% BM25, 60% Vector)

**Critérios de Sucesso:**
- ✅ Encontra documento com termo exato "Cairo-Bishop"
- ✅ Também traz documentos semanticamente relacionados
- ✅ Ranking final balanceado

---

### 7. **Teste de Detecção de Queries Visuais** 🖼️
**Objetivo:** Validar detecção automática de queries sobre imagens

**Como testar:**
```bash
# Query sobre imagem/figura
curl -X POST https://comfortable-tenderness-production.up.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Mostre a figura do algoritmo de manejo da sepse"
  }'
```

**Verificar nos logs:**
```
🖼️ QUERY VISUAL DETECTADA
Keywords encontradas: ['figura', 'algoritmo']
Buscando imagens com prioridade...
```

**Critérios de Sucesso:**
- ✅ Query detectada como visual
- ✅ Imagens/figuras priorizadas
- ✅ Resposta inclui imagens relevantes

---

### 8. **Teste de Performance e Latência** ⚡
**Objetivo:** Medir tempos de resposta

**Como testar:**
```bash
# Rodar script de performance
python test_performance.py
```

**Benchmarks esperados:**
- ✅ **Carregamento:** <5 segundos
- ✅ **Query simples:** <3 segundos
- ✅ **Query complexa:** <10 segundos
- ✅ **Reranking overhead:** <1 segundo
- ✅ **LLM query generation:** <2 segundos

---

### 9. **Teste de Multilíngue (Português)** 🇧🇷
**Objetivo:** Validar suporte a português do Cohere v3.5

**Como testar:**
```bash
# Queries em português com termos técnicos
curl -X POST https://comfortable-tenderness-production.up.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais os critérios diagnósticos de SDRA segundo Berlin?"
  }'
```

**Critérios de Sucesso:**
- ✅ Compreensão correta de português
- ✅ Reranking funciona bem com termos médicos em PT
- ✅ Resposta precisa e relevante
- ✅ Abreviações entendidas (SDRA)

---

### 10. **Teste de Volume e Persistência** 💾
**Objetivo:** Validar novo volume /app/base

**Como testar:**
```bash
# 1. Fazer upload de PDF
curl -X POST https://comfortable-tenderness-production.up.railway.app/upload \
  -F "pdf=@teste.pdf"

# 2. Verificar que foi salvo
curl https://comfortable-tenderness-production.up.railway.app/documents

# 3. Fazer query
curl -X POST https://comfortable-tenderness-production.up.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "conteúdo do PDF teste"}'

# 4. Redeploy no Railway (simula restart)

# 5. Verificar que PDF ainda existe
curl https://comfortable-tenderness-production.up.railway.app/documents
```

**Critérios de Sucesso:**
- ✅ PDF salvo em /app/base
- ✅ Dados persistem após redeploy
- ✅ Chroma DB mantém embeddings

---

### 11. **Teste de Dependências** 📦
**Objetivo:** Validar que todas as versões são compatíveis

**Como testar:**
```bash
# Verificar logs de build no Railway
# Procurar por:
✅ Successfully installed chromadb-1.3.x
✅ Successfully installed langchain-0.3.x
✅ Successfully installed langchain-chroma-0.2.3
✅ Successfully installed langchain-cohere-0.4.6
✅ No dependency conflicts
```

**Critérios de Sucesso:**
- ✅ Build completa sem erros
- ✅ Todas as versões corretas instaladas
- ✅ Sem conflitos de dependências

---

### 12. **Teste de Stress/Carga** 💪
**Objetivo:** Verificar comportamento sob carga

**Como testar:**
```bash
# Script de teste de stress
python test_stress_rag.py
```

**Cenários:**
- ✅ 10 queries simultâneas
- ✅ Upload de múltiplos PDFs
- ✅ Queries longas (>1000 caracteres)
- ✅ Queries com caracteres especiais

**Critérios de Sucesso:**
- ✅ Sistema responde todas as queries
- ✅ Sem timeouts
- ✅ Sem memory leaks
- ✅ Healthcheck continua OK

---

## 📊 Métricas de Sucesso Global

### Performance
- [ ] Latência média <5s
- [ ] Healthcheck <2s
- [ ] Build time <5min
- [ ] 99% uptime

### Qualidade
- [ ] Recall: +30-40% vs baseline (LLM query generation)
- [ ] Precision: +30-40% vs sem rerank
- [ ] Respostas relevantes: >90%
- [ ] Detecção de queries visuais: >95%

### Estabilidade
- [ ] Zero crashes em 24h
- [ ] Healthcheck sempre passa
- [ ] Volume persiste após redeploy
- [ ] Sem conflitos de dependências

---

## 🔧 Ferramentas de Teste

### Scripts Disponíveis:
1. `test_llm_query_generation.py` - Testa query generation
2. `test_performance.py` - Benchmarks de performance
3. `test_stress_rag.py` - Teste de stress
4. `test_queries.py` - Suite de queries de teste
5. `test_validation_suite.py` - Validação completa

### Endpoints de Debug:
- `/health` - Healthcheck
- `/debug-volume` - Info do volume
- `/debug-retrieval` - Debug retrieval
- `/documents` - Lista PDFs
- `/` - Documentação da API

---

## 📝 Template de Relatório de Testes

```markdown
## Relatório de Testes - [Data]

### Ambiente
- Railway URL: https://comfortable-tenderness-production.up.railway.app
- ChromaDB: 1.3.x
- Cohere Rerank: v3.5
- LangChain: 0.3.x

### Resultados

#### ✅ Testes Passaram (X/12)
- [x] Healthcheck
- [x] ChromaDB 1.3.0
- [ ] ...

#### ❌ Testes Falharam
- Nenhum / [Descrever]

#### ⚠️ Observações
- [Listar quaisquer issues menores]

#### 📊 Métricas
- Latência média: Xs
- Recall improvement: +X%
- Precision improvement: +X%

### Recomendações
- [Próximos passos]
```

---

## 🚀 Ordem Sugerida de Execução

1. **Primeiro:** Healthcheck (validar que está rodando)
2. **Segundo:** Volume e ChromaDB (validar persistência)
3. **Terceiro:** Upload de PDF teste (validar pipeline)
4. **Quarto:** Queries simples (validar retrieval básico)
5. **Quinto:** Features avançadas (LLM generation, rerank, etc)
6. **Sexto:** Performance e stress (validar sob carga)
7. **Sétimo:** Documentar resultados

---

## 📞 Em Caso de Problemas

### Healthcheck Falha
1. Verificar logs: Railway → Deployments → View Logs
2. Procurar por: `KeyError`, `ConnectionError`, `TimeoutError`
3. Verificar variáveis de ambiente estão corretas

### Queries Lentas
1. Verificar tamanho do knowledge base
2. Verificar logs de reranking
3. Considerar ajustar `top_n` do reranker

### Respostas Irrelevantes
1. Verificar se LLM query generation está ativo
2. Verificar logs de keywords extraídas
3. Verificar scores do reranker
4. Considerar ajustar weights do hybrid search

---

**Última atualização:** 29 Outubro 2025
**Status:** Pronto para testes
