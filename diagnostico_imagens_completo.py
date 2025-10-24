#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO COMPLETO DO SISTEMA DE IMAGENS
Verifica todo o fluxo: extração → armazenamento → retrieval → visualização

Data: 2025-10-22
"""

import os
import pickle
from dotenv import load_dotenv
from base64 import b64decode

load_dotenv()

PERSIST_DIR = os.getenv("PERSIST_DIR", "./knowledge")

print("=" * 80)
print("🔍 DIAGNÓSTICO COMPLETO DO SISTEMA DE IMAGENS")
print("=" * 80)

# ===========================================================================
# 1. VERIFICAR ESTRUTURA DE ARQUIVOS
# ===========================================================================
print("\n📁 [1/6] Verificando estrutura de arquivos...")

files_check = {
    "docstore.pkl": os.path.exists(f"{PERSIST_DIR}/docstore.pkl"),
    "metadata.pkl": os.path.exists(f"{PERSIST_DIR}/metadata.pkl"),
    "chroma.sqlite3": os.path.exists(f"{PERSIST_DIR}/chroma.sqlite3"),
}

for filename, exists in files_check.items():
    status = "✓" if exists else "✗"
    print(f"   {status} {filename}: {'EXISTE' if exists else 'NÃO ENCONTRADO'}")

if not files_check["docstore.pkl"]:
    print("\n❌ PROBLEMA CRÍTICO: docstore.pkl não existe!")
    print("   → Imagens são armazenadas no docstore")
    print("   → Sem docstore, não há como recuperar imagens")
    print("\n💡 SOLUÇÃO: Processar um PDF com imagens usando adicionar_pdf.py")
    exit(1)

# ===========================================================================
# 2. ANALISAR METADATA.PKL
# ===========================================================================
print("\n📊 [2/6] Analisando metadata.pkl...")

if files_check["metadata.pkl"]:
    with open(f"{PERSIST_DIR}/metadata.pkl", 'rb') as f:
        metadata = pickle.load(f)

    total_docs = len(metadata.get('documents', {}))
    print(f"   ✓ Documentos processados: {total_docs}")

    for pdf_id, doc_info in metadata.get('documents', {}).items():
        filename = doc_info.get('filename', 'unknown')
        stats = doc_info.get('stats', {})

        print(f"\n   📄 {filename}")
        print(f"      Textos: {stats.get('texts', 0)}")
        print(f"      Tabelas: {stats.get('tables', 0)}")
        print(f"      Imagens: {stats.get('images', 0)}")
        print(f"      Total chunks: {stats.get('total_chunks', 0)}")

        if stats.get('images', 0) == 0:
            print(f"      ⚠️  ALERTA: Nenhuma imagem detectada neste PDF")
else:
    print("   ✗ metadata.pkl não encontrado!")

# ===========================================================================
# 3. ANALISAR DOCSTORE
# ===========================================================================
print("\n🗄️ [3/6] Analisando docstore.pkl...")

with open(f"{PERSIST_DIR}/docstore.pkl", 'rb') as f:
    docstore = pickle.load(f)

print(f"   ✓ Total de entradas no docstore: {len(docstore)}")

# Contar tipos de conteúdo
image_count = 0
text_count = 0
table_count = 0
unknown_count = 0

for doc_id, content in docstore.items():
    # Tentar identificar tipo
    if isinstance(content, str):
        # String: pode ser imagem base64 ou texto
        try:
            # Tentar decodificar como base64
            decoded = b64decode(content[:100])  # Testar primeiros 100 chars
            # Se decodificou, verificar se é imagem (magic bytes)
            if decoded.startswith(b'\xff\xd8\xff') or decoded.startswith(b'\x89PNG'):
                image_count += 1
            else:
                # Base64 válido mas não é imagem
                unknown_count += 1
        except:
            # Não é base64, é texto
            text_count += 1
    elif hasattr(content, 'text'):
        # Objeto Unstructured (Table ou CompositeElement)
        type_name = type(content).__name__
        if 'Table' in type_name:
            table_count += 1
        else:
            text_count += 1
    else:
        unknown_count += 1

print(f"\n   Distribuição de conteúdo:")
print(f"      Imagens (base64): {image_count}")
print(f"      Textos: {text_count}")
print(f"      Tabelas: {table_count}")
print(f"      Desconhecido: {unknown_count}")

if image_count == 0:
    print(f"\n   ❌ PROBLEMA: Nenhuma imagem encontrada no docstore!")
    print(f"      → Imagens não foram armazenadas durante o processamento")
    print(f"      → Verificar se MIN_IMAGE_SIZE_KB está muito alto")
    print(f"      → Verificar se PDFs realmente contêm imagens")

# ===========================================================================
# 4. VERIFICAR VECTORSTORE (ChromaDB)
# ===========================================================================
print("\n🔎 [4/6] Verificando vectorstore (ChromaDB)...")

try:
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
        persist_directory=PERSIST_DIR
    )

    # Buscar TODAS as imagens (filtro por metadata)
    all_images = vectorstore.similarity_search(
        "",
        k=1000,
        filter={"type": "image"}
    )

    print(f"   ✓ Imagens no vectorstore: {len(all_images)}")

    if len(all_images) == 0:
        print(f"\n   ❌ PROBLEMA: Nenhuma imagem no vectorstore!")
        print(f"      → Embeddings de imagens não foram criados")
        print(f"      → Verificar código em adicionar_pdf.py (linhas 1143-1176)")

        # Verificar se há ALGUM documento no vectorstore
        all_docs = vectorstore.similarity_search("", k=10)
        print(f"\n   Total de documentos no vectorstore: {len(all_docs)}")

        if len(all_docs) > 0:
            # Contar tipos
            types = {}
            for doc in all_docs:
                doc_type = doc.metadata.get('type', 'unknown')
                types[doc_type] = types.get(doc_type, 0) + 1

            print(f"   Distribuição por tipo:")
            for t, count in types.items():
                print(f"      {t}: {count}")
    else:
        print(f"   ✓ Imagens encontradas no vectorstore!")

        # Mostrar sample
        print(f"\n   Amostra de imagens:")
        for i, img in enumerate(all_images[:3], 1):
            print(f"      [{i}] Source: {img.metadata.get('source', 'unknown')}")
            print(f"          Doc ID: {img.metadata.get('doc_id', 'N/A')}")
            print(f"          Summary: {img.page_content[:100]}...")

except Exception as e:
    print(f"   ✗ Erro ao acessar vectorstore: {str(e)}")

# ===========================================================================
# 5. TESTAR RETRIEVAL DE IMAGENS
# ===========================================================================
print("\n🔄 [5/6] Testando retrieval de imagens...")

try:
    from langchain.retrievers.multi_vector import MultiVectorRetriever
    from langchain.storage import InMemoryStore

    store = InMemoryStore()
    with open(f"{PERSIST_DIR}/docstore.pkl", 'rb') as f:
        store.store = pickle.load(f)

    retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key="doc_id",
        search_kwargs={"k": 10}
    )

    # Tentar buscar imagens com query específica
    test_query = "fluxograma figura algoritmo gráfico imagem"
    results = retriever.invoke(test_query)

    print(f"   ✓ Query de teste: '{test_query}'")
    print(f"   ✓ Resultados retornados: {len(results)}")

    # Analisar resultados
    images_in_results = 0
    for doc in results:
        # Verificar se é imagem (base64)
        if isinstance(doc, str):
            try:
                b64decode(doc[:100])
                images_in_results += 1
            except:
                pass

    print(f"   ✓ Imagens nos resultados: {images_in_results}")

    if images_in_results == 0 and len(all_images) > 0:
        print(f"\n   ⚠️  ALERTA: Imagens existem mas não foram recuperadas!")
        print(f"      → Problema no retrieval (match ruim entre query e embeddings)")
        print(f"      → Testar query mais específica baseada no conteúdo do PDF")

except Exception as e:
    print(f"   ✗ Erro no teste de retrieval: {str(e)}")

# ===========================================================================
# 6. VERIFICAR CONFIGURAÇÕES
# ===========================================================================
print("\n⚙️  [6/6] Verificando configurações...")

min_image_size = float(os.getenv("MIN_IMAGE_SIZE_KB", "10"))
print(f"   MIN_IMAGE_SIZE_KB: {min_image_size}KB")

if min_image_size > 30:
    print(f"   ⚠️  ALERTA: Threshold muito alto! Fluxogramas podem ser filtrados.")
    print(f"   💡 RECOMENDAÇÃO: Usar MIN_IMAGE_SIZE_KB=10 (valor atual do código)")

print(f"\n   DEBUG_IMAGES: {os.getenv('DEBUG_IMAGES', 'not set')}")
print(f"   PERSIST_DIR: {PERSIST_DIR}")

# ===========================================================================
# DIAGNÓSTICO FINAL
# ===========================================================================
print("\n" + "=" * 80)
print("📋 DIAGNÓSTICO FINAL")
print("=" * 80)

issues = []

if image_count == 0:
    issues.append("❌ Nenhuma imagem no docstore (não foram armazenadas)")

if len(all_images) == 0:
    issues.append("❌ Nenhuma imagem no vectorstore (embeddings não criados)")

if image_count > 0 and len(all_images) == 0:
    issues.append("⚠️  Imagens no docstore MAS não no vectorstore (bug no processamento)")

if len(all_images) > 0 and images_in_results == 0:
    issues.append("⚠️  Imagens no vectorstore MAS não sendo recuperadas (retrieval ruim)")

if not issues:
    print("\n✅ SISTEMA FUNCIONANDO CORRETAMENTE!")
    print(f"   • {image_count} imagens no docstore")
    print(f"   • {len(all_images)} imagens no vectorstore")
    print(f"   • {images_in_results} imagens recuperadas em teste")
else:
    print("\n❌ PROBLEMAS DETECTADOS:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")

    print("\n💡 PRÓXIMOS PASSOS:")
    if image_count == 0:
        print("   1. Verificar se PDFs realmente têm imagens (abrir manualmente)")
        print("   2. Processar um PDF COM IMAGENS usando:")
        print("      python adicionar_pdf.py <arquivo_com_imagens.pdf>")
        print("   3. Verificar logs durante processamento (procurar por 'imagens')")
    elif len(all_images) == 0:
        print("   1. Bug no código de adicionar_pdf.py (linhas 1143-1176)")
        print("   2. Imagens não estão sendo adicionadas ao vectorstore")
        print("   3. Verificar se doc_id está sendo passado corretamente")
    elif images_in_results == 0:
        print("   1. Melhorar descrições das imagens (GPT-4o Vision)")
        print("   2. Adicionar contexto mais rico aos embeddings")
        print("   3. Testar queries mais específicas")

print("\n" + "=" * 80)
print()
