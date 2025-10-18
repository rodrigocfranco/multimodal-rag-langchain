#!/usr/bin/env python3
"""
Test MultiVectorRetriever to diagnose why it returns 0 docs
"""

import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.storage import InMemoryStore
from langchain.retrievers.multi_vector import MultiVectorRetriever
import pickle

load_dotenv()

persist_directory = os.getenv("PERSIST_DIR", "./knowledge")

print("=" * 70)
print("🔍 TESTING MultiVectorRetriever")
print("=" * 70)

# 1. Load vectorstore
print("\n1️⃣ Loading vectorstore...")
vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
    persist_directory=persist_directory
)

collection = vectorstore._collection
count = collection.count()
print(f"   ✅ ChromaDB: {count} embeddings")

# 2. Test direct similarity_search
print("\n2️⃣ Testing direct similarity_search...")
test_query = "diabetes"
direct_results = vectorstore.similarity_search(test_query, k=5)
print(f"   ✅ Direct search returned: {len(direct_results)} results")

if direct_results:
    print(f"\n   First result:")
    print(f"     Content: {direct_results[0].page_content[:100]}...")
    print(f"     Metadata: {direct_results[0].metadata}")
    print(f"     doc_id in metadata: {'doc_id' in direct_results[0].metadata}")
    if 'doc_id' in direct_results[0].metadata:
        print(f"     doc_id value: {direct_results[0].metadata['doc_id']}")

# 3. Load docstore
print("\n3️⃣ Loading docstore...")
docstore_path = f"{persist_directory}/docstore.pkl"
store = InMemoryStore()

if os.path.exists(docstore_path):
    with open(docstore_path, 'rb') as f:
        store.store = pickle.load(f)
    print(f"   ✅ Docstore: {len(store.store)} documents")

    # Show sample keys
    sample_keys = list(store.store.keys())[:5]
    print(f"\n   Sample docstore keys:")
    for key in sample_keys:
        print(f"     - {key}")
else:
    print(f"   ❌ Docstore not found at {docstore_path}")
    exit(1)

# 4. Check doc_id mapping
print("\n4️⃣ Checking doc_id mapping...")
if direct_results:
    vectorstore_doc_ids = [r.metadata.get('doc_id', 'NO_DOC_ID') for r in direct_results]
    print(f"\n   doc_ids from vectorstore results:")
    for doc_id in vectorstore_doc_ids:
        exists = doc_id in store.store
        status = "✅" if exists else "❌"
        print(f"     {status} {doc_id} - {'EXISTS in docstore' if exists else 'NOT FOUND in docstore'}")

# 5. Create MultiVectorRetriever
print("\n5️⃣ Creating MultiVectorRetriever...")
retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key="doc_id",
    search_kwargs={"k": 5}
)
print(f"   ✅ Created with id_key='doc_id'")

# 6. Test MultiVectorRetriever
print("\n6️⃣ Testing MultiVectorRetriever.invoke()...")
try:
    mv_results = retriever.invoke(test_query)
    print(f"   ✅ MultiVectorRetriever returned: {len(mv_results)} results")

    if len(mv_results) == 0:
        print(f"\n   ❌ PROBLEM: MultiVectorRetriever returned 0 results!")
        print(f"      But direct similarity_search returned {len(direct_results)} results")
        print(f"\n   🔍 DIAGNOSIS:")
        print(f"      - Vectorstore has data ✅")
        print(f"      - Docstore has data ✅")
        print(f"      - Direct search works ✅")
        print(f"      - MultiVectorRetriever fails ❌")
        print(f"\n   🎯 POSSIBLE CAUSES:")
        print(f"      1. doc_id in vectorstore metadata doesn't match docstore keys")
        print(f"      2. id_key parameter is wrong (should be 'doc_id')")
        print(f"      3. Docstore doesn't have the doc_ids that vectorstore returned")
    else:
        print(f"\n   ✅ SUCCESS: MultiVectorRetriever is working!")
        print(f"\n   First result:")
        first = mv_results[0]
        print(f"     Type: {type(first).__name__}")
        if hasattr(first, 'page_content'):
            print(f"     Content: {first.page_content[:100]}...")
        elif hasattr(first, 'text'):
            print(f"     Content: {first.text[:100]}...")
        else:
            print(f"     Content: {str(first)[:100]}...")

except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    print(f"\n   Traceback:")
    traceback.print_exc()

print("\n" + "=" * 70)
print("🏁 Test complete")
print("=" * 70)
