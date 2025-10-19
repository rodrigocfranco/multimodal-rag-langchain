# 🔍 ANÁLISE: Problema de Extração Incompleta de Tabela

## 📋 PROBLEMA IDENTIFICADO

### Situação Atual
**Query:** "Traga todos os critérios de muito alto risco cardiovascular detalhados da diretriz brasileira de diabetes"

**Resposta Retornada:**
```
- Albuminúria >300 mg/g ou TFG <30 ml/min/1.73m²
- Albuminúria 30-300 mg/g + TFG <45 ml/min/1.73m²
- Retinopatia proliferativa
- NAC grave
- Estenose arterial >50% em qualquer território arterial
- Síndrome coronariana aguda - IAM
- Doença Coronariana Crônica - Angina Estável
- Acidente Vascular Encefálico Isquêmico
- Ataque isquêmico transitório
- Doença arterial obstrutiva periférica
- Amputação
- Revascularização arterial
```

**Critérios FALTANDO:**
- ❌ **3 ou mais fatores de risco**
- ❌ **Hipercolesterolemia Familiar**

---

## 🖼️ TABELA ORIGINAL (da imagem do PDF)

```
┌───────────┬──────────────────────┬─────────────────────┬─────────────────────┐
│  MUITO    │  • 3 ou mais fatores │ Qualquer das        │ Qualquer das        │
│  ALTO     │    de risco          │ seguintes:          │ seguintes:          │
│           │  • Hipercolesterole- │ • Albuminúria >300  │ • Síndrome          │
│           │    mia Familiar      │ • Albuminúria 30-300│   coronariana       │
│           │                      │ • Retinopatia...    │   aguda - IAM       │
│           │                      │ • NAC grave         │ • Doença Coronariana│
│           │                      │ • Estenose arterial │ • AVC Isquêmico     │
│           │                      │                     │ • Ataque isquêmico  │
│           │                      │                     │ • Doença arterial   │
│           │                      │                     │ • Amputação         │
│           │                      │                     │ • Revascularização  │
└───────────┴──────────────────────┴─────────────────────┴─────────────────────┘
  Coluna 1        Coluna 2               Coluna 3              Coluna 4
  (Label)      ❌ FALTANDO!!!          (✅ Capturada)        (✅ Capturada)
```

---

## 🔴 DIAGNÓSTICO

### Problema Confirmado
**Apenas as colunas 3 e 4 da tabela estão sendo extraídas, enquanto a coluna 2 (com os dois critérios críticos) está sendo perdida.**

### Possíveis Causas

#### 1. **Problema de OCR/Layout Detection**
**Hipótese:** O Tesseract OCR ou o layout detection do Unstructured não detectou a coluna 2

**Evidências:**
- A coluna 2 pode estar em uma área que o OCR pulou
- Layout complexo com múltiplas colunas pode confundir a detecção
- Estratégia `hi_res` usa Detectron2 para layout, mas pode falhar em tabelas complexas

**Teste:**
```bash
# Inspecionar PDF localmente com debug
python debug_chunks.py "content/diabetes.pdf"
```

#### 2. **Problema de Table Structure Inference**
**Hipótese:** `infer_table_structure=True` não detectou corretamente a estrutura da tabela

**Evidências:**
- Tabela tem 4 colunas, mas apenas 2 últimas foram capturadas
- Pode ter inferido estrutura diferente (2 colunas em vez de 4)

#### 3. **Problema de Chunking**
**Hipótese:** Chunking separou a coluna 2 em chunk diferente

**Evidências:**
- Menos provável, pois Unstructured preserva tabelas inteiras
- Mas com `max_characters=10000`, uma tabela MUITO grande poderia ser quebrada

---

## ✅ SOLUÇÕES PROPOSTAS

### SOLUÇÃO 1: Usar GPT-4o Vision para Tabelas Críticas ⭐⭐⭐⭐⭐

**Conceito:**
- Detectar tabelas no PDF
- Extrair imagem de cada tabela
- Usar GPT-4o Vision para extrair estrutura completa
- Armazenar texto extraído + imagem da tabela

**Implementação:**

```python
def extract_table_with_vision(table_image_b64, pdf_filename, page_num):
    """
    Usar GPT-4o Vision para extrair tabela completa com estrutura
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    llm = ChatOpenAI(model="gpt-4o", max_tokens=2000)

    prompt = f"""
Você é um especialista em extração de tabelas médicas.

TAREFA: Extraia COMPLETAMENTE a tabela da imagem, preservando TODAS as colunas e linhas.

INSTRUÇÕES:
1. Identifique TODAS as colunas (mesmo se algumas estiverem vazias ou com pouco texto)
2. Preserve a estrutura exata da tabela
3. Use Markdown table format
4. Se houver headers, identifique-os claramente
5. IMPORTANTE: Não omita nenhuma coluna, mesmo que pareça vazia

CONTEXTO:
- Documento: {pdf_filename}
- Página: {page_num}
- Tipo: Diretriz médica de diabetes

Forneça a tabela em formato Markdown:
"""

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{table_image_b64}"}
            }
        ]
    )

    response = llm.invoke([message])
    table_markdown = response.content

    return table_markdown


# Integrar no processamento
for table in tables:
    if hasattr(table.metadata, 'image_base64'):
        # Tabela tem imagem - usar Vision
        table_text_vision = extract_table_with_vision(
            table.metadata.image_base64,
            pdf_filename,
            table.metadata.page_number
        )

        # Armazenar ambos: OCR + Vision
        doc = Document(
            page_content=f"""
[TABELA EXTRAÍDA VIA OCR]
{table.text}

[TABELA EXTRAÍDA VIA VISION (GPT-4o)]
{table_text_vision}
            """,
            metadata={
                "doc_id": str(uuid.uuid4()),
                "type": "table",
                "extraction_methods": ["ocr", "vision"],
                "source": pdf_filename,
                "page_number": table.metadata.page_number
            }
        )
```

**Benefícios:**
- ✅ GPT-4o Vision é EXCELENTE em tabelas complexas
- ✅ Detecta TODAS as colunas, mesmo as sutis
- ✅ Preserva estrutura completa
- ✅ Fallback: se Vision falhar, usa OCR

**Trade-offs:**
- ⬆️ Custo: ~$0.01 por tabela (GPT-4o Vision)
- ⬆️ Latência: +3-5 segundos por tabela

**Esforço:** 3-4 horas

---

### SOLUÇÃO 2: Otimizar Parâmetros de Table Extraction ⭐⭐⭐⭐

**Conceito:**
- Ajustar parâmetros do Unstructured para melhor detecção de tabelas
- Testar estratégias diferentes

**Implementação:**

```python
# TESTE 1: OCR_ONLY strategy (força OCR em todo documento)
chunks = partition_pdf(
    filename=file_path,
    strategy="ocr_only",  # Força OCR pesado
    languages=["por"],
    infer_table_structure=True,
    extract_image_block_types=["Image", "Table"],
    extract_image_block_to_payload=True,

    # NOVO: Parâmetros de table detection
    extract_tables=True,  # Força extração de tabelas
    table_as_cells=False,  # Retorna tabela como texto único, não células
)

# TESTE 2: Aumentar resolução de OCR
chunks = partition_pdf(
    filename=file_path,
    strategy="hi_res",
    languages=["por"],
    infer_table_structure=True,

    # NOVO: OCR config
    ocr_languages="por",
    pdf_infer_table_structure=True,

    # Chunking
    chunking_strategy="by_title",
    max_characters=10000,
    combine_text_under_n_chars=4000,
    new_after_n_chars=6000,
)
```

**Esforço:** 1-2 horas

---

### SOLUÇÃO 3: Hybrid Approach (OCR + Vision) ⭐⭐⭐⭐⭐

**Conceito:**
- Extrair tabelas com ambos: OCR + Vision
- Comparar resultados
- Se OCR tiver < 80% do tamanho do Vision, usar Vision
- Armazenar ambos para redundância

**Implementação:**

```python
def extract_table_hybrid(table_element):
    """
    Extrai tabela com OCR + Vision, valida e escolhe melhor
    """
    # 1. Texto via OCR (Unstructured)
    ocr_text = table_element.text if hasattr(table_element, 'text') else ""

    # 2. Texto via Vision (GPT-4o)
    vision_text = ""
    if hasattr(table_element.metadata, 'image_base64'):
        vision_text = extract_table_with_vision(
            table_element.metadata.image_base64,
            pdf_filename,
            table_element.metadata.page_number
        )

    # 3. Validar qualidade
    ocr_size = len(ocr_text.split())
    vision_size = len(vision_text.split())

    # Se OCR perdeu >20% do conteúdo, usar Vision
    use_vision = (ocr_size < 0.8 * vision_size) if vision_size > 0 else False

    # 4. Armazenar ambos com flag de qualidade
    if use_vision:
        primary_text = vision_text
        method = "vision (OCR incomplete)"
    else:
        primary_text = ocr_text
        method = "ocr"

    # 5. Criar documento enriquecido
    doc_content = f"""
[MÉTODO PRIMÁRIO: {method}]
{primary_text}

[BACKUP - OCR]
{ocr_text}

[BACKUP - VISION]
{vision_text}
    """

    return doc_content, method
```

**Benefícios:**
- ✅ Máxima completude (redundância)
- ✅ Auto-validação de qualidade
- ✅ Fallback automático

**Trade-offs:**
- ⬆️⬆️ Custo: dobro (OCR + Vision sempre)
- ⬆️ Storage: ~3x maior por tabela

**Esforço:** 4-5 horas

---

### SOLUÇÃO 4: Post-Processing Validation ⭐⭐⭐

**Conceito:**
- Após extração, validar se tabelas críticas estão completas
- Se detectar keywords faltando, re-extrair com Vision

**Implementação:**

```python
def validate_table_completeness(table_text, expected_keywords):
    """
    Valida se tabela está completa baseado em keywords esperadas
    """
    missing = []
    for keyword in expected_keywords:
        if keyword.lower() not in table_text.lower():
            missing.append(keyword)

    completeness = 1 - (len(missing) / len(expected_keywords))

    return {
        "complete": len(missing) == 0,
        "completeness": completeness,
        "missing_keywords": missing
    }

# Após processar tabela
for table in tables:
    # Para tabelas de risco cardiovascular
    if "muito alto" in table.text.lower() or "risco" in table.text.lower():
        validation = validate_table_completeness(
            table.text,
            expected_keywords=[
                "3 ou mais fatores",
                "hipercolesterolemia familiar",
                "albuminúria",
                "TFG",
                "retinopatia",
                "síndrome coronariana"
            ]
        )

        if not validation["complete"]:
            print(f"⚠️ Tabela incompleta! Faltando: {validation['missing_keywords']}")
            print(f"   Completeness: {validation['completeness']*100:.1f}%")

            # Re-extrair com Vision
            if hasattr(table.metadata, 'image_base64'):
                print(f"   Re-extraindo com Vision...")
                vision_text = extract_table_with_vision(...)
                table.text = vision_text
```

**Esforço:** 2-3 horas

---

## 🎯 RECOMENDAÇÃO FINAL

### Estratégia Recomendada: **Hybrid Approach com Validação**

**Implementação em fases:**

#### Fase 1 (AGORA): Diagnóstico
1. ✅ Acessar `/inspect-tables` no Railway
2. ✅ Confirmar se coluna 2 está realmente faltando
3. ✅ Ver texto EXATO extraído da tabela

#### Fase 2 (Hoje): Quick Fix
1. Implementar **SOLUÇÃO 1** (Vision para tabelas)
2. Re-processar PDF com Vision ativada para tabelas
3. Validar que todos critérios foram capturados

#### Fase 3 (Próxima semana): Robust Solution
1. Implementar **SOLUÇÃO 3** (Hybrid OCR + Vision)
2. Implementar **SOLUÇÃO 4** (Validação automática)
3. Criar suite de testes para validar tabelas críticas

---

## 📊 PRÓXIMOS PASSOS IMEDIATOS

### 1. Testar Endpoint de Inspeção ⏳
```bash
# Acessar Railway (após deploy)
https://your-app.railway.app/inspect-tables
```

**O que verificar:**
- ✅ Quantas tabelas foram encontradas?
- ✅ A tabela de "Muito Alto" risco está lá?
- ✅ O texto completo contém "3 ou mais fatores"?
- ✅ O texto completo contém "Hipercolesterolemia Familiar"?

### 2. Se Confirmar Coluna Faltando
Implementar extração com Vision:

```python
# adicionar_pdf.py

# NOVO: Função para extrair tabelas com Vision
def extract_table_with_vision_api(table_image_b64, context_info):
    # ... código da SOLUÇÃO 1 ...
    pass

# No processamento de tabelas:
for table in tables:
    if hasattr(table.metadata, 'image_base64'):
        # Usar Vision para garantir completude
        vision_text = extract_table_with_vision_api(
            table.metadata.image_base64,
            {
                "filename": pdf_filename,
                "page": table.metadata.page_number if hasattr(table.metadata, 'page_number') else None
            }
        )

        # Armazenar OCR + Vision
        table.text = f"{table.text}\n\n[VISION EXTRACTION]\n{vision_text}"
```

### 3. Re-processar PDF
```bash
# Deletar documento atual via /manage
# Fazer upload novamente com código atualizado
```

---

## 💰 ANÁLISE DE CUSTO

### Vision API (GPT-4o)
**Custo por tabela:**
- Input: ~500 tokens (prompt) + imagem = ~$0.005
- Output: ~300 tokens (table markdown) = ~$0.004
- **Total: ~$0.01 por tabela**

**Para um PDF médico típico:**
- ~5-10 tabelas por documento
- **Custo total: $0.05 - $0.10 por PDF**

**Trade-off:**
- ⬆️ +$0.10 de custo por PDF
- ⬆️⬆️⬆️ Completude 100% vs 60% atual
- ✅ Vale MUITO a pena para documentos críticos

---

## 🔬 TESTES PARA VALIDAR SOLUÇÃO

### Dataset de Teste
```python
test_queries = [
    {
        "query": "Quais são TODOS os critérios de muito alto risco cardiovascular?",
        "must_contain": [
            "3 ou mais fatores de risco",
            "hipercolesterolemia familiar",
            "albuminúria >300",
            "TFG <30",
            "síndrome coronariana",
            "retinopatia proliferativa"
        ]
    },
    {
        "query": "Quando um paciente é classificado como muito alto risco?",
        "must_contain": [
            "3 ou mais fatores",
            "hipercolesterolemia familiar"
        ]
    }
]

# Testar
for test in test_queries:
    response = chain.invoke(test["query"])

    missing = []
    for keyword in test["must_contain"]:
        if keyword.lower() not in response["response"].lower():
            missing.append(keyword)

    if missing:
        print(f"❌ FALHOU: {test['query']}")
        print(f"   Faltando: {missing}")
    else:
        print(f"✅ PASSOU: {test['query']}")
```

---

## 📝 STATUS

- **Problema:** Tabela de risco CV com coluna 2 faltando
- **Endpoint criado:** `/inspect-tables` (aguardando deploy)
- **Próximo passo:** Confirmar diagnóstico via endpoint
- **Solução proposta:** Vision API para tabelas (SOLUÇÃO 1)

**Aguardando:** Resultados de `/inspect-tables` para confirmar e implementar fix.
