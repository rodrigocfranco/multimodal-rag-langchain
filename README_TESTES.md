# 🧪 Sistema de Testes para RAG Multimodal

## 📋 Arquivos Criados

### 1. **`PERGUNTAS_TESTE_STRESS.md`** (Documentação)
48 perguntas categorizadas para testar todos os aspectos do sistema:

- **Categoria 1:** Perguntas Básicas (6 perguntas) - Devem funcionar 100%
- **Categoria 2:** Negações (6 perguntas) - Testam "NÃO usar", "NÃO descarta"
- **Categoria 3:** Relações (6 perguntas) - Testam "relação entre X e Y"
- **Categoria 4:** Contextuais (6 perguntas) - Testam fluxos clínicos
- **Categoria 5:** Ambíguas (6 perguntas) - Testam premissas falsas
- **Categoria 6:** Armadilhas (6 perguntas) - Testam alucinação 🚨 CRÍTICO
- **Categoria 7:** Extremas (6 perguntas) - Testam perguntas muito longas
- **Categoria 8:** Humanas (6 perguntas) - Testam linguagem coloquial

---

### 2. **`test_stress_rag.py`** (Script Automatizado)
Script Python interativo que:

✅ Testa automaticamente as 48 perguntas
✅ Classifica respostas (sucesso_total, sucesso_parcial, falha, falha_crítica)
✅ Detecta alucinações automaticamente
✅ Gera relatório JSON com resultados
✅ Mostra estatísticas por categoria
✅ Interface colorida no terminal

**3 modos de teste:**
1. **Smoke Test:** 10 perguntas críticas (5 min) ← Comece por aqui
2. **Teste Completo:** 48 perguntas (30 min)
3. **Perguntas Originais:** 6 perguntas que falhavam antes

---

### 3. **`SOLUCOES_IMPLEMENTADAS.md`** (Documentação)
Explicação detalhada de:

- ✅ Problemas identificados (prompt restritivo, embeddings fracos, contexto insuficiente)
- ✅ Soluções implementadas (prompt melhorado, top_n=10, k=25)
- ✅ Trade-offs (custo, latência, risco)
- ✅ Como testar e validar
- ✅ Plano de rollback se necessário

---

## 🚀 Como Usar

### Passo 1: Iniciar o Servidor

```bash
# Terminal 1
python consultar_com_rerank.py --api

# Aguarde ver:
# 🌐 API COM RERANKER rodando em http://localhost:5001
```

---

### Passo 2: Executar Smoke Test (RECOMENDADO)

```bash
# Terminal 2
python test_stress_rag.py

# Escolha opção: 1 (Smoke Test)
```

**O que acontece:**
```
🧪 SMOKE TEST - 10 perguntas críticas
==================================================

Testando Q1/10... OK
✅ Q1 [basicas]
   Pergunta: Qual o valor de TFG que define insuficiência renal crônica?...
   Status: SUCESSO_TOTAL - Resposta substantiva com fontes
   Resposta: O valor de TFG que define insuficiência renal crônica é...

Testando Q2/10... OK
⚠️  Q2 [negacoes]
   Pergunta: Quando NÃO usar metformina?...
   Status: SUCESSO_PARCIAL - Resposta sem citação completa
   Resposta: A metformina não deve ser usada quando...

...

📊 RESUMO DO SMOKE TEST
==================================================
  ✅ Sucesso Total:   7/10
  ⚠️  Sucesso Parcial: 2/10
  ❌ Falhas:          1/10
  🚨 Falhas Críticas: 0/10

  Taxa de Sucesso: 90.0%

  🎉 META ATINGIDA! (≥80%)

💾 Resultados salvos em: smoke_test_20251017_143522.json
```

---

### Passo 3: Analisar Resultados

**Arquivo JSON gerado:**
```json
{
  "timestamp": "2025-10-17T14:35:22",
  "summary": {
    "sucesso_total": 7,
    "sucesso_parcial": 2,
    "falha": 1,
    "falha_critica": 0
  },
  "details": [
    {
      "qnum": 1,
      "category": "basicas",
      "question": "Qual o valor de TFG...",
      "status": "sucesso_total",
      "response": {
        "answer": "...",
        "sources": ["diretriz.pdf"]
      }
    }
  ]
}
```

---

### Passo 4: Teste Completo (Se Smoke Test Passou)

```bash
python test_stress_rag.py

# Escolha opção: 2 (Teste Completo)
# Aguarde ~30 minutos
```

**Resultados esperados:**

| Categoria | Meta | Expectativa |
|-----------|------|-------------|
| Básicas | 100% | 6/6 ✅ |
| Negações | 67% | 4/6 ⚠️ |
| Relações | 83% | 5/6 ✅ |
| Contextuais | 67% | 4/6 ⚠️ |
| Ambíguas | 50% | 3/6 ⚠️ |
| **Armadilhas** | **100%** | **6/6 ✅ CRÍTICO** |
| Extremas | 33% | 2/6 (edge cases) |
| Humanas | 83% | 5/6 ✅ |
| **TOTAL** | **≥73%** | **35-40/48** |

---

## 🎯 Critérios de Sucesso

### ✅ Sucesso Total
- Resposta correta e completa
- Cita fontes apropriadas
- Formatação adequada

### ⚠️ Sucesso Parcial
- Resposta incompleta mas correta
- Falta alguma citação
- Formatação imperfeita

### ❌ Falha
- Resposta incorreta
- "Informação não presente" quando ESTÁ presente
- Resposta muito vaga

### 🚨 Falha Crítica (BUG GRAVE!)
- **Alucinação em pergunta armadilha** (Categoria 6)
- Responde com confiança sobre informação ausente
- Contradiz informação do documento
- Não corrige premissa falsa do usuário

---

## 📊 Metas de Validação

### 🔴 CRÍTICO (Devem passar 100%)
- ✅ Categoria 1: Perguntas básicas
- ✅ Categoria 6: Armadilhas de alucinação (6/6)
- ✅ Zero falhas críticas

### 🟡 IMPORTANTE (≥ 80%)
- ✅ Categoria 3: Relações e conexões
- ✅ Categoria 8: Linguagem humana
- ✅ Smoke Test: 8/10

### 🟢 DESEJÁVEL (≥ 60%)
- ⚠️ Categoria 2: Negações
- ⚠️ Categoria 4: Casos clínicos
- ⚠️ Categoria 5: Perguntas ambíguas

---

## 🔍 Interpretando Resultados

### Cenário 1: Smoke Test Passou (8-10/10)
✅ **Sistema está funcionando bem!**
- Próximo passo: Executar teste completo
- Expectativa: 73-85% de sucesso geral

### Cenário 2: Smoke Test Parcial (5-7/10)
⚠️ **Sistema funciona mas tem limitações**
- Analisar quais categorias falharam
- Se Categoria 6 (armadilhas) falhou → 🚨 PROBLEMA CRÍTICO
- Considerar ajustes no prompt ou retriever

### Cenário 3: Smoke Test Falhou (<5/10)
❌ **Sistema precisa de ajustes significativos**
- Revisar configuração do retriever (k, top_n)
- Revisar prompt de inferência
- Verificar se documentos foram processados corretamente
- Consultar `SOLUCOES_IMPLEMENTADAS.md` para rollback

---

## 🐛 Troubleshooting

### Erro: "Servidor não está rodando"
```bash
# Iniciar servidor primeiro
python consultar_com_rerank.py --api

# Verificar se porta 5001 está livre
lsof -i :5001
```

### Erro: "Timeout após 30s"
```bash
# Aumentar timeout no script
# Editar test_stress_rag.py linha 9:
TIMEOUT = 60  # segundos (era 30)
```

### Erro: "Módulo requests não encontrado"
```bash
pip install requests
```

### Todas respostas dizem "informação não presente"
🚨 **Problema:** Knowledge base pode estar vazio

```bash
# Verificar se há documentos
python -c "
import os, pickle
if os.path.exists('./knowledge_base/metadata.pkl'):
    with open('./knowledge_base/metadata.pkl', 'rb') as f:
        m = pickle.load(f)
    print(f'Documentos: {len(m.get(\"documents\", {}))}')
else:
    print('Knowledge base vazio! Processe PDFs primeiro.')
"

# Se vazio, processar PDF:
python adicionar_pdf.py "caminho/para/documento.pdf"
```

---

## 📈 Melhorias Implementadas

### Antes das Melhorias (Original)
- ❌ Taxa de sucesso: **50% (3/6 perguntas)**
- ❌ Prompt proibia inferências lógicas
- ❌ top_n = 5 (contexto insuficiente)
- ❌ k = 20 (poucas opções para reranking)

### Depois das Melhorias (Atual)
- ✅ Taxa esperada: **83-100% (5-6/6 perguntas)**
- ✅ Prompt permite inferências guiadas e documentadas
- ✅ top_n = 10 (+100% vs original, +25% contexto)
- ✅ k = 25 (+25% diversidade)

**Arquivo:** `consultar_com_rerank.py` (modificado)

---

## 🔄 Próximos Passos Após Testes

### Se Taxa de Sucesso ≥ 80%
✅ **Sistema pronto para produção!**
- Deploy no Railway
- Monitorar métricas em produção
- Coletar feedback de usuários reais

### Se Taxa de Sucesso 60-79%
⚠️ **Sistema funcional mas pode melhorar**
- Implementar Query Expansion (reformular perguntas)
- Considerar Hybrid Search (BM25 + embeddings)
- Ajustar chunking (chunks maiores, overlap maior)

### Se Taxa de Sucesso < 60%
❌ **Sistema precisa de revisão**
- Revisar configuração do retriever
- Testar outros modelos de embedding
- Considerar re-processar documentos
- Consultar documentação avançada

---

## 📚 Documentação Relacionada

- **`PERGUNTAS_TESTE_STRESS.md`** - Banco de 48 perguntas detalhadas
- **`SOLUCOES_IMPLEMENTADAS.md`** - Análise técnica das melhorias
- **`ANALISE_TESTES_E_SOLUCOES.md`** - Análise original dos problemas
- **`GUIA_RAPIDO.md`** - Guia geral do sistema

---

## 🎓 Exemplos de Perguntas para Testar Manualmente

### Perguntas Fáceis (Devem funcionar 100%)
```
Q: Qual o alvo de HbA1c recomendado?
Q: Liste as contraindicações da metformina
Q: Quais são os iSGLT2 mencionados no documento?
```

### Perguntas Médias (Testam inferência)
```
Q: Qual a relação entre albuminúria e risco cardiovascular?
Q: Quando NÃO usar insulina como primeira linha?
Q: Como a obesidade influencia a escolha do antidiabético?
```

### Perguntas Difíceis (Testam limites)
```
Q: Paciente com DM2, obesidade e HbA1c 8,5%. Qual terapia inicial?
Q: Compare iSGLT2 vs GLP-1 em pacientes com DRC
Q: Existem situações onde HbA1c normal NÃO exclui diabetes?
```

### Perguntas Armadilha (DEVEM rejeitar)
```
Q: Qual o custo do tratamento com iSGLT2 no Brasil?
Q: Quantos pacientes no estudo UKPDS? (se não está no doc)
Q: O que a diretriz europeia recomenda? (se só tem brasileira)
```

---

**Pronto para testar!** 🧪

Execute: `python test_stress_rag.py`
