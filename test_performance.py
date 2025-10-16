#!/usr/bin/env python3
"""
Script de Teste de Performance - RAG System
Testa latência, precisão e overhead do sistema otimizado
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("🧪 TESTE DE PERFORMANCE - Sistema RAG Otimizado")
print("=" * 70)
print()

# Verificar se há knowledge base
persist_directory = "./knowledge_base"
if not os.path.exists(persist_directory):
    print("❌ Knowledge base não encontrado!")
    print("Execute: python adicionar_pdf.py <arquivo.pdf>")
    exit(1)

# Carregar sistema
print("📦 Carregando sistema...")
start_load = time.time()

from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain_cohere import CohereRerank
from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from typing import List
from base64 import b64decode
import pickle

vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(),
    persist_directory=persist_directory
)

docstore_path = f"{persist_directory}/docstore.pkl"
store = InMemoryStore()
if os.path.exists(docstore_path):
    with open(docstore_path, 'rb') as f:
        store.store = pickle.load(f)

base_retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key="doc_id",
    search_kwargs={"k": 20}  # Otimizado
)

class DocumentConverter(BaseRetriever):
    retriever: MultiVectorRetriever

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        docs = self.retriever.invoke(query)
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
        return converted

wrapped_retriever = DocumentConverter(retriever=base_retriever)

compressor = CohereRerank(
    model="rerank-multilingual-v3.0",
    top_n=5
)

retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=wrapped_retriever
)

def parse_docs(docs):
    b64, text = [], []
    for doc in docs:
        if hasattr(doc, 'page_content'):
            content = doc.page_content
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
        elif hasattr(doc, 'text'):
            content = doc.text
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
        elif isinstance(doc, str):
            content = doc
            metadata = {}
        else:
            content = str(doc)
            metadata = {}

        try:
            b64decode(content)
            b64.append(content)
        except:
            class TextDoc:
                def __init__(self, text_content, meta):
                    self.text = text_content
                    self.metadata = meta
            text.append(TextDoc(content, metadata))

    return {"images": b64, "texts": text}

def build_prompt(kwargs):
    docs = kwargs["context"]
    question = kwargs["question"]

    context = ""
    for text in docs["texts"]:
        source = 'unknown'
        if hasattr(text, 'metadata'):
            if isinstance(text.metadata, dict):
                source = text.metadata.get('source', 'unknown')
            elif hasattr(text.metadata, 'source'):
                source = text.metadata.source
        context += f"\n[{source}] {text.text}\n"

    prompt_content = [{
        "type": "text",
        "text": f"Answer based on context:\n{context}\n\nQuestion: {question}"
    }]

    for image in docs["images"]:
        prompt_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image}"}
        })

    return ChatPromptTemplate.from_messages([HumanMessage(content=prompt_content)])

chain = {
    "context": retriever | RunnableLambda(parse_docs),
    "question": RunnablePassthrough(),
} | RunnablePassthrough().assign(
    response=(
        RunnableLambda(build_prompt)
        | ChatOpenAI(model="gpt-4o-mini")
        | StrOutputParser()
    )
)

load_time = time.time() - start_load
print(f"✅ Sistema carregado em {load_time:.2f}s\n")

# Estatísticas do knowledge base
metadata_path = f"{persist_directory}/metadata.pkl"
if os.path.exists(metadata_path):
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    total_docs = len(metadata.get('documents', {}))
    total_chunks = 0
    total_size = 0

    for doc_info in metadata.get('documents', {}).values():
        total_chunks += doc_info.get('stats', {}).get('total_chunks', 0)
        total_size += doc_info.get('file_size', 0)

    print("📊 ESTATÍSTICAS DO KNOWLEDGE BASE")
    print(f"   Documentos: {total_docs}")
    print(f"   Chunks: {total_chunks}")
    print(f"   Tamanho total: {total_size / 1024 / 1024:.2f} MB")
    print()

# Queries de teste (ajuste conforme seu domínio)
test_queries = [
    "Quais são os principais achados?",
    "Como fazer o diagnóstico?",
    "Quais os efeitos colaterais?",
    "Qual o tratamento recomendado?",
    "Quais as indicações?",
]

print("🧪 TESTANDO PERFORMANCE COM QUERIES REAIS\n")
print("-" * 70)

latencies = []
results_count = []

for i, query in enumerate(test_queries, 1):
    print(f"\n[{i}/{len(test_queries)}] Query: {query}")

    # Medir tempo total (retrieval + rerank + LLM)
    start = time.time()

    try:
        response = chain.invoke(query)
        latency = time.time() - start

        # Contar resultados
        num_results = len(response['context']['texts'])

        # Extrair fontes
        sources = set()
        for text in response['context']['texts']:
            if hasattr(text, 'metadata'):
                if isinstance(text.metadata, dict):
                    source = text.metadata.get('source', 'unknown')
                elif hasattr(text.metadata, 'source'):
                    source = text.metadata.source
                else:
                    source = 'unknown'
                sources.add(source)

        latencies.append(latency)
        results_count.append(num_results)

        print(f"   ⏱️  Latency: {latency:.2f}s")
        print(f"   📊 Resultados rerankeados: {num_results}")
        print(f"   📄 Fontes: {', '.join(sorted(sources))}")

        # Mostrar preview da resposta
        answer_preview = response['response'][:150]
        if len(response['response']) > 150:
            answer_preview += "..."
        print(f"   💬 Resposta: {answer_preview}")

    except Exception as e:
        print(f"   ❌ ERRO: {str(e)}")
        continue

print("\n" + "-" * 70)
print("\n📈 RESUMO DOS TESTES\n")

if latencies:
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    avg_results = sum(results_count) / len(results_count)

    print(f"   Queries testadas: {len(latencies)}")
    print(f"   Latency média: {avg_latency:.2f}s")
    print(f"   Latency mínima: {min_latency:.2f}s")
    print(f"   Latency máxima: {max_latency:.2f}s")
    print(f"   Resultados médios após rerank: {avg_results:.1f}")
    print()

    # Classificação de performance
    if avg_latency < 2.0:
        print("   ✅ EXCELENTE - Sistema muito rápido!")
    elif avg_latency < 3.0:
        print("   ✅ BOM - Performance adequada para produção")
    elif avg_latency < 5.0:
        print("   ⚠️  RAZOÁVEL - Considere otimizações")
    else:
        print("   ❌ LENTO - Requer otimização urgente")

    print()

    # Recomendações baseadas em performance
    if total_chunks > 100000:
        print("   💡 RECOMENDAÇÃO: >100K chunks detectados")
        print("      Considere migrar para Weaviate ou Qdrant")
        print("      ChromaDB não tem indexação de metadata nativa\n")

    if avg_latency > 3.0 and total_chunks > 50000:
        print("   💡 RECOMENDAÇÃO: Latency alta + muitos chunks")
        print("      1. Migrar para Weaviate (melhor custo-benefício)")
        print("      2. Implementar cache de queries frequentes")
        print("      3. Considerar GPU para embeddings\n")

print("=" * 70)
print("✅ Teste concluído!")
print("=" * 70)
