# 📄 Como Usar Outros PDFs no Sistema RAG

## 🎯 3 Formas de Processar Seus Próprios PDFs

---

## ✅ Método 1: Substituir o PDF (Mais Simples)

### Passo a Passo:

1. **Copie seu PDF para o diretório `content/`**
   ```bash
   cp /caminho/para/seu_arquivo.pdf /Users/rcfranco/multimodal-rag-langchain/content/
   ```

2. **Edite o arquivo `multimodal_rag.py`**
   
   Abra o arquivo e vá até a **linha 30**:
   
   ```python
   # ANTES:
   file_path = output_path + 'attention.pdf'
   
   # DEPOIS:
   file_path = output_path + 'seu_arquivo.pdf'
   ```

3. **Execute normalmente**
   ```bash
   source venv/bin/activate
   python multimodal_rag.py
   ```

### Exemplo Prático:
```bash
# 1. Copiar PDF
cp ~/Downloads/meu_artigo.pdf content/

# 2. Editar multimodal_rag.py (linha 30)
# Trocar: file_path = output_path + 'meu_artigo.pdf'

# 3. Executar
python multimodal_rag.py
```

---

## ✅ Método 2: Script com Argumento de Linha de Comando

Vou criar um script que aceita o nome do PDF como parâmetro!

**Arquivo: `rag_custom_pdf.py`** (criar este arquivo)

```python
#!/usr/bin/env python3
"""
RAG Multimodal - Versão com Argumento de Linha de Comando
Uso: python rag_custom_pdf.py nome_do_arquivo.pdf
"""

import sys
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Verificar argumentos
if len(sys.argv) < 2:
    print("❌ Erro: Forneça o nome do arquivo PDF")
    print("\nUso:")
    print("  python rag_custom_pdf.py nome_do_arquivo.pdf")
    print("\nExemplo:")
    print("  python rag_custom_pdf.py meu_artigo.pdf")
    sys.exit(1)

# Obter nome do arquivo
pdf_filename = sys.argv[1]
output_path = "./content/"
file_path = output_path + pdf_filename

# Verificar se o arquivo existe
if not os.path.exists(file_path):
    print(f"❌ Erro: Arquivo não encontrado: {file_path}")
    print(f"\nCertifique-se de que o arquivo está no diretório 'content/'")
    print(f"Exemplo: cp ~/Downloads/{pdf_filename} content/")
    sys.exit(1)

print(f"✓ Processando PDF: {pdf_filename}")
print("=" * 80)

# [RESTO DO CÓDIGO É IGUAL AO multimodal_rag.py]
# Copie todo o código do multimodal_rag.py EXCETO as linhas 26-31
# A variável file_path já foi definida acima

# === COPIE DAQUI O RESTO DO CÓDIGO ===
from unstructured.partition.pdf import partition_pdf

# Configurar variáveis de ambiente
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")

print("\n1. EXTRAINDO DADOS DO PDF...")

chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image"],
    extract_image_block_to_payload=True,
    chunking_strategy="by_title",
    max_characters=10000,
    combine_text_under_n_chars=2000,
    new_after_n_chars=6000,
)

# ... [resto do código do multimodal_rag.py]
```

### Como Usar:
```bash
# Copiar PDF
cp ~/Downloads/meu_artigo.pdf content/

# Executar com o nome do arquivo
python rag_custom_pdf.py meu_artigo.pdf
```

---

## ✅ Método 3: Processar Múltiplos PDFs (Avançado)

Este método processa TODOS os PDFs no diretório `content/` de uma vez!

**Arquivo: `rag_multiplos_pdfs.py`** (criar este arquivo)

```python
#!/usr/bin/env python3
"""
RAG Multimodal - Processar Múltiplos PDFs
Processa todos os arquivos .pdf no diretório content/
"""

import os
import glob
from dotenv import load_dotenv

load_dotenv()

# Listar todos os PDFs
pdf_files = glob.glob("content/*.pdf")

if not pdf_files:
    print("❌ Nenhum PDF encontrado no diretório content/")
    print("   Copie seus PDFs para o diretório content/")
    exit(1)

print(f"✓ {len(pdf_files)} PDF(s) encontrado(s):")
for pdf in pdf_files:
    size = os.path.getsize(pdf) / 1024 / 1024
    print(f"  • {pdf} ({size:.1f} MB)")

print("\n" + "=" * 80)
print("PROCESSANDO MÚLTIPLOS PDFs")
print("=" * 80)

# Importar bibliotecas necessárias
from unstructured.partition.pdf import partition_pdf
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import uuid
from langchain_community.vectorstores import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
import time

# Criar vectorstore único para todos os PDFs
print("\nCriando vectorstore...")
vectorstore = Chroma(
    collection_name="multi_modal_rag_multiple",
    embedding_function=OpenAIEmbeddings()
)
store = InMemoryStore()
id_key = "doc_id"

retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key=id_key,
)

# Processar cada PDF
all_texts = []
all_tables = []
all_images = []

for pdf_idx, file_path in enumerate(pdf_files, 1):
    print(f"\n{'=' * 80}")
    print(f"PDF {pdf_idx}/{len(pdf_files)}: {os.path.basename(file_path)}")
    print('=' * 80)
    
    # 1. EXTRAIR DADOS
    print(f"\n1. Extraindo dados...")
    chunks = partition_pdf(
        filename=file_path,
        infer_table_structure=True,
        strategy="hi_res",
        extract_image_block_types=["Image"],
        extract_image_block_to_payload=True,
        chunking_strategy="by_title",
        max_characters=10000,
        combine_text_under_n_chars=2000,
        new_after_n_chars=6000,
    )
    
    print(f"✓ {len(chunks)} chunks extraídos")
    
    # 2. SEPARAR ELEMENTOS
    print(f"\n2. Separando elementos...")
    texts = []
    tables = []
    
    for chunk in chunks:
        # Adicionar metadado do arquivo de origem
        if hasattr(chunk, 'metadata'):
            chunk.metadata.source_file = os.path.basename(file_path)
        
        if "Table" in str(type(chunk)):
            tables.append(chunk)
        if "CompositeElement" in str(type(chunk)):
            texts.append(chunk)
    
    def get_images_base64(chunks):
        images_b64 = []
        for chunk in chunks:
            if "CompositeElement" in str(type(chunk)):
                chunk_els = chunk.metadata.orig_elements
                for el in chunk_els:
                    if "Image" in str(type(el)):
                        images_b64.append(el.metadata.image_base64)
        return images_b64
    
    images = get_images_base64(chunks)
    
    print(f"✓ {len(texts)} textos, {len(tables)} tabelas, {len(images)} imagens")
    
    all_texts.extend(texts)
    all_tables.extend(tables)
    all_images.extend(images)

# 3. GERAR RESUMOS DE TODOS OS DOCUMENTOS
print(f"\n{'=' * 80}")
print("3. GERANDO RESUMOS DE TODOS OS DOCUMENTOS")
print('=' * 80)

# Configurar modelo
model = ChatGroq(temperature=0.5, model="llama-3.1-8b-instant")
prompt_text = """
You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.

Respond only with the summary, no additional comment.
Do not start your message by saying "Here is a summary" or anything like that.
Just give the summary as it is.

Table or text chunk: {element}
"""
prompt = ChatPromptTemplate.from_template(prompt_text)
summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()

# Resumir textos
print(f"\n  • Resumindo {len(all_texts)} textos...")
text_summaries = []
for i, text in enumerate(all_texts):
    try:
        summary = summarize_chain.invoke(text)
        text_summaries.append(summary)
        print(f"    {i+1}/{len(all_texts)} textos processados", end="\r")
        time.sleep(0.5)
    except Exception as e:
        print(f"\n    ⚠️  Erro no texto {i+1}: {str(e)[:50]}")
        text_summaries.append(text.text[:500])

print(f"\n  ✓ {len(text_summaries)} resumos de texto criados")

# Resumir tabelas
if len(all_tables) > 0:
    print(f"\n  • Resumindo {len(all_tables)} tabelas...")
    tables_html = [table.metadata.text_as_html for table in all_tables]
    table_summaries = []
    for i, table_html in enumerate(tables_html):
        try:
            summary = summarize_chain.invoke(table_html)
            table_summaries.append(summary)
            print(f"    {i+1}/{len(tables_html)} tabelas processadas", end="\r")
            time.sleep(0.5)
        except Exception as e:
            print(f"\n    ⚠️  Erro na tabela {i+1}: {str(e)[:50]}")
            table_summaries.append(table_html[:500])
    print(f"\n  ✓ {len(table_summaries)} resumos de tabelas criados")
else:
    table_summaries = []

# Resumir imagens
if len(all_images) > 0:
    print(f"\n  • Resumindo {len(all_images)} imagens...")
    prompt_template = """Describe the image in detail. For context,
                      the image is part of research documents."""
    messages = [
        (
            "user",
            [
                {"type": "text", "text": prompt_template},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,{image}"},
                },
            ],
        )
    ]
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()
    
    image_summaries = []
    for i, image in enumerate(all_images):
        try:
            summary = chain.invoke(image)
            image_summaries.append(summary)
            print(f"    {i+1}/{len(all_images)} imagens processadas", end="\r")
            time.sleep(0.8)
        except Exception as e:
            print(f"\n    ⚠️  Erro na imagem {i+1}: {str(e)[:50]}")
            image_summaries.append(f"Imagem {i+1}")
    print(f"\n  ✓ {len(image_summaries)} resumos de imagens criados")
else:
    image_summaries = []

# 4. ADICIONAR AO VECTORSTORE
print(f"\n{'=' * 80}")
print("4. ADICIONANDO TUDO AO VECTORSTORE")
print('=' * 80)

# Adicionar textos
if len(all_texts) > 0:
    print(f"\n  • Adicionando {len(all_texts)} textos...")
    doc_ids = [str(uuid.uuid4()) for _ in all_texts]
    summary_texts = [
        Document(page_content=summary, metadata={
            id_key: doc_ids[i],
            "source_file": all_texts[i].metadata.source_file if hasattr(all_texts[i].metadata, 'source_file') else "unknown"
        }) for i, summary in enumerate(text_summaries)
    ]
    retriever.vectorstore.add_documents(summary_texts)
    retriever.docstore.mset(list(zip(doc_ids, all_texts)))
    print(f"  ✓ {len(all_texts)} textos adicionados")

# Adicionar tabelas
if len(all_tables) > 0:
    print(f"\n  • Adicionando {len(all_tables)} tabelas...")
    table_ids = [str(uuid.uuid4()) for _ in all_tables]
    summary_tables = [
        Document(page_content=summary, metadata={
            id_key: table_ids[i],
            "source_file": all_tables[i].metadata.source_file if hasattr(all_tables[i].metadata, 'source_file') else "unknown"
        }) for i, summary in enumerate(table_summaries)
    ]
    retriever.vectorstore.add_documents(summary_tables)
    retriever.docstore.mset(list(zip(table_ids, all_tables)))
    print(f"  ✓ {len(all_tables)} tabelas adicionadas")

# Adicionar imagens
if len(all_images) > 0:
    print(f"\n  • Adicionando {len(all_images)} imagens...")
    img_ids = [str(uuid.uuid4()) for _ in all_images]
    summary_img = [
        Document(page_content=summary, metadata={id_key: img_ids[i]}) 
        for i, summary in enumerate(image_summaries)
    ]
    retriever.vectorstore.add_documents(summary_img)
    retriever.docstore.mset(list(zip(img_ids, all_images)))
    print(f"  ✓ {len(all_images)} imagens adicionadas")

print("\n✓ Vectorstore criado com TODOS os PDFs!")

# 5. CONFIGURAR PIPELINE E TESTAR
print(f"\n{'=' * 80}")
print("5. TESTANDO O SISTEMA COM MÚLTIPLOS PDFs")
print('=' * 80)

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage
from base64 import b64decode

def parse_docs(docs):
    b64 = []
    text = []
    for doc in docs:
        try:
            b64decode(doc)
            b64.append(doc)
        except:
            text.append(doc)
    return {"images": b64, "texts": text}

def build_prompt(kwargs):
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]
    
    context_text = ""
    if len(docs_by_type["texts"]) > 0:
        for text_element in docs_by_type["texts"]:
            # Adicionar informação do arquivo de origem
            source = text_element.metadata.get('source_file', 'unknown')
            context_text += f"\n[Fonte: {source}]\n{text_element.text}\n"
    
    prompt_template = f"""
    Answer the question based on the following context from multiple documents.
    Context: {context_text}
    Question: {user_question}
    """
    
    prompt_content = [{"type": "text", "text": prompt_template}]
    
    if len(docs_by_type["images"]) > 0:
        for image in docs_by_type["images"]:
            prompt_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"},
            })
    
    return ChatPromptTemplate.from_messages([HumanMessage(content=prompt_content)])

chain_with_sources = {
    "context": retriever | RunnableLambda(parse_docs),
    "question": RunnablePassthrough(),
} | RunnablePassthrough().assign(
    response=(
        RunnableLambda(build_prompt)
        | ChatOpenAI(model="gpt-4o-mini")
        | StrOutputParser()
    )
)

# Fazer pergunta geral sobre todos os documentos
print("\n📝 Pergunta: What are the main topics covered in these documents?")
print("-" * 80)
response = chain_with_sources.invoke("What are the main topics covered in these documents?")
print("Resposta:", response['response'])
print(f"\n📚 Fontes consultadas:")
print(f"  • {len(response['context']['texts'])} textos")
print(f"  • {len(response['context']['images'])} imagens")

# Identificar arquivos fonte
sources = set()
for text in response['context']['texts']:
    if hasattr(text.metadata, 'source_file'):
        sources.add(text.metadata.source_file)
    elif 'source_file' in text.metadata:
        sources.add(text.metadata.source_file)

if sources:
    print(f"\n📄 Arquivos consultados:")
    for source in sources:
        print(f"  • {source}")

print("\n" + "=" * 80)
print("✅ PROCESSAMENTO DE MÚLTIPLOS PDFs COMPLETO!")
print("=" * 80)
print(f"\nTotal processado: {len(pdf_files)} PDF(s)")
print(f"  • {len(all_texts)} chunks de texto")
print(f"  • {len(all_tables)} tabelas")
print(f"  • {len(all_images)} imagens")
```

### Como Usar:
```bash
# 1. Copiar vários PDFs
cp ~/Downloads/*.pdf content/

# 2. Executar
python rag_multiplos_pdfs.py
```

---

## 📋 Comparação dos Métodos

| Método | Facilidade | Flexibilidade | Uso |
|--------|------------|---------------|-----|
| **Método 1** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Um PDF por vez |
| **Método 2** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Um PDF por vez (mais flexível) |
| **Método 3** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Múltiplos PDFs juntos |

---

## 💡 Dicas Importantes

### 1. Tamanho dos PDFs
- **PDFs pequenos** (< 20 páginas): Processam em 3-5 minutos
- **PDFs médios** (20-50 páginas): Processam em 5-10 minutos
- **PDFs grandes** (> 50 páginas): Podem demorar 15+ minutos

### 2. Rate Limits
Ao processar múltiplos PDFs, você pode atingir limites de API:
- **Groq**: 6000 tokens/minuto (gratuito)
- **OpenAI**: Depende do seu plano

**Solução**: Aumente o `time.sleep()` nos scripts

### 3. Qualidade dos PDFs
Funciona melhor com:
- ✅ PDFs com texto selecionável
- ✅ Imagens de boa qualidade
- ✅ Tabelas bem formatadas

Pode ter problemas com:
- ❌ PDFs escaneados (só imagem)
- ❌ PDFs muito antigos ou mal formatados
- ❌ PDFs protegidos por senha

---

## 🚀 Exemplo Completo

### Cenário: Processar 3 artigos científicos

```bash
# 1. Organizar PDFs
cd /Users/rcfranco/multimodal-rag-langchain
mkdir -p content
cp ~/Downloads/artigo1.pdf content/
cp ~/Downloads/artigo2.pdf content/
cp ~/Downloads/artigo3.pdf content/

# 2. Listar PDFs
ls -lh content/*.pdf

# 3. Processar todos de uma vez
source venv/bin/activate
python rag_multiplos_pdfs.py

# 4. Fazer perguntas que buscam em TODOS os documentos
# O sistema vai responder baseado em todos os 3 artigos!
```

---

## ❓ Perguntas Frequentes

### Q: Posso processar PDFs em português?
**R:** Sim! O sistema funciona com qualquer idioma. Você pode até fazer perguntas em português sobre PDFs em inglês.

### Q: Quanto custa processar um PDF?
**R:** Depende do tamanho:
- **Groq**: Gratuito (com limites)
- **OpenAI**: ~$0.10 a $0.50 por PDF médio

### Q: Posso salvar o vectorstore para não reprocessar?
**R:** Sim! Adicione `persist_directory` no Chroma:
```python
vectorstore = Chroma(
    collection_name="multi_modal_rag",
    embedding_function=OpenAIEmbeddings(),
    persist_directory="./chroma_db"  # Salvar em disco
)
```

### Q: Como limpar o vectorstore e começar de novo?
**R:** Delete o diretório `chroma_db`:
```bash
rm -rf chroma_db/
```

---

## 📞 Próximos Passos

1. **Teste com seu PDF**: Use o Método 1 primeiro
2. **Experimente múltiplos PDFs**: Use o Método 3
3. **Crie interface web**: Use Streamlit para facilitar

**Boa sorte processando seus PDFs! 🎉**

