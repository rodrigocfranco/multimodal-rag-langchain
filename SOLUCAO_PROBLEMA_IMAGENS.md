# 🔧 SOLUÇÃO DO PROBLEMA DE IMAGENS

**Data**: 2025-10-22
**Problema**: Sistema não retorna imagens nas respostas, mesmo quando perguntado explicitamente

---

## 🎯 CAUSA RAIZ IDENTIFICADA

### Diagnóstico Completo

✅ **O que ESTÁ funcionando:**
- ChromaDB: 250 embeddings
- Docstore: 401 entradas (incluindo imagens)
- Sistema processa PDFs corretamente

❌ **O que NÃO está funcionando:**
- **Imagens NÃO aparecem no retrieval** mesmo com queries óbvias:
  - "figura" → 0 imagens
  - "imagem" → 0 imagens
  - "fluxograma" → 0 imagens
  - "algoritmo" → 0 imagens

### Causa

**As descrições geradas pelo GPT-4o Vision não fazem match semântico com as queries dos usuários.**

Exemplo:
- **Query do usuário**: "explique a figura 1"
- **Descrição da imagem** (gerada por GPT-4o): "A imagem mostra um algoritmo de tratamento com múltiplas etapas..."
- **Problema**: O embedding de "explique a figura 1" está muito distante do embedding da descrição

---

## 💡 SOLUÇÃO IMPLEMENTADA

### Abordagem: Hybrid Retrieval com Boost para Imagens

Modificar `consultar_com_rerank.py` para:

1. **Detectar queries sobre imagens** (regex patterns)
2. **Fazer busca dedicada para imagens** quando detectado
3. **Combinar resultados**: textos + imagens forçadas

---

## 🔧 IMPLEMENTAÇÃO

### Arquivo: `consultar_com_rerank_fix_images.py`

Adicionar logo após a definição do `retriever` (linha ~392):

```python
# ===========================================================================
# 🖼️ FIX: HYBRID RETRIEVAL COM BOOST PARA IMAGENS
# ===========================================================================
import re

def detect_image_query(question):
    """
    Detecta se a query do usuário está pedindo informações visuais.

    Returns:
        (bool, list): (is_image_query, keywords_found)
    """
    image_patterns = [
        r'\bfigura\s+\d+\b',  # "figura 1", "figura 2"
        r'\bfig\.?\s*\d+\b',   # "fig. 1", "fig 2"
        r'\btabela\s+\d+\b',   # "tabela 1"
        r'\bfluxograma\b',
        r'\balgorit?mo\b',
        r'\bdiagrama\b',
        r'\bgr[aá]fico\b',
        r'\bimagem\b',
        r'\bilustra[çc][ãa]o\b',
        r'\bexplique\s+(a|o)\s+(figura|imagem|fluxograma|algoritmo|diagrama)\b',
        r'\bdescreva\s+(a|o)\s+(figura|imagem|fluxograma)\b',
        r'\bo\s+que\s+(mostra|diz|apresenta)\s+(a|o)\s+(figura|imagem)\b',
    ]

    keywords_found = []
    for pattern in image_patterns:
        match = re.search(pattern, question.lower())
        if match:
            keywords_found.append(match.group(0))

    return len(keywords_found) > 0, keywords_found


def force_include_images(question, base_results, vectorstore, max_images=3):
    """
    Força inclusão de imagens relevantes quando query é sobre conteúdo visual.

    Args:
        question: Query do usuário
        base_results: Resultados do retrieval normal
        vectorstore: ChromaDB vectorstore
        max_images: Máximo de imagens a incluir (default: 3)

    Returns:
        list: Resultados combinados (base_results + imagens forçadas)
    """
    is_image_query, keywords = detect_image_query(question)

    if not is_image_query:
        return base_results  # Não modifica se não for query sobre imagens

    print(f"   🖼️ Query sobre imagens detectada! Keywords: {keywords}")

    # Buscar DIRETAMENTE por imagens (filtro type='image')
    try:
        # Tentar múltiplas estratégias de busca
        image_queries = [
            question,  # Query original
            " ".join(keywords),  # Keywords extraídas
            "figura fluxograma algoritmo diagrama",  # Genérica
        ]

        found_images = []
        seen_doc_ids = set()

        for img_query in image_queries:
            try:
                images = vectorstore.similarity_search(
                    img_query,
                    k=20,  # Buscar mais para aumentar chances
                    filter={"type": "image"}
                )

                for img in images:
                    doc_id = img.metadata.get('doc_id')
                    if doc_id and doc_id not in seen_doc_ids:
                        found_images.append(img)
                        seen_doc_ids.add(doc_id)

                        if len(found_images) >= max_images:
                            break

            except Exception as e:
                print(f"      ⚠️ Erro na busca com filtro: {str(e)[:100]}")
                continue

            if len(found_images) >= max_images:
                break

        if found_images:
            print(f"   ✓ Forçando inclusão de {len(found_images)} imagens")

            # IMPORTANTE: Adicionar imagens NO INÍCIO dos resultados
            # Isso garante que passarão pelo rerank com prioridade
            combined_results = found_images + base_results

            # Deduplicate por doc_id
            seen = set()
            unique_results = []
            for doc in combined_results:
                doc_id = doc.metadata.get('doc_id')
                if doc_id not in seen:
                    seen.add(doc_id)
                    unique_results.append(doc)

            return unique_results[:40]  # Limitar a 40 para não sobrecarregar rerank

        else:
            print(f"   ⚠️ Nenhuma imagem encontrada mesmo com filtro!")
            return base_results

    except Exception as e:
        print(f"   ✗ Erro ao forçar inclusão de imagens: {str(e)[:200]}")
        return base_results
```

### Modificar o retriever wrapper:

Substituir o `wrapped_retriever` atual (linha ~170) por:

```python
# Wrapper do retriever para converter objetos E forçar imagens
class DocumentConverterWithImageBoost(BaseRetriever):
    retriever: MultiVectorRetriever
    vectorstore: any  # Vectorstore para busca direta de imagens

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        # 1. Retrieval normal
        docs = self.retriever.invoke(query)

        # 2. Converter para Documents
        converted = []
        for doc in docs:
            if hasattr(doc, 'page_content'):
                converted.append(doc)
            elif hasattr(doc, 'text'):
                metadata = {}
                if hasattr(doc, 'metadata'):
                    if isinstance(doc.metadata, dict):
                        metadata = doc.metadata
                    else:
                        metadata = doc.metadata.to_dict() if hasattr(doc.metadata, 'to_dict') else {}

                converted.append(Document(
                    page_content=doc.text,
                    metadata=metadata
                ))
            elif isinstance(doc, str):
                converted.append(Document(page_content=doc, metadata={}))
            else:
                converted.append(Document(page_content=str(doc), metadata={}))

        # 3. FORÇA INCLUSÃO DE IMAGENS se query for sobre imagens
        enhanced_results = force_include_images(
            question=query,
            base_results=converted,
            vectorstore=self.vectorstore,
            max_images=3
        )

        return enhanced_results

# Usar novo wrapper
wrapped_retriever = DocumentConverterWithImageBoost(
    retriever=base_retriever,
    vectorstore=vectorstore  # ← Passar vectorstore para busca direta
)
```

---

## 🧪 TESTE DA SOLUÇÃO

Após deploy:

```bash
# Teste 1: Query explícita sobre figura
curl -X POST https://seu-app.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "explique a figura 1 do documento sobre hiperglicemia"}'

# Resultado esperado:
# ✓ Sistema detecta "figura 1" como query de imagem
# ✓ Força busca de imagens com filtro type='image'
# ✓ Adiciona imagens aos resultados
# ✓ GPT-4o recebe imagens e responde sobre elas
```

---

## 📊 RESULTADOS ESPERADOS

### Antes da solução:
```
Q: explique a figura 1 do documento manejo de hiperglicemia
A: A informação solicitada não está presente nos documentos fornecidos.
```

### Depois da solução:
```
Q: explique a figura 1 do documento manejo de hiperglicemia
A: A Figura 1 apresenta um fluxograma de decisão para manejo da hiperglicemia
   hospitalar em pacientes não-críticos, mostrando:

   1. Avaliação inicial da glicemia
   2. Critérios para início de insulinoterapia (glicemia >180 mg/dL)
   3. Algoritmo de ajuste de dose
   ...

   [Descrição baseada na imagem recuperada do PDF]
```

---

## 🎯 MELHORIAS ADICIONAIS (Opcional)

### 1. Melhorar Descrições de Imagens

Modificar o prompt do GPT-4o Vision em `adicionar_pdf.py` (linhas 765-771):

```python
prompt_img = ChatPromptTemplate.from_messages([
    ("user", [
        {
            "type": "text",
            "text": """Descreva esta imagem médica em detalhes.

IMPORTANTE: Comece sua descrição com o TIPO de imagem:
- Se for fluxograma: "FLUXOGRAMA: ..."
- Se for tabela: "TABELA: ..."
- Se for gráfico: "GRÁFICO: ..."
- Se for diagrama: "DIAGRAMA: ..."
- Se for algoritmo: "ALGORITMO: ..."

Depois descreva:
1. O que a imagem mostra
2. Elementos principais
3. Dados ou informações chave
4. Contexto clínico (se aplicável)"""
        },
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{image}"}},
    ])
])
```

Isso vai fazer com que descrições comecem com "FLUXOGRAMA: ...", melhorando o match semântico.

### 2. Adicionar Metadata Específica

Em `adicionar_pdf.py` (linha ~1155), adicionar mais metadata:

```python
doc = Document(
    page_content=contextualized_chunk,
    metadata={
        "doc_id": doc_id,
        "pdf_id": pdf_id,
        "source": pdf_filename,
        "type": "image",
        "summary": summary[:500],
        # ✅ NOVOS METADADOS
        "is_figure": "figura" in summary.lower() or "figure" in summary.lower(),
        "is_flowchart": "fluxograma" in summary.lower() or "flowchart" in summary.lower() or "algoritmo" in summary.lower(),
        "is_diagram": "diagrama" in summary.lower() or "diagram" in summary.lower(),
        "is_table_image": "tabela" in summary.lower() or "table" in summary.lower(),
    }
)
```

---

## 🚀 DEPLOY

### 1. Aplicar mudanças:

```bash
# Editar consultar_com_rerank.py com as modificações acima
vim consultar_com_rerank.py

# Commit
git add consultar_com_rerank.py
git commit -m "FIX: Add hybrid retrieval with forced image inclusion for image queries"

# Push para Railway
git push origin main
```

### 2. Verificar deploy:

```bash
railway logs --follow
```

### 3. Testar:

Abrir `https://seu-app.railway.app/chat` e perguntar:
- "explique a figura 1"
- "mostre o fluxograma de hiperglicemia"
- "descreva o algoritmo da figura 2"

---

## 📝 CHECKLIST DE VALIDAÇÃO

- [ ] Código modificado em `consultar_com_rerank.py`
- [ ] Funções `detect_image_query()` e `force_include_images()` adicionadas
- [ ] `DocumentConverterWithImageBoost` implementado
- [ ] Commit e push para repositório
- [ ] Deploy na Railway concluído
- [ ] Teste com query "explique a figura 1"
- [ ] Sistema retorna descrição da imagem
- [ ] (Opcional) Melhorar prompt do GPT-4o Vision
- [ ] (Opcional) Adicionar metadata específica para imagens

---

## 🆘 TROUBLESHOOTING

### Se ainda não funcionar:

1. **Verificar logs**:
```bash
railway logs | grep "🖼️"
```
Procurar por: "Query sobre imagens detectada!"

2. **Verificar se imagens existem**:
```python
# No railway shell ou via script
python3 -c "
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
v = Chroma('knowledge_base', OpenAIEmbeddings(model='text-embedding-3-large'), '/app/knowledge')
imgs = v.similarity_search('', k=1000, filter={'type': 'image'})
print(f'Total de imagens: {len(imgs)}')
"
```

3. **Reprocessar PDFs** (última opção):
```bash
# Via Railway shell
railway run python3 adicionar_pdf.py "content/seu_pdf.pdf"
```

---

**Status**: ✅ Solução pronta para implementação
**Tempo estimado**: 15-30 minutos (código + deploy + teste)
