# 🔍 ANÁLISE CRÍTICA: Pipeline de Processamento de PDFs

## ❌ PROBLEMAS IDENTIFICADOS

### 1. **TABELAS QUEBRADAS PELO CHUNKING** (CRÍTICO)
**Arquivo:** `adicionar_pdf.py` linhas 86-90

```python
chunking_strategy="by_title",
max_characters=10000,
combine_text_under_n_chars=2000,
new_after_n_chars=6000,
```

**Problema:**
- `chunking_strategy="by_title"` pode quebrar tabelas no meio
- Se uma tabela tem múltiplas seções (Low, Intermediate, Alto, Muito Alto), cada seção pode virar um chunk separado
- Isso explica por que encontramos apenas "Low Intermediate" na tabela extraída

**Evidência:**
- `/search-table` retornou apenas 1 tabela com conteúdo parcial em inglês
- Keywords "3 ou mais fatores" e "Hipercolesterolemia Familiar" não existem em nenhum chunk
- Tabela foi processada como tipo "table" mas conteúdo incompleto

**Impacto:** ⭐⭐⭐⭐⭐ CRÍTICO
- Respostas incompletas para perguntas sobre critérios de risco
- Informação crítica perdida permanentemente


### 2. **OCR SEM CONFIGURAÇÃO DE IDIOMA**
**Arquivo:** `adicionar_pdf.py` linha 80-84

```python
return partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy=strategy,
    # ❌ FALTA: languages=["por"]
```

**Problema:**
- Unstructured usa Tesseract OCR por padrão
- Sem `languages=["por"]`, o OCR detecta automaticamente o idioma
- Tabelas com formatação complexa podem ser mal interpretadas como inglês

**Evidência:**
- Tabela extraída tem conteúdo em inglês: "Low Intermediate"
- Texto original está em português

**Impacto:** ⭐⭐⭐⭐ ALTO
- OCR impreciso reduz qualidade do retrieval
- Embeddings de texto em inglês não casam com queries em português


### 3. **RESUMOS PERDEM INFORMAÇÃO DETALHADA** (CRÍTICO)
**Arquivo:** `adicionar_pdf.py` linhas 345-377

```python
# Gerar resumos com GPT-4o-mini
summarize = {"element": lambda x: x} | prompt | model | StrOutputParser()

# PROBLEMA: Resumo é armazenado no vectorstore, texto original no docstore
```

**Problema:**
- **Busca é feita APENAS nos resumos** (vectorstore)
- Resumos podem omitir detalhes específicos como "3 ou mais fatores de risco"
- GPT-4o-mini com prompt "Summarize concisely" pode generalizar demais

**Exemplo do que pode acontecer:**
```
Texto original: "MUITO ALTO: Hipercolesterolemia Familiar, 3 ou mais fatores de risco, albuminúria >300mg/g..."

Resumo gerado: "Critérios de classificação de risco cardiovascular incluem fatores como hipercolesterolemia, albuminúria e função renal"

❌ PERDEU: "3 ou mais fatores", "Hipercolesterolemia Familiar", valores específicos
```

**Impacto:** ⭐⭐⭐⭐⭐ CRÍTICO
- Keywords específicos não aparecem nos embeddings
- Queries específicas não encontram documentos relevantes
- Cohere reranker não consegue compensar se o doc não está nos top 30


### 4. **FILTRO DE IMAGENS PODE REMOVER TABELAS**
**Arquivo:** `adicionar_pdf.py` linhas 278, 286-297

```python
MIN_IMAGE_SIZE_KB = float(os.getenv("MIN_IMAGE_SIZE_KB", "5"))

# Filtrar imagens pequenas
if size_kb >= MIN_IMAGE_SIZE_KB:
    # ... adicionar
else:
    filtered_count += 1
```

**Problema:**
- Tabelas extraídas como imagens podem ter <5KB se forem simples
- Tabelas compactas (poucas linhas) podem ser descartadas
- TABELA 1 de risco cardiovascular pode ser compacta

**Impacto:** ⭐⭐⭐ MÉDIO
- Tabelas importantes podem ser removidas silenciosamente
- Sem warning no log


### 5. **ESTRATÉGIA `hi_res` vs `fast`**
**Arquivo:** `adicionar_pdf.py` linhas 76-101

```python
strategy_env = os.getenv("UNSTRUCTURED_STRATEGY", "hi_res").strip().lower()

try:
    chunks = run_partition(strategy_env)
except Exception as e:
    # Fallback para 'fast'
    if "libGL.so.1" in str(e):
        chunks = run_partition("fast")
```

**Problema:**
- `hi_res`: Melhor OCR, mas pode falhar em ambiente Railway (sem libGL)
- `fast`: Mais rápido, mas OCR inferior, não detecta tabelas complexas bem
- Railway provavelmente usa `fast` por falta de libGL

**Evidência:**
- Log de upload não mostra qual estratégia foi usada
- Tabela em inglês sugere OCR ruim

**Impacto:** ⭐⭐⭐⭐ ALTO
- Qualidade de extração muito inferior com `fast`
- Usuário não sabe qual estratégia foi usada


### 6. **CHUNKING AGRESSIVO DEMAIS**
**Arquivo:** `adicionar_pdf.py` linha 89

```python
new_after_n_chars=6000,  # Força quebra a cada 6000 chars
```

**Problema:**
- Força quebra a cada 6000 caracteres
- Tabelas longas ou seções médicas detalhadas são quebradas
- Contexto é perdido entre chunks

**Impacto:** ⭐⭐⭐ MÉDIO
- Informações relacionadas ficam em chunks separados
- LLM precisa conectar múltiplos chunks (nem sempre funciona)


### 7. **SEPARAÇÃO DE ELEMENTOS INCOMPLETA**
**Arquivo:** `adicionar_pdf.py` linhas 108-121

```python
for chunk in chunks:
    chunk_type = str(type(chunk).__name__)

    if "Table" in chunk_type and chunk not in tables:
        tables.append(chunk)
    elif chunk_type in ['CompositeElement', 'NarrativeText', 'Title', 'Text', 'ListItem']:
        texts.append(chunk)
```

**Problema:**
- Lista manual de tipos pode perder novos elementos da Unstructured
- Elementos não classificados são ignorados silenciosamente
- Não há log de elementos descartados

**Impacto:** ⭐⭐ BAIXO
- Alguns elementos podem ser perdidos sem aviso


### 8. **SEM VALIDAÇÃO DE QUALIDADE PÓS-PROCESSAMENTO**

**Problema:**
- Não há verificação se tabelas críticas foram extraídas
- Não há comparação de # de páginas vs # de chunks
- Não há detecção de OCR falho (muito texto em inglês em PDF português)

**Impacto:** ⭐⭐⭐ MÉDIO
- Problemas só são detectados quando usuário pergunta


## ✅ SOLUÇÕES PROPOSTAS

### SOLUÇÃO 1: Desabilitar chunking para preservar tabelas completas

```python
# ANTES (adicionar_pdf.py linha 86):
chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy=strategy,
    extract_image_block_types=["Image", "Table"],
    extract_image_block_to_payload=True,
    chunking_strategy="by_title",  # ❌ QUEBRA TABELAS
    max_characters=10000,
    combine_text_under_n_chars=2000,
    new_after_n_chars=6000,
)

# DEPOIS:
chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy=strategy,
    extract_image_block_types=["Image", "Table"],
    extract_image_block_to_payload=True,
    languages=["por"],  # ✅ FORÇA PORTUGUÊS
    # ✅ REMOVER chunking automático - fazer manual depois
)
```

**Benefícios:**
- Tabelas preservadas inteiras
- OCR em português correto
- Controle total sobre chunking

**Trade-off:**
- Chunks maiores → mais tokens no contexto
- Solução: fazer chunking manual APÓS separar tabelas


### SOLUÇÃO 2: Armazenar texto original + resumo nos embeddings

```python
# ANTES: Só resumo no vectorstore
doc = Document(
    page_content=summary,  # ❌ SÓ RESUMO
    metadata={"doc_id": doc_id, ...}
)

# DEPOIS: Texto original + resumo
doc = Document(
    page_content=f"{summary}\n\n---ORIGINAL---\n{original_text}",  # ✅ AMBOS
    metadata={"doc_id": doc_id, "summary": summary, ...}
)
```

**Benefícios:**
- Keywords específicos aparecem nos embeddings
- Retrieval encontra texto mesmo se resumo omitiu
- Cohere rerank vê texto completo

**Trade-off:**
- Embeddings maiores (mais custo)
- Solução: aceitar custo para melhor qualidade


### SOLUÇÃO 3: Estratégia híbrida para tabelas

```python
# Processar tabelas separadamente sem resumo
for table in tables:
    # Armazenar tabela COMPLETA sem resumir
    doc = Document(
        page_content=table.text,  # ✅ TEXTO COMPLETO
        metadata={"doc_id": doc_id, "type": "table", ...}
    )

    # Também adicionar imagem da tabela
    if hasattr(table.metadata, 'image_base64'):
        # Armazenar imagem também
        ...
```

**Benefícios:**
- Tabelas preservadas 100%
- Retrieval encontra keywords específicos
- Multimodal: texto + imagem da tabela

**Trade-off:**
- Mais chunks (41 → ~60)
- Solução: aumentar `k` no retrieval


### SOLUÇÃO 4: Logging detalhado do processamento

```python
# Adicionar ao final do processamento:
print("\n📊 RELATÓRIO DE QUALIDADE:")
print(f"   Estratégia OCR: {strategy_used}")
print(f"   Páginas no PDF: {num_pages}")
print(f"   Chunks gerados: {len(chunk_ids)}")
print(f"   Tabelas encontradas: {len(tables)}")

# Listar tabelas extraídas
for i, table in enumerate(tables):
    preview = table.text[:100] if hasattr(table, 'text') else str(table)[:100]
    print(f"   Tabela {i+1}: {preview}...")

# Detectar OCR ruim (muito inglês em PDF português)
all_text = " ".join([t.text for t in texts if hasattr(t, 'text')])
english_words = len([w for w in all_text.split() if w.lower() in ['the', 'and', 'or', 'with']])
total_words = len(all_text.split())
if english_words / total_words > 0.1:
    print(f"   ⚠️  AVISO: {english_words/total_words*100:.1f}% de palavras em inglês detectadas")
    print(f"      PDF pode ter sido mal processado. Considere reprocessar com OCR otimizado.")
```


### SOLUÇÃO 5: Validação pós-processamento

```python
# Verificar se keywords críticos foram capturados
def validate_extraction(texts, tables, critical_keywords):
    """Verifica se keywords críticos foram extraídos"""
    all_content = " ".join([
        t.text.lower() for t in texts if hasattr(t, 'text')
    ] + [
        t.text.lower() for t in tables if hasattr(t, 'text')
    ])

    missing = []
    for keyword in critical_keywords:
        if keyword.lower() not in all_content:
            missing.append(keyword)

    if missing:
        print(f"\n   ⚠️  KEYWORDS AUSENTES: {missing}")
        print(f"      Processamento pode estar incompleto")

    return len(missing) == 0

# Para PDFs de diabetes, verificar:
if 'diabetes' in pdf_filename.lower():
    validate_extraction(texts, tables, [
        "hipercolesterolemia familiar",
        "muito alto",
        "albuminúria",
        "TFG"
    ])
```


## 🎯 PRIORIZAÇÃO DAS SOLUÇÕES

| Solução | Impacto | Esforço | Prioridade |
|---------|---------|---------|------------|
| 1. Desabilitar chunking automático | ⭐⭐⭐⭐⭐ | Baixo | **P0 - CRÍTICO** |
| 2. Texto original + resumo | ⭐⭐⭐⭐⭐ | Médio | **P0 - CRÍTICO** |
| 3. Estratégia híbrida tabelas | ⭐⭐⭐⭐ | Médio | **P1 - ALTO** |
| 4. Logging detalhado | ⭐⭐⭐ | Baixo | **P1 - ALTO** |
| 5. Validação pós-processamento | ⭐⭐⭐ | Médio | **P2 - MÉDIO** |


## 📋 PLANO DE IMPLEMENTAÇÃO

### Fase 1: Correções Críticas (30 min)
1. ✅ Remover `chunking_strategy="by_title"`
2. ✅ Adicionar `languages=["por"]`
3. ✅ Armazenar texto original + resumo nos embeddings

### Fase 2: Melhorias Tabelas (20 min)
4. ✅ Processar tabelas sem resumo (texto completo)
5. ✅ Logging de tabelas extraídas

### Fase 3: Validação (10 min)
6. ✅ Adicionar relatório de qualidade
7. ✅ Validação de keywords críticos


## 🔍 TESTE APÓS IMPLEMENTAÇÃO

1. Reprocessar PDF de diabetes
2. Verificar `/search-table` retorna `has_tabela_1: true`
3. Fazer query: "Quais são todos os critérios de muito alto risco cardiovascular?"
4. Verificar resposta inclui:
   - ✅ Hipercolesterolemia Familiar
   - ✅ 3 ou mais fatores de risco
   - ✅ Albuminúria >300
   - ✅ TFG <30
   - ✅ Todos outros critérios da TABELA 1
