# 🔍 DIAGNÓSTICO DO PROBLEMA DE IMAGENS - RAG MULTIMODAL

**Data**: 2025-10-22
**Contexto**: Sistema em produção na Railway não está retornando imagens nas respostas

---

## 📊 RESUMO EXECUTIVO

### Problema Relatado
O sistema RAG multimodal não está incluindo imagens nas respostas, mesmo quando a pergunta solicita explicitamente informações visuais (fluxogramas, algoritmos, gráficos).

### Causa Raiz Identificada
**O knowledge base local está vazio** - não há documentos processados, portanto não há imagens para recuperar.

**Evidências**:
- ❌ `knowledge/docstore.pkl` não existe
- ❌ `knowledge/metadata.pkl` não existe
- ⚠️ `knowledge/chroma.sqlite3` existe mas pode estar vazio

---

## 🔬 ANÁLISE TÉCNICA DO SISTEMA

### Arquitetura Atual

O sistema possui 3 componentes principais:

#### 1. **Extração de Imagens** (`adicionar_pdf.py`)
- **Localização**: Linhas 381-477
- **Funcionamento**:
  - Usa Unstructured para extrair imagens
  - Filtra imagens pequenas (<10KB por padrão)
  - Converte TODAS para JPEG (linhas 327-378)
  - Gera descrições com GPT-4o Vision
  - Armazena em base64 no `docstore.pkl`

**Código relevante** (linhas 1143-1176):
```python
for i, summary in enumerate(image_summaries):
    doc_id = str(uuid.uuid4())
    chunk_ids.append(doc_id)

    contextualized_chunk = contextualized_images[i] if i < len(contextualized_images) else summary

    doc = Document(
        page_content=contextualized_chunk,
        metadata={
            "doc_id": doc_id,
            "pdf_id": pdf_id,
            "source": pdf_filename,
            "type": "image",  # ✅ Marcado como image
            # ...
        }
    )

    # ✅ Adiciona ao vectorstore
    retriever.vectorstore.add_documents([doc])

    # ✅ Salva imagem original (base64) no docstore
    retriever.docstore.mset([(doc_id, images[i])])  # ← AQUI
```

#### 2. **Armazenamento**
- **Vectorstore** (ChromaDB): embeddings + metadata (incluindo `type: "image"`)
- **Docstore** (pickle): imagens originais em base64
- **Metadata** (pickle): tracking de documentos processados

#### 3. **Retrieval** (`consultar_com_rerank.py`)
- **Localização**: Linhas 394-429 (`parse_docs`)
- **Funcionamento**:
  - Separa textos e imagens
  - Tenta decodificar base64 para identificar imagens
  - Converte imagens para JPEG antes de enviar ao GPT-4o Vision

**Código relevante** (linhas 418-428):
```python
# Tentar identificar se é imagem (base64)
try:
    b64decode(content)
    b64.append(content)  # ✅ Adiciona como imagem
except:
    # Se falhar, trata como texto
    text.append(TextDoc(content, metadata))
```

---

## 🐛 POSSÍVEIS CAUSAS DO PROBLEMA (em ordem de probabilidade)

### 1. ❌ **Knowledge Base Vazio** (CONFIRMADO LOCALMENTE)
**Probabilidade**: 🔴 ALTA (já confirmado no ambiente local)

**Evidências**:
- Não existe `docstore.pkl` localmente
- Não existe `metadata.pkl` localmente
- `visualizar_imagens.py` retorna 0 imagens

**Verificação no Railway**:
```bash
# Conectar via Railway CLI
railway shell

# Verificar arquivos
ls -lah $PERSIST_DIR/
cat $PERSIST_DIR/metadata.pkl | python -c "import pickle, sys; print(pickle.load(sys.stdin.buffer))"
```

**Solução**: Processar documentos com imagens usando `adicionar_pdf.py`

---

### 2. ⚠️ **Imagens Filtradas Durante Extração**
**Probabilidade**: 🟡 MÉDIA

**Causa**:
Threshold de `MIN_IMAGE_SIZE_KB=10` pode estar filtrando imagens pequenas mas importantes (fluxogramas vetoriais, diagramas).

**Evidência no código** (linhas 401, 419-428):
```python
MIN_IMAGE_SIZE_KB = float(os.getenv("MIN_IMAGE_SIZE_KB", "10"))

# ...

if size_kb >= MIN_IMAGE_SIZE_KB:
    # Aceita imagem
    images_b64.append(jpeg_img)
else:
    filtered_count += 1  # Descarta
```

**Commit recente** (22c2086):
```
FIX: Reduce image filter threshold from 30KB to 10KB (capture flowcharts!)
```
→ Você já tentou reduzir o threshold!

**Verificação**:
- Processar PDF com `DEBUG_IMAGES=1` para ver logs detalhados
- Verificar logs: `(detectadas: X, filtradas: Y imagens pequenas <10KB)`

**Solução**: Reduzir ainda mais: `MIN_IMAGE_SIZE_KB=5`

---

### 3. ⚠️ **Imagens Não Sendo Recuperadas no Retrieval**
**Probabilidade**: 🟡 MÉDIA

**Causa**:
Embeddings das descrições de imagens não fazem match com a query do usuário.

**Exemplo**:
- Query: "Existe algum fluxograma sobre hiperglicemia?"
- Descrição da imagem: "Figura mostrando algoritmo de tratamento..."
- Match ruim → imagem não aparece nos top-K resultados

**Evidência**:
- Sistema usa MultiVectorRetriever com `k=30`
- Depois aplica Cohere Rerank com `top_n=12`
- Se imagem não estiver nos 30 iniciais, não será considerada

**Verificação**:
```python
# No railway shell ou localmente
python3 -c "
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

vectorstore = Chroma(
    collection_name='knowledge_base',
    embedding_function=OpenAIEmbeddings(model='text-embedding-3-large'),
    persist_directory='./knowledge'
)

# Buscar imagens
images = vectorstore.similarity_search('', k=1000, filter={'type': 'image'})
print(f'Total de imagens: {len(images)}')

# Testar query
results = vectorstore.similarity_search('fluxograma algoritmo', k=30)
image_results = [r for r in results if r.metadata.get('type') == 'image']
print(f'Imagens nos top-30: {len(image_results)}')
"
```

**Solução**:
- Melhorar descrições das imagens (prompt do GPT-4o Vision)
- Adicionar keywords explícitas: "FLUXOGRAMA", "ALGORITMO", "DIAGRAMA"
- Aumentar `k` para 50 (capturar mais resultados iniciais)

---

### 4. 🟢 **Bug no Código de Conversão de Imagens**
**Probabilidade**: 🟢 BAIXA

**Causa**:
Função `convert_image_to_jpeg_base64()` falhando silenciosamente.

**Evidência**:
Código tem tratamento de erro mas continua (linhas 413-416):
```python
jpeg_img, success = convert_image_to_jpeg_base64(img)
if not success:
    filtered_count += 1
    continue  # ← Pula imagem se conversão falhar
```

**Verificação**:
- Logs devem mostrar: `⚠️ Erro ao converter imagem: ...`
- Se muitas imagens estão falhando, há problema

**Solução**: Adicionar logging mais detalhado

---

## 🔧 SCRIPTS DE DIAGNÓSTICO CRIADOS

### 1. `diagnostico_imagens_completo.py`
**Uso**:
```bash
python3 diagnostico_imagens_completo.py
```

**O que faz**:
- ✅ Verifica estrutura de arquivos (docstore, metadata, chroma)
- ✅ Analisa quantos documentos foram processados
- ✅ Conta imagens no docstore vs vectorstore
- ✅ Testa retrieval de imagens
- ✅ Mostra configurações (MIN_IMAGE_SIZE_KB, etc)
- ✅ Gera diagnóstico final com próximos passos

### 2. `visualizar_imagens.py` (já existente)
**Uso**:
```bash
python3 visualizar_imagens.py
```

**O que faz**:
- Busca imagens no vectorstore
- Extrai do docstore
- Salva localmente para inspeção visual

---

## ✅ PLANO DE AÇÃO (PASSO A PASSO)

### Fase 1: Diagnóstico na Railway

```bash
# 1. Conectar ao projeto
railway link -p 731ec6d7-57d7-4527-9598-fdc309ca64d0

# 2. Abrir shell
railway shell

# 3. Verificar arquivos
ls -lah $PERSIST_DIR/

# 4. Se docstore.pkl existe, rodar diagnóstico
python3 diagnostico_imagens_completo.py

# 5. Verificar metadata
python3 -c "
import pickle, os
with open(os.getenv('PERSIST_DIR', './knowledge') + '/metadata.pkl', 'rb') as f:
    m = pickle.load(f)
    for doc in m.get('documents', {}).values():
        print(f'{doc[\"filename\"]}: {doc[\"stats\"][\"images\"]} imagens')
"
```

### Fase 2: Testes Específicos

```bash
# Testar extração de imagens em um PDF específico
DEBUG_IMAGES=1 python3 adicionar_pdf.py "content/seu_pdf.pdf"

# Procurar nos logs:
# - "✓ X textos, Y tabelas, Z imagens"
# - "(detectadas: A, filtradas: B imagens pequenas)"
```

### Fase 3: Ajustes

**Se nenhuma imagem está sendo extraída:**
```bash
# Reduzir threshold
export MIN_IMAGE_SIZE_KB=5
python3 adicionar_pdf.py "content/pdf_com_imagens.pdf"
```

**Se imagens existem mas não são recuperadas:**
- Aumentar `k` no retriever (linha 132): `search_kwargs={"k": 50}`
- Aumentar `top_n` no Cohere (linha 383): `top_n=20`

---

## 📝 TESTES RECOMENDADOS (do seu documento)

Use o checklist em `test_enrichment_web.md` - especialmente:

### ✅ TESTE 7: Query sobre figura/imagem
```
Pergunta: "Existe algum fluxograma ou algoritmo sobre manejo de hiperglicemia?"

Resultado esperado:
- ✅ Menciona a imagem/figura do PDF
- ✅ Descreve o conteúdo visual
- ✅ Usa descrição do GPT-4o Vision
```

---

## 🎯 RECOMENDAÇÕES TÉCNICAS

### Curto Prazo
1. ✅ Executar `diagnostico_imagens_completo.py` na Railway
2. ✅ Verificar se há imagens processadas
3. ✅ Processar PDF com imagens se necessário

### Médio Prazo
1. 🔧 Adicionar logging detalhado:
   ```python
   print(f"   [DEBUG] Imagem {i+1}: {size_kb:.1f}KB - {'✓ aceita' if size_kb >= MIN_IMAGE_SIZE_KB else '✗ filtrada'}")
   ```

2. 🔧 Melhorar prompt de descrição de imagens (linhas 765-771):
   ```python
   prompt = "Describe this image in detail. If it's a flowchart or algorithm,
   describe the steps. If it's a table, extract the data.
   Start with: FLOWCHART: or TABLE: or DIAGRAM: to help retrieval."
   ```

3. 🔧 Adicionar metadata específica para imagens:
   ```python
   metadata={
       # ...
       "is_flowchart": "flowchart" in summary.lower(),
       "is_diagram": "diagram" in summary.lower(),
   }
   ```

### Longo Prazo
1. 📊 Implementar métricas:
   - Taxa de imagens extraídas vs total de páginas
   - Taxa de imagens recuperadas em queries
   - Precisão de match (usuário solicitou imagem → sistema retornou)

2. 🧪 A/B testing de thresholds:
   - Testar MIN_IMAGE_SIZE_KB: 5KB, 10KB, 15KB
   - Medir impacto em precisão vs recall

---

## 📚 REFERÊNCIAS NO CÓDIGO

### Extração
- `adicionar_pdf.py:381-477` - Função `get_images_base64()`
- `adicionar_pdf.py:327-378` - Conversão para JPEG
- `adicionar_pdf.py:761-788` - GPT-4o Vision para descrições

### Armazenamento
- `adicionar_pdf.py:1143-1176` - Adição ao vectorstore + docstore
- `adicionar_pdf.py:1179-1182` - Salvamento do docstore

### Retrieval
- `consultar_com_rerank.py:394-429` - Função `parse_docs()`
- `consultar_com_rerank.py:57-107` - Conversão para JPEG durante query
- `consultar_com_rerank.py:487-498` - Adição de imagens ao prompt

---

## 🆘 COMANDOS ÚTEIS

```bash
# Verificar tamanho do docstore
du -h ./knowledge/docstore.pkl

# Contar imagens no vectorstore
python3 -c "from langchain_chroma import Chroma; from langchain_openai import OpenAIEmbeddings; v=Chroma('knowledge_base', OpenAIEmbeddings(model='text-embedding-3-large'), './knowledge'); print(len(v.similarity_search('', k=1000, filter={'type':'image'})))"

# Backup do knowledge base
tar -czf knowledge_backup_$(date +%Y%m%d).tar.gz ./knowledge/

# Limpar e reprocessar
rm -rf ./knowledge/*
python3 adicionar_pdf.py "content/seu_pdf.pdf"
```

---

**Status**: 🔴 Aguardando diagnóstico na Railway
**Próximo passo**: Executar `diagnostico_imagens_completo.py` no ambiente de produção
