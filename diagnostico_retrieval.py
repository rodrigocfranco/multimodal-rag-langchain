#!/usr/bin/env python3
"""
Diagnóstico do Retrieval - Identifica problemas no pipeline
"""

import os
import pickle
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.storage import InMemoryStore
from langchain.retrievers.multi_vector import MultiVectorRetriever

load_dotenv()

persist_directory = "./knowledge_base"

print("=" * 70)
print("🔍 DIAGNÓSTICO DO RETRIEVAL")
print("=" * 70)

# 1. Verificar arquivos
print("\n1️⃣ Verificando arquivos...")
docstore_path = f"{persist_directory}/docstore.pkl"
metadata_path = f"{persist_directory}/metadata.pkl"

if os.path.exists(docstore_path):
    size_mb = os.path.getsize(docstore_path) / (1024 * 1024)
    print(f"✅ docstore.pkl: {size_mb:.1f} MB")
else:
    print("❌ docstore.pkl não encontrado")

if os.path.exists(metadata_path):
    print(f"✅ metadata.pkl: {os.path.getsize(metadata_path)} bytes")
else:
    print("❌ metadata.pkl não encontrado")

# 2. Carregar ChromaDB
print("\n2️⃣ Carregando ChromaDB...")
try:
    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
        persist_directory=persist_directory
    )

    # Contar embeddings
    collection = vectorstore._collection
    count = collection.count()
    print(f"✅ ChromaDB carregado: {count} embeddings")

except Exception as e:
    print(f"❌ Erro ao carregar ChromaDB: {e}")
    exit(1)

# 3. Carregar docstore
print("\n3️⃣ Carregando docstore...")
store = InMemoryStore()
try:
    with open(docstore_path, 'rb') as f:
        store.store = pickle.load(f)

    print(f"✅ Docstore carregado: {len(store.store)} documentos completos")

    # Analisar tipos
    types_count = {}
    for doc in list(store.store.values())[:100]:  # Sample de 100
        doc_type = type(doc).__name__
        types_count[doc_type] = types_count.get(doc_type, 0) + 1

    print("\n   Tipos de documentos no docstore:")
    for doc_type, count in types_count.items():
        print(f"     - {doc_type}: {count}")

except Exception as e:
    print(f"❌ Erro ao carregar docstore: {e}")
    exit(1)

# 4. Testar retrieval básico
print("\n4️⃣ Testando retrieval básico (sem rerank)...")

base_retriever = MultiVectorRetriever(
    vectorstore=vectorstore,
    docstore=store,
    id_key="doc_id",
    search_kwargs={"k": 30}
)

# Perguntas de teste
test_queries = [
    "Liste todos os iSGLT2 mencionados no documento",
    "Quais os efeitos adversos da metformina",
    "Quando NÃO usar metformina",
]

for query in test_queries:
    print(f"\n📝 Query: {query}")

    try:
        # Buscar sem rerank
        docs = base_retriever.invoke(query)
        print(f"   ✅ Retornou {len(docs)} documentos")

        # Analisar conteúdo
        if len(docs) > 0:
            first_doc = docs[0]

            # Detectar tipo
            if hasattr(first_doc, 'text'):
                content = first_doc.text[:150]
                print(f"   📄 Tipo: {type(first_doc).__name__}")
                print(f"   📄 Preview: {content}...")
            elif hasattr(first_doc, 'page_content'):
                content = first_doc.page_content[:150]
                print(f"   📄 Tipo: Document")
                print(f"   📄 Preview: {content}...")
            else:
                print(f"   ⚠️  Tipo desconhecido: {type(first_doc).__name__}")

            # Verificar se contém keywords relevantes
            content_lower = content.lower()

            if query.lower().startswith("liste todos os isglt2"):
                keywords = ["dapagliflozina", "empagliflozina", "canagliflozina", "isglt2", "sglt2"]
                found = [kw for kw in keywords if kw in content_lower]
                if found:
                    print(f"   ✅ Encontrou keywords: {found}")
                else:
                    print(f"   ⚠️  NÃO encontrou keywords relevantes para iSGLT2")

            elif "efeitos adversos" in query.lower():
                keywords = ["náusea", "vômito", "diarreia", "efeito", "adverso"]
                found = [kw for kw in keywords if kw in content_lower]
                if found:
                    print(f"   ✅ Encontrou keywords: {found}")
                else:
                    print(f"   ⚠️  NÃO encontrou keywords sobre efeitos adversos")

            elif "não usar" in query.lower():
                keywords = ["contraindicação", "evitar", "não", "tfg"]
                found = [kw for kw in keywords if kw in content_lower]
                if found:
                    print(f"   ✅ Encontrou keywords: {found}")
                else:
                    print(f"   ⚠️  NÃO encontrou keywords sobre contraindicações")
        else:
            print("   ❌ Nenhum documento retornado!")

    except Exception as e:
        print(f"   ❌ Erro: {e}")

# 5. Análise de embeddings
print("\n5️⃣ Analisando qualidade dos embeddings...")

# Testar similaridade
test_pairs = [
    ("metformina", "biguanida"),
    ("iSGLT2", "inibidor SGLT2"),
    ("diabetes", "glicemia"),
]

embeddings_func = OpenAIEmbeddings(model="text-embedding-3-large")

print("\nTeste de similaridade:")
for term1, term2 in test_pairs:
    emb1 = embeddings_func.embed_query(term1)
    emb2 = embeddings_func.embed_query(term2)

    # Cosine similarity
    import numpy as np
    similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    print(f"   '{term1}' ↔ '{term2}': {similarity:.3f}")

# 6. Recomendações
print("\n" + "=" * 70)
print("📊 DIAGNÓSTICO COMPLETO")
print("=" * 70)

print(f"""
✅ Embeddings: {count}
✅ Documentos completos: {len(store.store)}

⚠️  POSSÍVEIS PROBLEMAS IDENTIFICADOS:

1. Se retrieval retornar poucos docs (<10):
   → Problema: Embeddings não estão capturando semântica
   → Solução: Re-processar PDFs com chunks maiores

2. Se keywords não aparecem nos primeiros docs:
   → Problema: Ranking ruim do vectorstore
   → Solução: Aumentar k ainda mais (30→40) ou usar BM25

3. Se docs retornados são do tipo errado:
   → Problema: Conversão de objetos Unstructured falhou
   → Solução: Revisar DocumentConverter

4. Se similaridade entre termos relacionados <0.7:
   → Problema: Modelo de embedding fraco
   → Solução: Testar text-embedding-3-large

🎯 PRÓXIMOS PASSOS:
- Revisar output acima
- Identificar qual problema ocorre
- Aplicar solução específica
""")
