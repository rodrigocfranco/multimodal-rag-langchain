# 🧪 Suite de Testes - Queries Variadas

**Objetivo:** Validar sistema RAG com Vision API + Hybrid Search antes de novas implementações

**Data:** 2025-10-18

---

## 📋 Categorias de Teste

### 1️⃣ RETRIEVAL DIRETO (Tabelas e Listas)

Testa capacidade de buscar informação estruturada diretamente.

#### Teste 1.1 - Critérios de Risco (JÁ VALIDADO ✅)
```
Query: "Quais os critérios de muito alto risco cardiovascular segundo a diretriz brasileira de diabetes?"

Expectativa:
✅ Deve incluir TODOS os critérios:
   - 3 ou mais fatores de risco
   - Hipercolesterolemia Familiar
   - Albuminúria >300 mg/g
   - TFG <30 ml/min/1.73m²
   - Albuminúria 30-300 + TFG <45
   - Retinopatia proliferativa
   - NAC grave
   - Estenose arterial >50%
   - Síndrome coronariana aguda
   - IAM
   - Doença Coronariana Crônica
   - Angina Estável
   - AVC Isquêmico
   - Ataque isquêmico transitório
   - Doença arterial obstrutiva periférica
   - Amputação
   - Revascularização arterial

Status: ✅ PASSOU (100% completo)
```

#### Teste 1.2 - Outros Níveis de Risco
```
Query: "Quais são os critérios de risco alto cardiovascular?"

Expectativa:
✅ Deve trazer critérios de "ALTO" risco (não muito alto)
❌ Não deve misturar com "muito alto" ou "moderado"
```

#### Teste 1.3 - Risco Moderado
```
Query: "Quais são os critérios de risco moderado cardiovascular?"

Expectativa:
✅ Deve trazer critérios de "MODERADO" risco
```

#### Teste 1.4 - Risco Baixo
```
Query: "Quais são os critérios de risco baixo cardiovascular?"

Expectativa:
✅ Deve trazer critérios de "BAIXO" risco
```

---

### 2️⃣ VALORES NUMÉRICOS (Limiares e Critérios)

Testa precisão em extrair valores específicos.

#### Teste 2.1 - HbA1c para Diagnóstico
```
Query: "Qual o valor de HbA1c para diagnóstico de diabetes?"

Expectativa:
✅ Deve mencionar: HbA1c ≥ 6.5% ou ≥ 48 mmol/mol
✅ Pode mencionar contexto (2 medições, etc.)
```

#### Teste 2.2 - Glicemia de Jejum
```
Query: "Qual o valor de glicemia de jejum para diagnóstico de diabetes?"

Expectativa:
✅ Deve mencionar: ≥ 126 mg/dL
```

#### Teste 2.3 - Metas de Controle Glicêmico
```
Query: "Qual a meta de HbA1c para a maioria dos pacientes com diabetes?"

Expectativa:
✅ Deve mencionar meta individualizada
✅ Provavelmente: <7% para maioria, mas pode variar
```

#### Teste 2.4 - Albuminúria
```
Query: "Quais os valores de albuminúria que definem nefropatia diabética?"

Expectativa:
✅ Moderada: 30-300 mg/g
✅ Grave/Macroalbuminúria: >300 mg/g
```

#### Teste 2.5 - TFG (Taxa de Filtração Glomerular)
```
Query: "Qual o valor de TFG que indica doença renal crônica grave?"

Expectativa:
✅ Deve mencionar categorias (G3, G4, G5)
✅ TFG <30 ml/min/1.73m² (grave)
```

---

### 3️⃣ TRATAMENTOS E MEDICAMENTOS

Testa retrieval de recomendações terapêuticas.

#### Teste 3.1 - Primeira Linha
```
Query: "Qual é a primeira linha de tratamento para diabetes tipo 2?"

Expectativa:
✅ Deve mencionar Metformina (provavelmente)
✅ Pode mencionar mudança de estilo de vida
```

#### Teste 3.2 - Pacientes com Risco Alto
```
Query: "Qual o tratamento recomendado para pacientes com diabetes e risco cardiovascular muito alto?"

Expectativa:
✅ Deve mencionar intensificação de tratamento
✅ Pode mencionar classes específicas (SGLT2i, GLP-1 RA, etc.)
✅ Deve mencionar controle de múltiplos fatores de risco
```

#### Teste 3.3 - Nefropatia Diabética
```
Query: "Como tratar pacientes com diabetes e albuminúria elevada?"

Expectativa:
✅ Deve mencionar controle glicêmico
✅ Deve mencionar IECA ou BRA (inibidores do sistema renina-angiotensina)
✅ Pode mencionar SGLT2i
```

#### Teste 3.4 - Contraindicações
```
Query: "Quando evitar Metformina em pacientes com diabetes?"

Expectativa:
✅ Deve mencionar TFG <30 ml/min (contraindicação)
✅ Pode mencionar TFG 30-45 (cautela/ajuste de dose)
✅ Pode mencionar acidose lática, insuficiência hepática
```

---

### 4️⃣ CLASSIFICAÇÃO E CATEGORIZAÇÃO

Testa capacidade de classificar casos específicos.

#### Teste 4.1 - Classificação por Albuminúria
```
Query: "Um paciente com albuminúria de 350 mg/g é classificado como que nível de risco cardiovascular?"

Expectativa:
✅ Deve classificar como: MUITO ALTO RISCO
✅ Justificativa: albuminúria >300 mg/g é critério de muito alto risco
```

#### Teste 4.2 - Classificação por TFG
```
Query: "Paciente com TFG de 25 ml/min/1.73m² tem que nível de risco?"

Expectativa:
✅ Deve classificar como: MUITO ALTO RISCO
✅ Justificativa: TFG <30 é critério de muito alto risco
```

#### Teste 4.3 - Hipercolesterolemia Familiar
```
Query: "Hipercolesterolemia Familiar é critério de qual nível de risco cardiovascular?"

Expectativa:
✅ Deve classificar como: MUITO ALTO RISCO
```

#### Teste 4.4 - Múltiplos Fatores
```
Query: "Um paciente com 4 fatores de risco cardiovascular é classificado em que categoria?"

Expectativa:
✅ Deve classificar como: MUITO ALTO RISCO
✅ Justificativa: ≥3 fatores de risco = muito alto risco
```

---

### 5️⃣ QUERIES COMPARATIVAS

Testa capacidade de comparar e diferenciar conceitos.

#### Teste 5.1 - Diferença entre Categorias
```
Query: "Qual a diferença entre risco alto e muito alto cardiovascular?"

Expectativa:
✅ Deve listar critérios de cada categoria
✅ Deve mostrar distinção clara
```

#### Teste 5.2 - Albuminúria Moderada vs Grave
```
Query: "Qual a diferença entre albuminúria moderada e grave?"

Expectativa:
✅ Moderada: 30-300 mg/g (microalbuminúria)
✅ Grave: >300 mg/g (macroalbuminúria)
```

#### Teste 5.3 - Diabetes Tipo 1 vs Tipo 2
```
Query: "Qual a diferença entre diabetes tipo 1 e tipo 2?"

Expectativa:
✅ Deve explicar fisiopatologia (autoimune vs resistência insulínica)
✅ Pode mencionar idade de início, tratamento
```

---

### 6️⃣ RACIOCÍNIO MULTI-HOP (Complexas)

Testa capacidade de sintetizar informação de múltiplos chunks.

#### Teste 6.1 - Caso Clínico Complexo
```
Query: "Paciente com diabetes, albuminúria de 350 mg/g e TFG de 42 ml/min. Qual o risco cardiovascular e como tratar?"

Expectativa:
✅ Risco: MUITO ALTO (albuminúria >300 + TFG <45)
✅ Tratamento: controle glicêmico, IECA/BRA, possivelmente SGLT2i
⚠️ Teste CRÍTICO: requer síntese de múltiplas informações
```

#### Teste 6.2 - Comorbidades Múltiplas
```
Query: "Paciente com diabetes, hipertensão e dislipidemia. Quais as metas de tratamento?"

Expectativa:
✅ Deve mencionar metas para:
   - Glicemia/HbA1c
   - Pressão arterial
   - LDL-colesterol
⚠️ Pode exigir síntese de diferentes seções da diretriz
```

#### Teste 6.3 - Contraindicação em Contexto
```
Query: "Paciente com diabetes e TFG de 25 ml/min pode usar Metformina?"

Expectativa:
✅ NÃO (TFG <30 é contraindicação)
✅ Deve explicar risco (acidose lática)
⚠️ Requer conectar: TFG <30 + contraindicação Metformina
```

---

### 7️⃣ QUERIES NEGATIVAS (O que NÃO fazer)

Testa capacidade de identificar contraindicações e limitações.

#### Teste 7.1 - Quando NÃO usar Metformina
```
Query: "Em quais situações não devo usar Metformina?"

Expectativa:
✅ TFG <30 ml/min
✅ Insuficiência hepática grave
✅ Acidose metabólica
✅ Insuficiência cardíaca descompensada (histórico)
```

#### Teste 7.2 - Metas NÃO apropriadas
```
Query: "HbA1c de 5% é uma meta apropriada para idosos com diabetes?"

Expectativa:
✅ Provavelmente NÃO (risco de hipoglicemia)
✅ Deve mencionar individualização de metas
✅ Idosos: metas mais flexíveis (7-8% pode ser aceitável)
```

---

### 8️⃣ EDGE CASES E PERGUNTAS DIFÍCEIS

Testa limites do sistema.

#### Teste 8.1 - Informação NÃO presente
```
Query: "Qual a dose de insulina para pacientes com diabetes tipo 1?"

Expectativa:
❌ Provavelmente NÃO está na diretriz (muito específico)
✅ Sistema deve responder: "Informação não encontrada nos documentos"
✅ NÃO deve alucinar/inventar doses
```

#### Teste 8.2 - Pergunta Ambígua
```
Query: "Qual o tratamento para diabetes?"

Expectativa:
✅ Pergunta muito ampla - pode retornar overview geral
⚠️ Observar se resposta é coerente ou confusa
```

#### Teste 8.3 - Termos Técnicos vs Leigos
```
Query: "O que é TFG?"

Expectativa:
✅ Deve explicar: Taxa de Filtração Glomerular
✅ Deve mencionar função renal
```

#### Teste 8.4 - Cálculos e Fórmulas
```
Query: "Como calcular o risco cardiovascular?"

Expectativa:
✅ Pode mencionar scores (Framingham, etc.)
❌ Provavelmente não tem fórmulas detalhadas
✅ Deve mencionar critérios de estratificação
```

---

### 9️⃣ RASTREAMENTO E DIAGNÓSTICO

Testa queries sobre diagnóstico e screening.

#### Teste 9.1 - Rastreamento de Diabetes
```
Query: "Quem deve fazer rastreamento para diabetes?"

Expectativa:
✅ Idade (>45 anos)
✅ Fatores de risco (obesidade, história familiar, etc.)
✅ Frequência de rastreamento
```

#### Teste 9.2 - Diagnóstico de Nefropatia
```
Query: "Como diagnosticar nefropatia diabética?"

Expectativa:
✅ Dosagem de albuminúria
✅ Cálculo de TFG
✅ Pode mencionar exclusão de outras causas
```

#### Teste 9.3 - Rastreamento de Complicações
```
Query: "Com que frequência fazer rastreamento de retinopatia diabética?"

Expectativa:
✅ Anual (geralmente)
✅ Pode variar conforme risco e tipo de diabetes
```

---

### 🔟 PREVENÇÃO E ESTILO DE VIDA

Testa retrieval de recomendações não-farmacológicas.

#### Teste 10.1 - Prevenção Primária
```
Query: "Como prevenir diabetes tipo 2?"

Expectativa:
✅ Perda de peso
✅ Atividade física
✅ Dieta saudável
✅ Pode mencionar estudos (DPP, DPS)
```

#### Teste 10.2 - Dieta para Diabetes
```
Query: "Qual a dieta recomendada para pacientes com diabetes?"

Expectativa:
✅ Redução de carboidratos simples
✅ Aumento de fibras
✅ Controle de porções
✅ Individualização
```

#### Teste 10.3 - Atividade Física
```
Query: "Qual a recomendação de atividade física para diabéticos?"

Expectativa:
✅ 150 minutos/semana de atividade moderada (geralmente)
✅ Exercícios aeróbicos + resistência
```

---

## 📊 Planilha de Resultados

### Template de Teste

```
Teste X.Y - [Nome]
Query: "[pergunta exata]"

Resposta Recebida:
[colar resposta completa]

Análise:
✅ PASSOU / ⚠️ PARCIAL / ❌ FALHOU

Detalhes:
- Completude: [%]
- Precisão: [correta / incorreta / parcial]
- Alucinação: [sim / não]
- Citação de fonte: [sim / não]

Observações:
[comentários adicionais]
```

---

## 🎯 Critérios de Sucesso

### Metas de Accuracy

**Nível Excelente (>90%):**
- Categoria 1 (Retrieval Direto): 95-100%
- Categoria 2 (Valores Numéricos): 90-100%
- Categoria 3 (Tratamentos): 85-95%

**Nível Bom (80-90%):**
- Categoria 4 (Classificação): 85-95%
- Categoria 5 (Comparativas): 80-90%
- Categoria 9 (Rastreamento): 80-90%

**Nível Aceitável (70-80%):**
- Categoria 6 (Multi-hop): 70-85%
- Categoria 7 (Negativas): 75-85%
- Categoria 10 (Prevenção): 70-80%

**Esperado Falhar (OK <50%):**
- Categoria 8 (Edge Cases): 40-60% (informação não presente é OK)

---

## 🚨 Red Flags (Problemas Críticos)

### ❌ Falhas Inaceitáveis

1. **Alucinação de valores numéricos**
   - Inventar doses, valores de corte, metas
   - CRÍTICO: pode causar dano ao paciente

2. **Contraindicações incorretas**
   - Não mencionar contraindicações importantes
   - Mencionar contraindicações inexistentes

3. **Inversão de conceitos**
   - Confundir "alto" com "muito alto"
   - Trocar diabetes tipo 1 com tipo 2

4. **Responder quando não sabe**
   - Inventar informação não presente no documento
   - Deve dizer: "Informação não encontrada"

---

## 📈 Próximos Passos Após Testes

### Se Accuracy >85% (Geral):
✅ Sistema está robusto para produção
✅ Pode focar em: UI/UX, features adicionais, mais documentos

### Se Accuracy 70-85%:
⚠️ Identificar categorias com problemas
⚠️ Melhorar prompts, chunking, ou reranking
⚠️ Considerar ajustes finos

### Se Accuracy <70%:
❌ Revisar pipeline completo
❌ Verificar qualidade de extração (Vision API)
❌ Testar diferentes estratégias de retrieval

---

## 🔧 Como Executar os Testes

### Opção 1: Manual (Recomendado para primeiros testes)
1. Acessar /chat no Railway
2. Copiar query de cada teste
3. Colar resposta na planilha de resultados
4. Analisar e classificar (✅⚠️❌)

### Opção 2: Script Automatizado (Para testes recorrentes)
```python
# test_suite.py
import requests
import json

RAILWAY_URL = "https://your-app.railway.app"

test_queries = [
    {"id": "1.2", "query": "Quais são os critérios de risco alto cardiovascular?"},
    {"id": "2.1", "query": "Qual o valor de HbA1c para diagnóstico de diabetes?"},
    # ... todas as queries
]

for test in test_queries:
    response = requests.post(f"{RAILWAY_URL}/api/chat", json={"question": test["query"]})
    result = response.json()

    print(f"\n{'='*70}")
    print(f"Teste {test['id']}")
    print(f"Query: {test['query']}")
    print(f"Resposta: {result['response']}")
    print(f"{'='*70}")
```

---

**READY TO START TESTING!** 🚀

Escolha quais categorias quer priorizar ou comece pela Categoria 1 (Retrieval Direto).
