#!/usr/bin/env python3
"""
Remove documento deletado do vectorstore

O documento foi deletado do metadata.pkl e docstore.pkl,
mas ainda existe no ChromaDB (vectorstore).
"""

import os
import pickle
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

PERSIST_DIR = os.getenv("PERSIST_DIR", "./knowledge")

print("=" * 80)
print("🗑️ REMOVENDO DOCUMENTO DELETADO DO VECTORSTORE")
print("=" * 80)

# 1. Verificar metadata para ver quais documentos DEVEM existir
print("\n[1/3] Verificando metadata.pkl...")

metadata_path = f"{PERSIST_DIR}/metadata.pkl"
valid_pdfs = set()

if os.path.exists(metadata_path):
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    for pdf_id, doc_info in metadata.get('documents', {}).items():
        filename = doc_info.get('filename', 'unknown')
        valid_pdfs.add(filename)
        print(f"   ✓ Documento válido: {filename}")

    print(f"\n   Total de documentos válidos: {len(valid_pdfs)}")
else:
    print("   ⚠️  metadata.pkl não encontrado!")

# 2. Verificar vectorstore para ver o que REALMENTE existe
print("\n[2/3] Verificando vectorstore...")

vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
    persist_directory=PERSIST_DIR
)

# Buscar TODOS os documentos
all_docs = vectorstore.similarity_search("", k=10000)
print(f"   Total de chunks no vectorstore: {len(all_docs)}")

# Agrupar por source
docs_by_source = {}
for doc in all_docs:
    source = doc.metadata.get('source', 'unknown')
    if source not in docs_by_source:
        docs_by_source[source] = []
    docs_by_source[source].append(doc)

print(f"\n   Documentos no vectorstore:")
for source, chunks in sorted(docs_by_source.items()):
    status = "✓ VÁLIDO" if source in valid_pdfs else "❌ DELETADO"
    print(f"      {status}: {source} ({len(chunks)} chunks)")

# 3. Remover documentos deletados
print("\n[3/3] Removendo documentos deletados...")

deleted_count = 0
for source, chunks in docs_by_source.items():
    if source not in valid_pdfs and source != 'unknown':
        print(f"\n   🗑️ Removendo: {source}")

        # Pegar IDs dos chunks a deletar
        ids_to_delete = [chunk.metadata.get('doc_id') for chunk in chunks if chunk.metadata.get('doc_id')]

        if ids_to_delete:
            print(f"      Deletando {len(ids_to_delete)} chunks...")
            try:
                vectorstore.delete(ids=ids_to_delete)
                deleted_count += len(ids_to_delete)
                print(f"      ✓ Deletado com sucesso!")
            except Exception as e:
                print(f"      ✗ Erro: {str(e)}")
        else:
            print(f"      ⚠️  Nenhum doc_id encontrado, pulando...")

print("\n" + "=" * 80)
print(f"✅ LIMPEZA CONCLUÍDA")
print(f"   Chunks deletados: {deleted_count}")
print("=" * 80)

if deleted_count > 0:
    print("\n⚠️  IMPORTANTE: Limpe o cache do retriever!")
    print("   curl -X POST https://seu-app.railway.app/clear-cache")
    print()
