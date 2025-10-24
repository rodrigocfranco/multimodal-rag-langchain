#!/usr/bin/env python3
"""
🖼️ VISUALIZADOR DE IMAGENS PROCESSADAS

Mostra as imagens que estão no vectorstore e suas descrições do GPT-4o Vision

Data: 2025-10-22
"""

import os
import pickle
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from base64 import b64decode
from PIL import Image
import io

load_dotenv()

PERSIST_DIR = os.getenv("PERSIST_DIR", "./knowledge")

print("=" * 80)
print("🖼️ VISUALIZADOR DE IMAGENS PROCESSADAS")
print("=" * 80)

# Inicializar vectorstore
print("\n🔧 Carregando vectorstore...")
vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
    persist_directory=PERSIST_DIR
)
print("✓ Vectorstore carregado!")

# Buscar TODAS as imagens
print("\n🔍 Buscando todas as imagens no vectorstore...")
all_images = vectorstore.similarity_search(
    "",  # Query vazia para pegar tudo
    k=1000,  # Número grande
    filter={"type": "image"}
)

print(f"✓ Encontradas {len(all_images)} imagens no total\n")

if len(all_images) == 0:
    print("❌ Nenhuma imagem encontrada no vectorstore!")
    exit(1)

# Agrupar por PDF
images_by_pdf = {}
for img in all_images:
    source = img.metadata.get('source', 'Unknown')
    if source not in images_by_pdf:
        images_by_pdf[source] = []
    images_by_pdf[source].append(img)

# Mostrar resumo
print("=" * 80)
print("📊 RESUMO POR DOCUMENTO")
print("=" * 80)
for source, imgs in sorted(images_by_pdf.items()):
    print(f"\n📄 {source}")
    print(f"   Imagens: {len(imgs)}")

# Perguntar qual documento visualizar
print("\n" + "=" * 80)
print("🎯 VISUALIZAÇÃO DETALHADA")
print("=" * 80)

# Focar em documentos de hiperglicemia
hiperglicemia_docs = {k: v for k, v in images_by_pdf.items() if 'hiperglicemia' in k.lower() or 'diabetes' in k.lower()}

if not hiperglicemia_docs:
    print("\n⚠️ Nenhum documento de hiperglicemia encontrado!")
    print("Documentos disponíveis:")
    for i, source in enumerate(sorted(images_by_pdf.keys()), 1):
        print(f"   [{i}] {source}")
    exit(0)

print("\nDocumentos de hiperglicemia/diabetes encontrados:")
for i, (source, imgs) in enumerate(sorted(hiperglicemia_docs.items()), 1):
    print(f"   [{i}] {source} ({len(imgs)} imagens)")

# Carregar docstore para ver imagens originais
print("\n🔧 Carregando docstore (imagens originais em base64)...")
docstore_path = f"{PERSIST_DIR}/docstore.pkl"
if os.path.exists(docstore_path):
    with open(docstore_path, 'rb') as f:
        docstore = pickle.load(f)
    print(f"✓ Docstore carregado ({len(docstore)} documentos)")
else:
    print("❌ Docstore não encontrado!")
    docstore = {}

# Mostrar detalhes de cada imagem
print("\n" + "=" * 80)
print("🔍 DETALHES DAS IMAGENS")
print("=" * 80)

for source, imgs in sorted(hiperglicemia_docs.items()):
    print(f"\n{'=' * 80}")
    print(f"📄 DOCUMENTO: {source}")
    print(f"{'=' * 80}\n")

    for i, img_doc in enumerate(imgs, 1):
        print(f"[IMAGEM {i}/{len(imgs)}]")
        print(f"   Doc ID: {img_doc.metadata.get('doc_id', 'N/A')}")
        print(f"   Índice: {img_doc.metadata.get('index', 'N/A')}")
        print(f"   Página: {img_doc.metadata.get('page_number', 'N/A')}")

        # Descrição (GPT-4o Vision)
        summary = img_doc.metadata.get('summary', img_doc.page_content[:500])
        print(f"\n   📝 DESCRIÇÃO (GPT-4o Vision):")
        print(f"   {'-' * 76}")
        # Remover contexto se houver
        if '[CONTEXTO]' in summary:
            parts = summary.split('[CONTEÚDO]')
            if len(parts) > 1:
                summary = parts[1].strip()

        # Mostrar descrição (primeiras linhas)
        lines = summary.split('\n')
        for line in lines[:10]:  # Primeiras 10 linhas
            print(f"   {line}")
        if len(lines) > 10:
            print(f"   ... ({len(lines) - 10} linhas adicionais)")
        print(f"   {'-' * 76}")

        # Verificar se tem a imagem original no docstore
        doc_id = img_doc.metadata.get('doc_id')
        if doc_id in docstore:
            print(f"\n   🖼️ Imagem original: DISPONÍVEL no docstore")

            # Tentar decodificar e salvar
            try:
                img_data = docstore[doc_id]

                # Se for string base64
                if isinstance(img_data, str):
                    # Remover prefixo data:image se houver
                    if 'data:image' in img_data:
                        img_data = img_data.split(',')[1]

                    # Decodificar
                    img_bytes = b64decode(img_data)
                    img = Image.open(io.BytesIO(img_bytes))

                    # Salvar
                    filename = f"imagem_{source.replace('.pdf', '')}_{i}.png"
                    filename = filename.replace(' ', '_').replace('–', '-')
                    img.save(filename)

                    print(f"   ✓ Imagem salva em: {filename}")
                    print(f"   Tamanho: {img.size[0]}x{img.size[1]} pixels")
                    print(f"   Formato: {img.format}")
                else:
                    print(f"   ⚠️ Formato inesperado no docstore: {type(img_data)}")

            except Exception as e:
                print(f"   ✗ Erro ao decodificar imagem: {str(e)[:100]}")
        else:
            print(f"\n   ⚠️ Imagem original NÃO encontrada no docstore")

        print("\n")

print("=" * 80)
print("✅ VISUALIZAÇÃO CONCLUÍDA")
print("=" * 80)
print("\nImagens salvas no diretório atual como:")
print("   imagem_[documento]_[numero].png")
print("\nAbra as imagens para verificar se são os fluxogramas esperados!")
print()
