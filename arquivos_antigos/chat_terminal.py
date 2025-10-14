#!/usr/bin/env python3
"""
Chat Interativo no Terminal - RAG Multimodal
Permite fazer perguntas sobre o PDF de forma interativa
"""

import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

print("=" * 80)
print("💬 CHAT INTERATIVO - RAG MULTIMODAL")
print("=" * 80)
print()

# Verificar argumentos
if len(sys.argv) < 2:
    print("❌ Uso: python chat_terminal.py nome_do_arquivo.pdf")
    print()
    print("Exemplo:")
    print("  python chat_terminal.py attention.pdf")
    print("  python chat_terminal.py 'Manejo da terapia antidiabética no DM2.pdf'")
    sys.exit(1)

pdf_filename = sys.argv[1]
output_path = "./content/"
file_path = output_path + pdf_filename

if not os.path.exists(file_path):
    print(f"❌ Arquivo não encontrado: {file_path}")
    sys.exit(1)

print(f"📄 Processando PDF: {pdf_filename}")
print("⏳ Aguarde... (isso pode levar 5-10 minutos)")
print()

# ============================================================================
# 1. PROCESSAR PDF
# ============================================================================
from unstructured.partition.pdf import partition_pdf
import time

os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")

print("1️⃣  Extraindo dados do PDF...")
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
print(f"   ✓ {len(chunks)} chunks extraídos")

# Separar elementos
tables = []
texts = []
for chunk in chunks:
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
print(f"   ✓ {len(texts)} textos, {len(tables)} tabelas, {len(images)} imagens")

# ============================================================================
# 2. GERAR RESUMOS
# ============================================================================
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

print("\n2️⃣  Gerando resumos com IA...")

# Resumir textos
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

text_summaries = []
for i, text in enumerate(texts):
    try:
        summary = summarize_chain.invoke(text)
        text_summaries.append(summary)
        print(f"   Resumindo textos: {i+1}/{len(texts)}", end="\r")
        time.sleep(0.5)
    except Exception as e:
        text_summaries.append(text.text[:500])

print(f"\n   ✓ {len(text_summaries)} resumos de texto")

# Resumir tabelas
table_summaries = []
if len(tables) > 0:
    tables_html = [table.metadata.text_as_html for table in tables]
    for i, table_html in enumerate(tables_html):
        try:
            summary = summarize_chain.invoke(table_html)
            table_summaries.append(summary)
            print(f"   Resumindo tabelas: {i+1}/{len(tables_html)}", end="\r")
            time.sleep(0.5)
        except:
            table_summaries.append(table_html[:500])
    print(f"\n   ✓ {len(table_summaries)} resumos de tabelas")

# Resumir imagens
image_summaries = []
if len(images) > 0:
    prompt_template = """Describe the image in detail. For context,
                      the image is part of a document."""
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
    
    for i, image in enumerate(images):
        try:
            summary = chain.invoke(image)
            image_summaries.append(summary)
            print(f"   Resumindo imagens: {i+1}/{len(images)}", end="\r")
            time.sleep(0.8)
        except:
            image_summaries.append(f"Imagem {i+1}")
    print(f"\n   ✓ {len(image_summaries)} resumos de imagens")

# ============================================================================
# 3. CRIAR VECTORSTORE
# ============================================================================
print("\n3️⃣  Criando banco de dados vetorial...")

import uuid
from langchain_community.vectorstores import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever

vectorstore = Chroma(
    collection_name="chat_rag",
    embedding_function=OpenAIEmbeddings()
)
store = InMemoryStore()
id_key = "doc_id"

retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key=id_key,
)

# Adicionar textos
doc_ids = [str(uuid.uuid4()) for _ in texts]
summary_texts = [
    Document(page_content=summary, metadata={id_key: doc_ids[i]}) 
    for i, summary in enumerate(text_summaries)
]
retriever.vectorstore.add_documents(summary_texts)
retriever.docstore.mset(list(zip(doc_ids, texts)))

# Adicionar tabelas
if len(tables) > 0:
    table_ids = [str(uuid.uuid4()) for _ in tables]
    summary_tables = [
        Document(page_content=summary, metadata={id_key: table_ids[i]}) 
        for i, summary in enumerate(table_summaries)
    ]
    retriever.vectorstore.add_documents(summary_tables)
    retriever.docstore.mset(list(zip(table_ids, tables)))

# Adicionar imagens
if len(images) > 0:
    img_ids = [str(uuid.uuid4()) for _ in images]
    summary_img = [
        Document(page_content=summary, metadata={id_key: img_ids[i]}) 
        for i, summary in enumerate(image_summaries)
    ]
    retriever.vectorstore.add_documents(summary_img)
    retriever.docstore.mset(list(zip(img_ids, images)))

print("   ✓ Banco de dados criado!")

# ============================================================================
# 4. CONFIGURAR PIPELINE RAG
# ============================================================================
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
            context_text += text_element.text
    
    prompt_template = f"""
    Answer the question based only on the following context, which can include text, tables, and images.
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

# ============================================================================
# 5. LOOP DE CHAT INTERATIVO
# ============================================================================
print("\n" + "=" * 80)
print("✅ SISTEMA PRONTO! Você pode fazer perguntas agora.")
print("=" * 80)
print()
print("💡 Dicas:")
print("  • Digite sua pergunta e pressione Enter")
print("  • Digite 'sair' ou 'exit' para encerrar")
print("  • Digite 'info' para ver estatísticas do documento")
print("  • Digite 'exemplos' para ver perguntas sugeridas")
print()

conversation_count = 0

while True:
    try:
        # Obter pergunta do usuário
        print("─" * 80)
        question = input("\n🤔 Sua pergunta: ").strip()
        
        if not question:
            continue
        
        # Comandos especiais
        if question.lower() in ['sair', 'exit', 'quit', 'q']:
            print("\n👋 Encerrando chat. Até logo!")
            break
        
        if question.lower() == 'info':
            print(f"\n📊 Estatísticas do documento:")
            print(f"  • Arquivo: {pdf_filename}")
            print(f"  • Chunks de texto: {len(texts)}")
            print(f"  • Tabelas: {len(tables)}")
            print(f"  • Imagens: {len(images)}")
            print(f"  • Perguntas feitas: {conversation_count}")
            continue
        
        if question.lower() == 'exemplos':
            print("\n💡 Perguntas sugeridas:")
            print("  • What is the main topic of this document?")
            print("  • Summarize the key points")
            print("  • What are the main findings?")
            print("  • Explain the methodology used")
            print("  • What are the conclusions?")
            continue
        
        # Processar pergunta
        print("\n⏳ Processando...")
        response = chain_with_sources.invoke(question)
        
        conversation_count += 1
        
        # Mostrar resposta
        print("\n🤖 Resposta:")
        print("-" * 80)
        print(response['response'])
        print("-" * 80)
        
        # Mostrar fontes
        num_texts = len(response['context']['texts'])
        num_images = len(response['context']['images'])
        print(f"\n📚 Fontes: {num_texts} textos, {num_images} imagens")
        
    except KeyboardInterrupt:
        print("\n\n👋 Encerrando chat. Até logo!")
        break
    except Exception as e:
        print(f"\n❌ Erro: {str(e)[:100]}")
        print("Tente outra pergunta.")

print()
print("=" * 80)
print(f"Sessão encerrada. Total de perguntas: {conversation_count}")
print("=" * 80)

