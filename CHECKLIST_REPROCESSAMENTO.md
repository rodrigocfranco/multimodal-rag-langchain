# ✅ CHECKLIST: Preparação para Reprocessamento de PDFs

## 🎯 Objetivo
Reprocessar o documento "Manejo de hiperglicemia hospitalar em pacientes não-críticos" para extrair e armazenar imagens.

---

## ✅ VERIFICAÇÕES CONCLUÍDAS

### 1. ✅ Função `get_images_base64()` (linhas 381-458)

**Status:** ✅ PERFEITO

**Verificações:**
- ✅ Extrai imagens de elementos Image diretos
- ✅ Extrai imagens de CompositeElement.metadata.orig_elements
- ✅ Converte TODAS imagens para JPEG (GPT-4o Vision suporta)
- ✅ Filtro de tamanho: MIN_IMAGE_SIZE_KB = 30KB (remove ícones)
- ✅ Deduplicação por hash (evita imagens repetidas)
- ✅ Retorna: (images_b64, filtered_count, total_found)

**Código-chave:**
```python
MIN_IMAGE_SIZE_KB = float(os.getenv("MIN_IMAGE_SIZE_KB", "30"))

# Conversão para JPEG
jpeg_img, success = convert_image_to_jpeg_base64(img)
if success and size_kb >= MIN_IMAGE_SIZE_KB:
    images_b64.append(jpeg_img)
```

---

### 2. ✅ Processamento com GPT-4o Vision (linhas 760-807)

**Status:** ✅ PERFEITO

**Verificações:**
- ✅ Prompt instrui GPT-4o Vision a identificar tipo e número
- ✅ Formato esperado: "FIGURA 1: ...", "FLUXOGRAMA 2: ..."
- ✅ Fallback se GPT não incluir: "[Imagem {i+1} do documento] {descrição}"
- ✅ Modelo: gpt-4o-mini (econômico para descrições)
- ✅ Limite de tamanho: 1KB < imagem < 20MB
- ✅ Sleep 0.8s entre chamadas (evita rate limit)

**Prompt GPT-4o Vision:**
```
IMPORTANT: Start your description with the image type and number if visible:
- If it shows "Figura 1" or "Figure 1": Start with "FIGURA 1: ..."
- If it shows "Fluxograma 1": Start with "FLUXOGRAMA 1: ..."
- If no number is visible, identify the type: "FLUXOGRAMA: ...", "DIAGRAMA: ..."

Then describe:
1. What the image shows (flowchart, algorithm, diagram, table, graph, etc)
2. Main elements and structure
3. Key data or information
4. Clinical context if applicable
```

---

### 3. ✅ Contextual Retrieval para Imagens (linhas 1090-1120)

**Status:** ✅ IMPLEMENTADO

**Verificações:**
- ✅ Gera contexto situacional para cada imagem
- ✅ Usa GPT-4o-mini para economizar
- ✅ Formato: "[CONTEXTO]\n{contexto}\n\n[CONTEÚDO]\n{descrição}"
- ✅ Melhora retrieval em ~49% segundo Anthropic

**Exemplo de contexto gerado:**
```
[CONTEXTO]
Esta imagem faz parte do documento 'Manejo da hiperglicemia hospitalar
em pacientes não-críticos', especificamente sobre monitorização da glicemia.

[CONTEÚDO]
FIGURA 1: Fluxograma para monitorização da glicemia em ambiente hospitalar...
```

---

### 4. ✅ Armazenamento no Vectorstore + Docstore (linhas 1165-1194)

**Status:** ✅ PERFEITO

**Verificações:**
- ✅ Cada imagem gera um Document com metadata completo
- ✅ Metadata inclui:
  - `doc_id`: UUID único
  - `pdf_id`: Hash SHA256 do PDF
  - `source`: Nome do arquivo
  - `type`: "image" ✅ (CRÍTICO para filtro!)
  - `index`: Índice da imagem (0, 1, 2...)
  - `summary`: Primeiros 500 chars da descrição
  - `document_type`: Tipo do documento
  - `uploaded_at`: Timestamp
- ✅ Vectorstore armazena: summary contextualizado (para busca semântica)
- ✅ Docstore armazena: base64 original (para exibição)

**Código-chave:**
```python
doc = Document(
    page_content=contextualized_chunk,  # Para busca
    metadata={
        "doc_id": doc_id,
        "type": "image",  # ✅ ESSENCIAL!
        "summary": summary[:500],
        # ... outros metadados
    }
)

# Adicionar ao vectorstore (busca)
retriever.vectorstore.add_documents([doc])

# Adicionar ao docstore (imagem original base64)
retriever.docstore.mset([(doc_id, images[i])])
```

---

### 5. ✅ Salvamento do Docstore (linhas 1199-1202)

**Status:** ✅ PERFEITO

**Verificações:**
- ✅ Docstore é salvo como pickle: `knowledge/docstore.pkl`
- ✅ Contém mapeamento: `{doc_id: base64_string}`
- ✅ Persistido em disco (Railway Volume)

**Código:**
```python
with open(docstore_path, 'wb') as f:
    pickle.dump(dict(store.store), f)
```

---

## 🔍 PONTOS DE ATENÇÃO

### ⚠️ Filtro de 30KB

**Configuração atual:**
```python
MIN_IMAGE_SIZE_KB = 30  # Default
```

**Imagens que PASSAM:**
- ✅ Fluxogramas (geralmente 50-200KB)
- ✅ Diagramas complexos (100-500KB)
- ✅ Gráficos com dados (50-150KB)
- ✅ Screenshots de tabelas (50-200KB)

**Imagens que são FILTRADAS:**
- ❌ Ícones pequenos (<30KB)
- ❌ Logos (<30KB)
- ❌ Elementos decorativos (<30KB)
- ❌ Setas/símbolos isolados (<30KB)

**Recomendação:** ✅ Manter 30KB (está correto!)

---

### ✅ Detecção de Imagens em Queries

**Patterns que detectam queries sobre imagens:**
```python
r'\bfigura\s+\d+\b'      # "figura 1", "figura 2"
r'\bfig\.?\s*\d+\b'      # "fig. 1", "fig 2"
r'\btabela\s+\d+\b'      # "tabela 1"
r'\bfluxograma\b'        # "fluxograma"
r'\balgorit?mo\b'        # "algoritmo"
r'\bdiagrama\b'          # "diagrama"
r'\bgr[aá]fico\b'        # "gráfico"
r'\bimagem\b'            # "imagem"
```

**Teste:**
```
✅ "Explique a figura 1" → DETECTA
✅ "Descreva o fluxograma" → DETECTA
✅ "O que mostra a imagem" → DETECTA
❌ "Quais critérios de alto risco" → NÃO DETECTA (correto!)
```

---

## 📋 CHECKLIST PRÉ-REPROCESSAMENTO

### Verificações de Código:
- [x] `get_images_base64()` extrai corretamente
- [x] Conversão para JPEG funciona
- [x] Filtro de 30KB está ativo
- [x] GPT-4o Vision prompt está otimizado
- [x] Contextual Retrieval está implementado
- [x] Metadata `type: "image"` está presente
- [x] Docstore salva base64 original
- [x] Vectorstore salva summary contextualizado

### Verificações de Ambiente:
- [x] Railway está com último deploy (commit 01f6eb9)
- [x] Endpoint `/query` retorna campos `images`, `has_images`, `num_images`
- [x] Interface `/chat` exibe imagens inline
- [x] `global vectorstore` está acessível no endpoint

### Verificações de API Keys:
- [x] OPENAI_API_KEY configurada (para GPT-4o Vision)
- [x] COHERE_API_KEY configurada (para Rerank)

---

## 🚀 PRONTO PARA REPROCESSAR!

### ✅ Tudo está preparado!

**Passos para reprocessamento:**

1. **Acessar:** `https://comfortable-tenderness-production.up.railway.app/manage`

2. **Deletar documento antigo:**
   - Procurar: "Manejo da hiperglicemia hospitalar em pacientes não-críticos"
   - Clicar em "Deletar"
   - Confirmar

3. **Upload do PDF novamente:**
   - Clicar em "Choose File"
   - Selecionar: "Manejo da hiperglicemia hospitalar em pacientes não-críticos – Diretriz da SBD – Ed. 2025.pdf"
   - Clicar em "Upload PDF"

4. **Aguardar processamento (~2-5 min):**
   - ✅ Extração de texto
   - ✅ Extração de tabelas
   - ✅ **Extração de imagens** (NOVO!)
   - ✅ GPT-4o Vision gera descrições
   - ✅ Contextual Retrieval
   - ✅ Salvamento no vectorstore + docstore

5. **Verificar logs:**
   - Procurar: `"✓ X imagens processadas"`
   - Procurar: `"✓ X imagens adicionadas"`
   - **Esperado:** Pelo menos 1-3 imagens

6. **Testar no /chat:**
   - Query: `Explique a figura 1 do documento de hiperglicemia no paciente internado não crítico`
   - **Esperado:**
     - Resposta descrevendo a figura
     - 📸 Imagens (1)
     - IMAGEM VISÍVEL DO FLUXOGRAMA

---

## 🐛 Troubleshooting

### Se não extrair imagens:

**Verificar logs:**
```
railway logs | grep -i "imagem"
```

**Procurar por:**
- `"detectadas: X, filtradas: Y imagens pequenas <30KB"`
- Se `X = 0`: PDF não tem imagens ou Unstructured não extraiu
- Se `Y = X`: Todas imagens foram filtradas (muito pequenas)

**Soluções:**
- Se `Y = X`: Reduzir MIN_IMAGE_SIZE_KB temporariamente:
  ```
  railway variables set MIN_IMAGE_SIZE_KB=10
  railway up
  ```
- Reprocessar novamente

---

### Se extrair mas não aparecer na query:

**Verificar se imagens estão no vectorstore:**
```bash
curl -X POST 'https://...:app/debug-retrieval' \
  -H 'Content-Type: application/json' \
  -d '{"question": "figura", "filters": {"type": "image"}, "k": 5}'
```

**Esperado:**
```json
{
  "documents": [
    {
      "metadata": {"type": "image", "summary": "FIGURA 1: ..."},
      ...
    }
  ]
}
```

**Se vazio:** Problema no armazenamento (verificar logs de upload)

---

## 📊 Métricas Esperadas

| Métrica | Valor Esperado |
|---------|----------------|
| **Imagens detectadas** | 1-5 (depende do PDF) |
| **Imagens filtradas** | 0-2 (ícones pequenos) |
| **Imagens processadas** | 1-3 |
| **Tempo de GPT-4o Vision** | ~1-2s por imagem |
| **Tempo total de upload** | 2-5 min (com imagens) |

---

## ✅ CONFIRMAÇÃO FINAL

**Status:** 🟢 **TUDO PRONTO PARA REPROCESSAMENTO!**

**Código verificado:** ✅
**Ambiente preparado:** ✅
**APIs funcionando:** ✅
**Interface atualizada:** ✅

**Pode reprocessar o PDF sem problemas!** 🚀

---

**Criado em:** 2025-10-23
**Última verificação:** 2025-10-23 14:15
**Status:** ✅ Aprovado para reprocessamento
