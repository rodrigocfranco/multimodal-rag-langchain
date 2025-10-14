"""
Multi-modal RAG com LangChain
Este script implementa um sistema RAG que processa PDFs extraindo texto, tabelas e imagens.
"""

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Verificar se as chaves de API estão configuradas
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY não está configurada no arquivo .env")
if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY não está configurada no arquivo .env")

# Configurar variáveis de ambiente
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")

print("✓ Ambiente configurado com sucesso!")
print("=" * 80)

# ============================================================================
# 1. EXTRAÇÃO DE DADOS DO PDF
# ============================================================================
print("\n1. EXTRAINDO DADOS DO PDF...")

from unstructured.partition.pdf import partition_pdf

output_path = "./content/"
file_path = output_path + 'attention.pdf'

# Verificar se o arquivo existe
if not os.path.exists(file_path):
    print(f"⚠️  ATENÇÃO: O arquivo {file_path} não foi encontrado.")
    print("   Por favor, coloque o arquivo 'attention.pdf' no diretório 'content/'")
    print("   Você pode baixar o paper 'Attention Is All You Need' em:")
    print("   https://arxiv.org/pdf/1706.03762.pdf")
    exit(1)

# Referência: https://docs.unstructured.io/open-source/core-functionality/chunking
chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,            # extrair tabelas
    strategy="hi_res",                     # obrigatório para inferir tabelas

    extract_image_block_types=["Image, Table"],   # Adicione 'Table' para extrair imagem de tabelas
    image_output_dir_path=output_path,   # se None, imagens e tabelas serão salvos em base64

    extract_image_block_to_payload=True,   # se true, extrairá base64 para uso de API

    chunking_strategy="by_title",          # ou 'basic'
    max_characters=10000,                  # padrão é 500
    combine_text_under_n_chars=2000,       # padrão é 0
    new_after_n_chars=6000,
)

print(f"✓ {len(chunks)} chunks extraídos do PDF")

# Tipos de elementos obtidos da função partition_pdf
element_types = set([str(type(el)) for el in chunks])
print(f"✓ Tipos de elementos encontrados: {len(element_types)}")

# ============================================================================
# 2. SEPARAR ELEMENTOS EM TABELAS, TEXTO E IMAGENS
# ============================================================================
print("\n2. SEPARANDO ELEMENTOS...")

# Separar tabelas de textos
tables = []
texts = []

for chunk in chunks:
    if "Table" in str(type(chunk)):
        tables.append(chunk)
    
    if "CompositeElement" in str(type((chunk))):
        texts.append(chunk)

print(f"✓ {len(texts)} chunks de texto encontrados")
print(f"✓ {len(tables)} tabelas encontradas")

# Obter as imagens dos objetos CompositeElement
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
print(f"✓ {len(images)} imagens encontradas")

# ============================================================================
# 3. CRIAR RESUMOS DOS ELEMENTOS
# ============================================================================
print("\n3. GERANDO RESUMOS...")

# --- Resumos de texto e tabelas ---
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Prompt
prompt_text = """
You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.

Respond only with the summary, no additional comment.
Do not start your message by saying "Here is a summary" or anything like that.
Just give the summary as it is.

Table or text chunk: {element}
"""
prompt = ChatPromptTemplate.from_template(prompt_text)

# Cadeia de resumo
model = ChatGroq(temperature=0.5, model="llama-3.1-8b-instant")
summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()

# Resumir textos (com rate limiting)
import time

print("  • Resumindo textos...")
text_summaries = []
for i, text in enumerate(texts):
    try:
        summary = summarize_chain.invoke(text)
        text_summaries.append(summary)
        print(f"    {i+1}/{len(texts)} textos processados", end="\r")
        time.sleep(0.5)  # Pausa para evitar rate limit
    except Exception as e:
        print(f"\n    ⚠️  Erro ao processar texto {i+1}: {str(e)[:50]}")
        text_summaries.append(text.text[:500])  # Usar texto original como fallback
print(f"\n  ✓ {len(text_summaries)} resumos de texto criados")

# Resumir tabelas (com rate limiting)
print("  • Resumindo tabelas...")
tables_html = [table.metadata.text_as_html for table in tables]
table_summaries = []
for i, table_html in enumerate(tables_html):
    try:
        summary = summarize_chain.invoke(table_html)
        table_summaries.append(summary)
        print(f"    {i+1}/{len(tables_html)} tabelas processadas", end="\r")
        time.sleep(0.5)  # Pausa para evitar rate limit
    except Exception as e:
        print(f"\n    ⚠️  Erro ao processar tabela {i+1}: {str(e)[:50]}")
        table_summaries.append(table_html[:500])  # Usar HTML original como fallback
print(f"\n  ✓ {len(table_summaries)} resumos de tabelas criados")

# --- Resumos de imagens ---
from langchain_openai import ChatOpenAI

prompt_template = """Describe the image in detail. For context,
                  the image is part of a research paper explaining the transformers
                  architecture. Be specific about graphs, such as bar plots."""
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

print("  • Resumindo imagens...")
image_summaries = []
for i, image in enumerate(images):
    try:
        summary = chain.invoke(image)
        image_summaries.append(summary)
        print(f"    {i+1}/{len(images)} imagens processadas", end="\r")
        time.sleep(0.8)  # Pausa maior para imagens
    except Exception as e:
        print(f"\n    ⚠️  Erro ao processar imagem {i+1}: {str(e)[:50]}")
        image_summaries.append(f"Imagem {i+1} do documento")  # Descrição genérica como fallback
print(f"\n  ✓ {len(image_summaries)} resumos de imagens criados")

# ============================================================================
# 4. CARREGAR DADOS E RESUMOS NO VECTORSTORE
# ============================================================================
print("\n4. CRIANDO VECTORSTORE...")

import uuid
from langchain.vectorstores import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever

# O vectorstore para indexar os chunks filhos
vectorstore = Chroma(collection_name="multi_modal_rag", embedding_function=OpenAIEmbeddings())

# A camada de armazenamento para os documentos pai
store = InMemoryStore()
id_key = "doc_id"

# O retriever (vazio no início)
retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key=id_key,
)

# Adicionar textos
print("  • Adicionando textos...")
doc_ids = [str(uuid.uuid4()) for _ in texts]
summary_texts = [
    Document(page_content=summary, metadata={id_key: doc_ids[i]}) for i, summary in enumerate(text_summaries)
]
retriever.vectorstore.add_documents(summary_texts)
retriever.docstore.mset(list(zip(doc_ids, texts)))
print(f"  ✓ {len(texts)} textos adicionados")

# Adicionar tabelas
if len(tables) > 0:
    print("  • Adicionando tabelas...")
    table_ids = [str(uuid.uuid4()) for _ in tables]
    summary_tables = [
        Document(page_content=summary, metadata={id_key: table_ids[i]}) for i, summary in enumerate(table_summaries)
    ]
    retriever.vectorstore.add_documents(summary_tables)
    retriever.docstore.mset(list(zip(table_ids, tables)))
    print(f"  ✓ {len(tables)} tabelas adicionadas")
else:
    print("  • Nenhuma tabela para adicionar")

# Adicionar resumos de imagens
if len(images) > 0:
    print("  • Adicionando imagens...")
    img_ids = [str(uuid.uuid4()) for _ in images]
    summary_img = [
        Document(page_content=summary, metadata={id_key: img_ids[i]}) for i, summary in enumerate(image_summaries)
    ]
    retriever.vectorstore.add_documents(summary_img)
    retriever.docstore.mset(list(zip(img_ids, images)))
    print(f"  ✓ {len(images)} imagens adicionadas")
else:
    print("  • Nenhuma imagem para adicionar")

print("\n✓ Vectorstore criado com sucesso!")

# ============================================================================
# 5. PIPELINE RAG
# ============================================================================
print("\n5. CONFIGURANDO PIPELINE RAG...")

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from base64 import b64decode

def parse_docs(docs):
    """Separar imagens codificadas em base64 e textos"""
    b64 = []
    text = []
    for doc in docs:
        try:
            b64decode(doc)
            b64.append(doc)
        except Exception as e:
            text.append(doc)
    return {"images": b64, "texts": text}


def build_prompt(kwargs):
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]

    context_text = ""
    if len(docs_by_type["texts"]) > 0:
        for text_element in docs_by_type["texts"]:
            context_text += text_element.text

    # construir prompt com contexto (incluindo imagens)
    prompt_template = f"""
    Answer the question based only on the following context, which can include text, tables, and the below image.
    Context: {context_text}
    Question: {user_question}
    """

    prompt_content = [{"type": "text", "text": prompt_template}]

    if len(docs_by_type["images"]) > 0:
        for image in docs_by_type["images"]:
            prompt_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                }
            )

    return ChatPromptTemplate.from_messages(
        [
            HumanMessage(content=prompt_content),
        ]
    )


chain = (
    {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
    }
    | RunnableLambda(build_prompt)
    | ChatOpenAI(model="gpt-4o-mini")
    | StrOutputParser()
)

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

print("✓ Pipeline RAG configurado!")

# ============================================================================
# 6. TESTAR O SISTEMA
# ============================================================================
print("\n" + "=" * 80)
print("6. TESTANDO O SISTEMA RAG")
print("=" * 80)

# Teste 1
print("\n📝 Pergunta 1: What is the attention mechanism?")
print("-" * 80)
response = chain.invoke("What is the attention mechanism?")
print("Resposta:", response)

# Teste 2
print("\n" + "=" * 80)
print("📝 Pergunta 2: Who are the authors of the paper?")
print("-" * 80)
response_with_sources = chain_with_sources.invoke("Who are the authors of the paper?")
print("Resposta:", response_with_sources['response'])
print(f"\n📚 Fontes consultadas:")
print(f"  • {len(response_with_sources['context']['texts'])} textos")
print(f"  • {len(response_with_sources['context']['images'])} imagens")

# Teste 3
print("\n" + "=" * 80)
print("📝 Pergunta 3: What is multihead attention?")
print("-" * 80)
response_with_sources = chain_with_sources.invoke("What is multihead attention?")
print("Resposta:", response_with_sources['response'])
print(f"\n📚 Fontes consultadas:")
print(f"  • {len(response_with_sources['context']['texts'])} textos")
print(f"  • {len(response_with_sources['context']['images'])} imagens")

print("\n" + "=" * 80)
print("✅ SISTEMA RAG MULTIMODAL FUNCIONANDO!")
print("=" * 80)
print("\nAgora você pode usar o sistema interativamente modificando as perguntas no código")
print("ou criando uma interface de chat.")

