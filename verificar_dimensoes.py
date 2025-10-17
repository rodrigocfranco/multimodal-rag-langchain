#!/usr/bin/env python3
"""
Verificar dimensões de embeddings no ChromaDB existente
Diagnostica incompatibilidade de dimensões após upgrade do modelo
"""

import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

persist_directory = "./knowledge_base"

print("=" * 70)
print("🔍 DIAGNÓSTICO: Dimensões de Embeddings")
print("=" * 70)

# Verificar se knowledge_base existe
if not os.path.exists(persist_directory):
    print("\n✅ Knowledge base vazio - não há problema de compatibilidade")
    print("   Pode processar PDFs normalmente com o novo modelo.\n")
    exit(0)

print("\n1️⃣ Verificando modelo ANTIGO (text-embedding-ada-002)...")
try:
    vectorstore_old = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(model="text-embedding-ada-002"),
        persist_directory=persist_directory
    )
    collection_old = vectorstore_old._collection
    count_old = collection_old.count()

    if count_old > 0:
        # Pegar um embedding de exemplo
        sample = collection_old.get(limit=1, include=['embeddings'])
        if sample and sample.get('embeddings'):
            dim_old = len(sample['embeddings'][0])
            print(f"   ✅ ChromaDB existente detectado")
            print(f"      Embeddings: {count_old}")
            print(f"      Dimensões: {dim_old} (text-embedding-ada-002)")
        else:
            print(f"   ⚠️  ChromaDB tem {count_old} docs mas sem embeddings detectados")
    else:
        print(f"   ✅ ChromaDB vazio")
        dim_old = None
except Exception as e:
    print(f"   ❌ Erro ao verificar modelo antigo: {e}")
    dim_old = None

print("\n2️⃣ Verificando modelo NOVO (text-embedding-3-large)...")
try:
    # Testar dimensão do novo modelo
    new_embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    test_embedding = new_embeddings.embed_query("teste")
    dim_new = len(test_embedding)
    print(f"   ✅ Novo modelo funciona")
    print(f"      Dimensões: {dim_new} (text-embedding-3-large)")
except Exception as e:
    print(f"   ❌ Erro ao testar novo modelo: {e}")
    dim_new = None

print("\n" + "=" * 70)
print("📊 DIAGNÓSTICO")
print("=" * 70)

if dim_old and dim_new:
    if dim_old == dim_new:
        print("\n✅ COMPATÍVEL: Dimensões iguais")
        print(f"   Antigo: {dim_old}, Novo: {dim_new}")
        print("\n   Pode processar PDFs normalmente.\n")
    else:
        print("\n❌ INCOMPATÍVEL: Dimensões diferentes!")
        print(f"   Antigo: {dim_old} dimensões (text-embedding-ada-002)")
        print(f"   Novo: {dim_new} dimensões (text-embedding-3-large)")
        print("\n🔧 SOLUÇÃO:")
        print("   Para usar o novo modelo (3-large), você precisa:")
        print("   1. Deletar knowledge base antigo:")
        print("      rm -rf ./knowledge_base")
        print("   2. Re-processar PDFs com o novo modelo")
        print("\n⚠️  AVISO:")
        print("   - Isso APAGARÁ todos documentos processados")
        print("   - Você precisará fazer upload dos PDFs novamente")
        print("   - O novo modelo é MELHOR (+30% qualidade)")
        print("\n💡 ALTERNATIVA (não recomendada):")
        print("   - Reverter para ada-002 editando consultar_com_rerank.py")
        print("   - Mas perderá +30% de qualidade do retrieval\n")
elif dim_old is None and dim_new:
    print("\n✅ Knowledge base vazio - sem problemas")
    print(f"   Novo modelo pronto: {dim_new} dimensões")
    print("\n   Pode processar PDFs normalmente.\n")
elif dim_old and dim_new is None:
    print("\n⚠️  Novo modelo não funciona")
    print("   Verifique OPENAI_API_KEY no .env\n")
else:
    print("\n❌ Não foi possível diagnosticar")
    print("   Verifique configuração do ambiente\n")
