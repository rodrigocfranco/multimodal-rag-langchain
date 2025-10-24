#!/usr/bin/env python3
"""
Verifica integridade de um documento processado no knowledge base
"""

import os
import pickle
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

PERSIST_DIR = os.getenv("PERSIST_DIR", "./knowledge")
PDF_ID = "38d1b6f3c5244470"  # ID do documento em questão

print("🔍 VERIFICANDO INTEGRIDADE DO DOCUMENTO")
print("=" * 70)

# 1. Verificar metadata.pkl
print("\n1️⃣ Verificando metadata.pkl...")
metadata_path = f"{PERSIST_DIR}/metadata.pkl"
if os.path.exists(metadata_path):
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    if PDF_ID in metadata.get('documents', {}):
        doc_info = metadata['documents'][PDF_ID]
        print(f"   ✓ Documento encontrado em metadata.pkl")
        print(f"   Filename: {doc_info['filename']}")
        print(f"   Status: {doc_info['status']}")
        print(f"   Chunks totais: {doc_info['stats']['total_chunks']}")
        print(f"   - Textos: {doc_info['stats']['texts']}")
        print(f"   - Tabelas: {doc_info['stats']['tables']}")
        print(f"   - Imagens: {doc_info['stats']['images']}")
        print(f"   Processado em: {doc_info['processed_at']}")

        expected_chunks = doc_info['stats']['total_chunks']
        chunk_ids = doc_info.get('chunk_ids', [])
        print(f"   Chunk IDs salvos: {len(chunk_ids)}")
    else:
        print(f"   ❌ Documento NÃO encontrado em metadata.pkl!")
        exit(1)
else:
    print(f"   ❌ metadata.pkl não existe!")
    exit(1)

# 2. Verificar vectorstore (ChromaDB)
print("\n2️⃣ Verificando vectorstore (ChromaDB)...")
vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
    persist_directory=PERSIST_DIR
)

# Buscar documentos do PDF_ID
results = vectorstore.similarity_search(
    "",  # Query vazia para pegar qualquer coisa
    k=100,
    filter={"pdf_id": PDF_ID}
)

print(f"   ✓ Documentos no vectorstore: {len(results)}")
print(f"   Esperado: {expected_chunks}")

if len(results) == expected_chunks:
    print(f"   ✅ COMPLETO: Todos os {expected_chunks} chunks estão no vectorstore!")
elif len(results) < expected_chunks:
    print(f"   ⚠️  INCOMPLETO: Faltam {expected_chunks - len(results)} chunks!")
    print(f"   Processamento pode ter sido interrompido antes de completar.")
else:
    print(f"   ⚠️  ESTRANHO: Mais chunks do que esperado!")

# 3. Verificar tipos de chunks
print("\n3️⃣ Analisando tipos de chunks...")
types_count = {}
for doc in results:
    doc_type = doc.metadata.get('type', 'unknown')
    types_count[doc_type] = types_count.get(doc_type, 0) + 1

print(f"   Distribuição:")
for dtype, count in types_count.items():
    print(f"   - {dtype}: {count}")

# 4. Verificar metadados enriquecidos
print("\n4️⃣ Verificando metadados enriquecidos...")
with_keywords = 0
with_entities = 0
with_measurements = 0

for doc in results[:5]:  # Amostrar primeiros 5
    if doc.metadata.get('keywords_str'):
        with_keywords += 1
    if doc.metadata.get('entities_diseases_str') or doc.metadata.get('entities_medications_str'):
        with_entities += 1
    if doc.metadata.get('measurements_count', 0) > 0:
        with_measurements += 1

print(f"   Amostra de 5 documentos:")
print(f"   - Com keywords: {with_keywords}/5")
print(f"   - Com entidades médicas: {with_entities}/5")
print(f"   - Com medições: {with_measurements}/5")

# 5. Verificar docstore.pkl
print("\n5️⃣ Verificando docstore.pkl...")
docstore_path = f"{PERSIST_DIR}/docstore.pkl"
if os.path.exists(docstore_path):
    with open(docstore_path, 'rb') as f:
        docstore = pickle.load(f)

    # Contar documentos no docstore que pertencem a este PDF
    matching_docs = 0
    for chunk_id in chunk_ids:
        if chunk_id in docstore:
            matching_docs += 1

    print(f"   ✓ Documentos originais no docstore: {matching_docs}/{len(chunk_ids)}")

    if matching_docs == len(chunk_ids):
        print(f"   ✅ COMPLETO: Todos os documentos originais salvos!")
    else:
        print(f"   ⚠️  INCOMPLETO: Faltam {len(chunk_ids) - matching_docs} docs originais!")
else:
    print(f"   ❌ docstore.pkl não existe!")

# VEREDICTO FINAL
print("\n" + "=" * 70)
print("📊 VEREDICTO FINAL")
print("=" * 70)

if len(results) == expected_chunks and matching_docs == len(chunk_ids):
    print("✅ DOCUMENTO COMPLETO E ÍNTEGRO")
    print("   O processamento foi concluído com sucesso.")
    print("   Você pode confiar neste documento!")
elif len(results) >= expected_chunks * 0.8:
    print("⚠️  DOCUMENTO PARCIALMENTE COMPLETO")
    print(f"   {len(results)}/{expected_chunks} chunks presentes ({len(results)/expected_chunks*100:.0f}%)")
    print("   Recomendação: Reprocessar para garantir completude.")
else:
    print("❌ DOCUMENTO INCOMPLETO")
    print(f"   Apenas {len(results)}/{expected_chunks} chunks presentes")
    print("   AÇÃO NECESSÁRIA: Deletar e reprocessar o documento!")

print()
