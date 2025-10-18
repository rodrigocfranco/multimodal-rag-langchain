#!/usr/bin/env python3
"""
Deletar PDF do knowledge base
"""

import os
import pickle
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.storage import InMemoryStore

load_dotenv()

persist_directory = os.getenv("PERSIST_DIR", "./knowledge")
pdf_id_to_delete = "24516e7262a0fde602e9e935ebc5dda47a6e66085574509b6f8ee3172bbd7ab2"

print("=" * 70)
print("🗑️  DELETANDO PDF DO KNOWLEDGE BASE")
print("=" * 70)
print(f"\nPDF ID: {pdf_id_to_delete}")
print(f"Persist directory: {persist_directory}\n")

# 1. Load vectorstore
print("1️⃣ Loading vectorstore...")
vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
    persist_directory=persist_directory
)

# 2. Load docstore
print("2️⃣ Loading docstore...")
docstore_path = f"{persist_directory}/docstore.pkl"
store = InMemoryStore()

if os.path.exists(docstore_path):
    with open(docstore_path, 'rb') as f:
        store.store = pickle.load(f)
    print(f"   ✅ Docstore loaded: {len(store.store)} documents")
else:
    print(f"   ❌ Docstore not found")
    exit(1)

# 3. Find all doc_ids for this PDF
print(f"\n3️⃣ Finding chunks for PDF {pdf_id_to_delete[:16]}...")
doc_ids_to_delete = []

for doc_id, doc in store.store.items():
    # Extract metadata
    metadata = {}
    if hasattr(doc, 'metadata'):
        metadata = doc.metadata

    # Check if this doc belongs to the PDF
    if metadata.get('pdf_id') == pdf_id_to_delete:
        doc_ids_to_delete.append(doc_id)

print(f"   ✅ Found {len(doc_ids_to_delete)} chunks to delete")

if len(doc_ids_to_delete) == 0:
    print(f"\n⚠️  No chunks found for this PDF ID")
    exit(0)

# 4. Delete from docstore
print(f"\n4️⃣ Deleting from docstore...")
for doc_id in doc_ids_to_delete:
    if doc_id in store.store:
        del store.store[doc_id]
print(f"   ✅ Deleted {len(doc_ids_to_delete)} documents from docstore")

# 5. Delete from vectorstore
print(f"\n5️⃣ Deleting from vectorstore...")
try:
    vectorstore._collection.delete(
        where={"pdf_id": pdf_id_to_delete}
    )
    print(f"   ✅ Deleted vectors for PDF from ChromaDB")
except Exception as e:
    print(f"   ❌ Error deleting from vectorstore: {e}")

# 6. Save docstore
print(f"\n6️⃣ Saving updated docstore...")
with open(docstore_path, 'wb') as f:
    pickle.dump(store.store, f)
print(f"   ✅ Docstore saved: {len(store.store)} documents remaining")

# 7. Verify
print(f"\n7️⃣ Verifying deletion...")
collection = vectorstore._collection
remaining_count = collection.count()
print(f"   ✅ ChromaDB now has: {remaining_count} embeddings")
print(f"   ✅ Docstore now has: {len(store.store)} documents")

print("\n" + "=" * 70)
print("✅ PDF DELETED SUCCESSFULLY")
print("=" * 70)
print("\nYou can now re-upload the PDF with better table extraction.")
print()
