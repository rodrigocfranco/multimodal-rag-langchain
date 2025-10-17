# 🧪 Perguntas de Teste para Estressar o Sistema RAG

## 📋 Objetivo
Testar limites e pontos fracos do sistema com perguntas progressivamente mais difíceis.

---

## ✅ Categoria 1: PERGUNTAS BÁSICAS (Devem funcionar 100%)

### 1.1 Busca Direta de Valores Numéricos
```
Q1: Qual o valor de TFG que define insuficiência renal crônica?
Q2: Em qual porcentagem a metformina reduz o risco de IAM segundo o UKPDS?
Q3: Qual o alvo de HbA1c recomendado pela diretriz?
```

**Expectativa:** ✅ Respostas exatas com citações

---

### 1.2 Listas e Enumerações
```
Q4: Liste todos os iSGLT2 mencionados no documento
Q5: Quais são os critérios de muito alto risco cardiovascular?
Q6: Enumere os efeitos adversos da metformina
```

**Expectativa:** ✅ Listas completas e formatadas

---

## 🔥 Categoria 2: PERGUNTAS COM NEGAÇÕES (50% falham antes da correção)

### 2.1 Negação Simples
```
Q7: Quando NÃO usar metformina?
Q8: Quais medicamentos NÃO são recomendados em pacientes com TFG < 30?
Q9: Em quais situações NÃO se deve fazer insulina como primeira linha?
```

**Expectativa:** ✅ Inferência a partir de contraindicações/recomendações positivas

---

### 2.2 Dupla Negação (Muito difícil!)
```
Q10: Existem casos onde HbA1c normal NÃO exclui o diagnóstico de diabetes?
Q11: Há situações em que controle glicêmico rigoroso NÃO é recomendado?
Q12: TFG acima de 60 NÃO garante ausência de risco cardiovascular. Verdadeiro ou falso?
```

**Expectativa:** ⚠️ Difícil - precisa inferir lógica inversa

---

## 🧠 Categoria 3: RELAÇÕES E CONEXÕES (Falhavam antes)

### 3.1 Relações Causais
```
Q13: Qual a relação entre HbA1c elevada e complicações microvasculares?
Q14: Como a obesidade influencia a escolha do antidiabético?
Q15: Qual a conexão entre TFG reduzida e dosagem de metformina?
```

**Expectativa:** ✅ Conectar múltiplos chunks

---

### 3.2 Comparações
```
Q16: Compare a eficácia de iSGLT2 vs GLP-1 em pacientes com DRC
Q17: Qual a diferença entre monoterapia e terapia dupla inicial?
Q18: Compare os alvos de HbA1c para pacientes jovens vs idosos
```

**Expectativa:** ✅ Sintetizar informações de diferentes seções

---

## 🎯 Categoria 4: PERGUNTAS CONTEXTUAIS (Precisam de múltiplos chunks)

### 4.1 Fluxos Clínicos
```
Q19: Qual a sequência de escalonamento terapêutico se o paciente falha na monoterapia?
Q20: Descreva o algoritmo de escolha do antidiabético em paciente com ICC
Q21: Como ajustar a terapia se HbA1c permanecer > 7% após 3 meses?
```

**Expectativa:** ✅ Narrativa coerente conectando múltiplos passos

---

### 4.2 Casos Clínicos Implícitos
```
Q22: Paciente com DM2, obesidade e HbA1c 8,5%. Qual terapia inicial recomendada?
Q23: Mulher com DM2, TFG 25 ml/min e DCV prévia. Posso usar metformina?
Q24: Idoso frágil, HbA1c 9%, sem DCV. Qual meta glicêmica adequada?
```

**Expectativa:** ⚠️ Muito difícil - precisa conectar múltiplos critérios

---

## 🔬 Categoria 5: PERGUNTAS AMBÍGUAS OU INCOMPLETAS

### 5.1 Perguntas Vagas
```
Q25: Quais os benefícios dos iSGLT2? (Sem especificar qual aspecto)
Q26: Como tratar diabetes? (Muito aberta)
Q27: O que diz sobre insulina? (Sem contexto)
```

**Expectativa:** ⚠️ Sistema deve dar resposta abrangente OU pedir clarificação

---

### 5.2 Perguntas com Informação Errada
```
Q28: Qual a dose máxima de iSGLT2 em pacientes com TFG < 15? (iSGLT2 é contraindicado!)
Q29: A metformina é recomendada em gestantes com DM2? (NÃO!)
Q30: HbA1c abaixo de 5% é o alvo ideal? (Risco de hipoglicemia!)
```

**Expectativa:** ✅ Deve CORRIGIR a premissa falsa baseado no documento

---

## 🚨 Categoria 6: PERGUNTAS ARMADILHA (Testam alucinação)

### 6.1 Informação NÃO presente no documento
```
Q31: Qual o custo médio do tratamento com iSGLT2 no Brasil?
Q32: Quantos pacientes foram incluídos no estudo UKPDS?
Q33: Qual a prevalência de DM2 no Brasil segundo a diretriz?
```

**Expectativa:** ✅ DEVE responder "A informação não está presente nos documentos fornecidos"

---

### 6.2 Perguntas sobre outro documento
```
Q34: Quais são os critérios da ADA para diagnóstico de diabetes? (Se só tem diretriz brasileira)
Q35: O que a diretriz europeia recomenda sobre metformina?
Q36: Como a OMS define síndrome metabólica?
```

**Expectativa:** ✅ DEVE responder "A informação não está presente" (não alucinar!)

---

## 💥 Categoria 7: PERGUNTAS EXTREMAS (Stress test máximo)

### 7.1 Perguntas Muito Longas
```
Q37: Em um paciente de 65 anos, com DM2 há 10 anos, HbA1c 8,2%, IMC 32,
     TFG 45 ml/min, com histórico de IAM há 2 anos, atualmente em uso de
     metformina 2g/dia, qual seria a melhor opção de escalonamento terapêutico
     segundo a diretriz brasileira considerando o perfil de risco cardiovascular
     muito alto e a presença de doença renal crônica moderada?
```

**Expectativa:** ⚠️ Deve processar todas as condições e dar resposta coerente

---

### 7.2 Perguntas Compostas (Múltiplas perguntas em uma)
```
Q38: Quais são as contraindicações da metformina E dos iSGLT2 E quando cada um deve ser preferido?
Q39: Liste os valores de TFG para cada estágio de DRC, as restrições medicamentosas correspondentes
     e os ajustes de dose necessários para metformina em cada caso.
```

**Expectativa:** ⚠️ Deve responder TODAS as partes OU avisar que são múltiplas perguntas

---

### 7.3 Perguntas com Termos Técnicos Variados
```
Q40: Qual a diferença entre clearance de creatinina e taxa de filtração glomerular estimada?
Q41: O que é prontidão terapêutica e por que é importante no DM2?
Q42: Explique a relação entre inércia clínica e controle glicêmico inadequado
```

**Expectativa:** ⚠️ Se os termos estão no documento, deve explicar. Se não, avisar.

---

## 🎭 Categoria 8: PERGUNTAS "HUMANAS" (Como usuários reais perguntam)

### 8.1 Linguagem Coloquial
```
Q43: Meu paciente tá com açúcar de 8 e pouco na hemoglobina. O que faço?
Q44: Posso dar metformina pra quem tem problema no rim?
Q45: Qual remédio é melhor pra quem é gordo e tem diabetes?
```

**Expectativa:** ✅ Deve interpretar ("açúcar" = HbA1c, "gordo" = obesidade)

---

### 8.2 Perguntas em Primeira Pessoa
```
Q46: Sou diabético e minha HbA1c está em 7,5%. Preciso aumentar o remédio?
Q47: Tenho um paciente com DM2 novo. Por onde começar o tratamento?
Q48: Posso usar insulina logo de cara ou tem que tentar comprimido primeiro?
```

**Expectativa:** ✅ Responder no contexto clínico apropriado

---

## 📊 MATRIZ DE PRIORIDADE DE TESTES

### 🔴 **CRÍTICO** (Devem passar 100%)
- Categoria 1: Perguntas básicas
- Categoria 6: Armadilhas de alucinação
- Q7, Q8, Q9 (negações simples)

### 🟡 **IMPORTANTE** (≥ 80% de sucesso)
- Categoria 3: Relações e conexões
- Categoria 4.1: Fluxos clínicos
- Categoria 8: Linguagem humana

### 🟢 **DESEJÁVEL** (≥ 60% de sucesso)
- Categoria 2.2: Dupla negação
- Categoria 4.2: Casos clínicos
- Categoria 5: Perguntas ambíguas
- Categoria 7: Perguntas extremas

---

## 🧪 PROTOCOLO DE TESTE

### Fase 1: Smoke Test (10 perguntas - 5 minutos)
```
Q1, Q4, Q5, Q7, Q13, Q19, Q22, Q28, Q31, Q43
```
**Meta:** 8/10 (80%) de sucesso

---

### Fase 2: Teste de Regressão (Perguntas originais - 3 minutos)
```
Q_original_1: Relação albuminúria e risco CV
Q_original_2: Contraindicações metformina
Q_original_3: Quando NÃO usar insulina
Q_original_4: Glicose jejum NÃO descarta diabetes
Q_original_5: Valor exato TFG
Q_original_6: Valores HbA1c
```
**Meta:** 5-6/6 (83-100%) - NÃO pode piorar!

---

### Fase 3: Teste Completo (48 perguntas - 30 minutos)
```
Todas as categorias
```

**Metas por categoria:**
- Cat 1: 6/6 (100%) ✅
- Cat 2: 4/6 (67%) ⚠️
- Cat 3: 5/6 (83%) ✅
- Cat 4: 4/6 (67%) ⚠️
- Cat 5: 3/6 (50%) ⚠️
- Cat 6: 6/6 (100%) ✅ CRÍTICO
- Cat 7: 2/6 (33%) - edge cases
- Cat 8: 5/6 (83%) ✅

**Meta geral:** ≥ 35/48 (73%)

---

## 📈 SCRIPT DE TESTE AUTOMATIZADO

```bash
#!/bin/bash
# test_rag.sh

API_URL="http://localhost:5001/query"
RESULTS_FILE="test_results_$(date +%Y%m%d_%H%M%S).json"

echo "🧪 Iniciando teste de stress do RAG..." > $RESULTS_FILE

# Função para testar uma pergunta
test_question() {
  local qnum=$1
  local question=$2
  local category=$3

  echo "Testing Q$qnum: $question"

  response=$(curl -s -X POST $API_URL \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"$question\"}")

  echo "{\"question_id\": \"Q$qnum\", \"category\": \"$category\", \"question\": \"$question\", \"response\": $response}" >> $RESULTS_FILE

  sleep 1  # Rate limiting
}

# Smoke Test (10 perguntas críticas)
echo "=== SMOKE TEST ===" >> $RESULTS_FILE
test_question 1 "Qual o valor de TFG que define insuficiência renal crônica?" "basica"
test_question 4 "Liste todos os iSGLT2 mencionados no documento" "basica"
test_question 7 "Quando NÃO usar metformina?" "negacao"
test_question 13 "Qual a relação entre HbA1c elevada e complicações microvasculares?" "relacao"
test_question 19 "Qual a sequência de escalonamento terapêutico se o paciente falha na monoterapia?" "fluxo"
test_question 22 "Paciente com DM2, obesidade e HbA1c 8,5%. Qual terapia inicial recomendada?" "caso_clinico"
test_question 28 "A metformina é recomendada em gestantes com DM2?" "armadilha_corrigir"
test_question 31 "Qual o custo médio do tratamento com iSGLT2 no Brasil?" "armadilha_ausente"
test_question 43 "Meu paciente tá com açúcar de 8 e pouco na hemoglobina. O que faço?" "coloquial"

echo "✅ Teste completo! Resultados em: $RESULTS_FILE"
```

---

## 🎯 CRITÉRIOS DE AVALIAÇÃO

### ✅ Sucesso Total
- Resposta correta
- Cita fontes apropriadas
- Formatação adequada

### ⚠️ Sucesso Parcial
- Resposta incompleta mas correta
- Falta alguma citação
- Formatação imperfeita

### ❌ Falha
- Resposta incorreta
- Alucinação (inventou informação)
- "Informação não presente" quando ESTÁ presente

### 🚨 Falha Crítica (Bug grave!)
- Alucinação em pergunta armadilha (Cat 6)
- Responde com confiança sobre informação ausente
- Contradiz informação do documento

---

## 📝 TEMPLATE DE RELATÓRIO

```markdown
# Relatório de Teste de Stress - RAG System

**Data:** YYYY-MM-DD
**Versão:** consultar_com_rerank.py (commit: XXXXX)
**Configuração:**
- Base retriever k: 25
- Reranker top_n: 10
- Prompt: Inferência moderada guiada

## Resultados por Categoria

| Categoria | Sucesso | Parcial | Falha | Taxa |
|-----------|---------|---------|-------|------|
| 1. Básicas | X/6 | X/6 | X/6 | XX% |
| 2. Negações | X/6 | X/6 | X/6 | XX% |
| 3. Relações | X/6 | X/6 | X/6 | XX% |
| 4. Contextuais | X/6 | X/6 | X/6 | XX% |
| 5. Ambíguas | X/6 | X/6 | X/6 | XX% |
| 6. Armadilhas | X/6 | X/6 | X/6 | XX% |
| 7. Extremas | X/6 | X/6 | X/6 | XX% |
| 8. Humanas | X/6 | X/6 | X/6 | XX% |
| **TOTAL** | **X/48** | **X/48** | **X/48** | **XX%** |

## 🚨 Falhas Críticas
- [ ] Q28: Não corrigiu premissa falsa sobre metformina em gestantes
- [ ] Q31: Alucinação sobre custo de medicamentos

## 💡 Recomendações
1. ...
2. ...
```

---

**Próximo passo:** Execute o smoke test (10 perguntas) e reporte os resultados!
