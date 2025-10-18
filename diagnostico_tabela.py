#!/usr/bin/env python3
"""
Diagnóstico de como a Tabela 1 (Estratificação de Risco) foi chunkeada
"""

import os
import pickle
from dotenv import load_dotenv

load_dotenv()

persist_directory = os.getenv("PERSIST_DIR", "./knowledge")

print("=" * 70)
print("🔍 DIAGNÓSTICO: Chunking da Tabela de Risco Cardiovascular")
print("=" * 70)

# 1. Carregar docstore
docstore_path = f"{persist_directory}/docstore.pkl"
if not os.path.exists(docstore_path):
    print("❌ Docstore não encontrado")
    exit(1)

with open(docstore_path, 'rb') as f:
    docstore = pickle.load(f)

print(f"\n✅ Docstore carregado: {len(docstore)} documentos\n")

# 2. Buscar chunks relacionados a "risco cardiovascular" ou "hipercolesterolemia"
print("🔍 Procurando chunks da tabela de risco...\n")

relevant_chunks = []
for chunk_id, doc in docstore.items():
    # Extrair texto do chunk
    text = ""
    if hasattr(doc, 'text'):
        text = doc.text
    elif hasattr(doc, 'page_content'):
        text = doc.page_content
    elif isinstance(doc, str):
        text = doc
    else:
        text = str(doc)

    text_lower = text.lower()

    # Verificar se contém keywords da tabela
    if any(keyword in text_lower for keyword in [
        'hipercolesterolemia familiar',
        'muito alto',
        'alto',
        'moderado',
        'risco cardiovascular',
        '3 ou mais fatores',
        'três ou mais fatores'
    ]):
        relevant_chunks.append({
            'chunk_id': chunk_id,
            'text': text,
            'length': len(text),
            'type': type(doc).__name__,
            'has_metadata': hasattr(doc, 'metadata')
        })

print(f"✅ Encontrados {len(relevant_chunks)} chunks relevantes\n")

# 3. Analisar cada chunk
for i, chunk in enumerate(relevant_chunks):
    print(f"\n{'='*70}")
    print(f"CHUNK {i+1}/{len(relevant_chunks)}")
    print(f"{'='*70}")
    print(f"ID: {chunk['chunk_id']}")
    print(f"Tipo: {chunk['type']}")
    print(f"Tamanho: {chunk['length']} chars")
    print(f"\nCONTEÚDO:")
    print("-" * 70)
    print(chunk['text'])
    print("-" * 70)

    # Verificar keywords específicas
    text_lower = chunk['text'].lower()
    keywords_found = []

    if 'hipercolesterolemia familiar' in text_lower:
        keywords_found.append('✅ Hipercolesterolemia Familiar')
    if '3 ou mais fatores' in text_lower or 'três ou mais fatores' in text_lower:
        keywords_found.append('✅ 3 ou mais fatores')
    if 'muito alto' in text_lower:
        keywords_found.append('✅ MUITO ALTO')
    if 'alto' in text_lower and 'muito alto' not in text_lower:
        keywords_found.append('⚠️  ALTO (sem "muito")')
    if 'moderado' in text_lower:
        keywords_found.append('⚠️  MODERADO')

    if keywords_found:
        print("\nKeywords encontradas:")
        for kw in keywords_found:
            print(f"  {kw}")

print("\n" + "=" * 70)
print("📊 ANÁLISE")
print("=" * 70)

# 4. Verificar se algum chunk tem "Hipercolesterolemia Familiar" + "MUITO ALTO" juntos
hf_chunks = [c for c in relevant_chunks if 'hipercolesterolemia familiar' in c['text'].lower()]
ma_chunks = [c for c in relevant_chunks if 'muito alto' in c['text'].lower()]

print(f"\nChunks com 'Hipercolesterolemia Familiar': {len(hf_chunks)}")
print(f"Chunks com 'MUITO ALTO': {len(ma_chunks)}")

# Verificar se HF está no mesmo chunk que "MUITO ALTO"
hf_and_ma = [c for c in hf_chunks if 'muito alto' in c['text'].lower()]
print(f"Chunks com AMBOS: {len(hf_and_ma)}")

if len(hf_and_ma) == 0:
    print("\n❌ PROBLEMA IDENTIFICADO!")
    print("   'Hipercolesterolemia Familiar' NÃO está no mesmo chunk que 'MUITO ALTO'")
    print("   A tabela foi quebrada incorretamente pelo chunking!")
    print("\n🔧 SOLUÇÃO:")
    print("   1. Aumentar max_characters para evitar quebrar tabelas")
    print("   2. Ou processar tabela inteira como imagem")
else:
    print("\n✅ HF e MUITO ALTO estão no mesmo chunk")

print("\n" + "=" * 70)
