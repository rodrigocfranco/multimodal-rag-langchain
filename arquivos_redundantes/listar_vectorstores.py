#!/usr/bin/env python3
"""
Listar Vectorstores Disponíveis
Mostra todos os vectorstores processados e salvos
"""

import os
import pickle
from datetime import datetime

print("=" * 80)
print("📂 VECTORSTORES DISPONÍVEIS")
print("=" * 80)
print()

vectorstores_dir = "./vectorstores"

if not os.path.exists(vectorstores_dir):
    print("❌ Nenhum vectorstore encontrado.")
    print()
    print("💡 Processe um PDF primeiro com:")
    print('  python processar_e_salvar.py "seu_arquivo.pdf"')
    exit(0)

vectorstores = [d for d in os.listdir(vectorstores_dir) if os.path.isdir(os.path.join(vectorstores_dir, d))]

if not vectorstores:
    print("❌ Nenhum vectorstore encontrado.")
    print()
    print("💡 Processe um PDF primeiro com:")
    print('  python processar_e_salvar.py "seu_arquivo.pdf"')
    exit(0)

print(f"Encontrados {len(vectorstores)} vectorstore(s):")
print()

for i, vs_name in enumerate(sorted(vectorstores), 1):
    vs_path = os.path.join(vectorstores_dir, vs_name)
    metadata_path = os.path.join(vs_path, "metadata.pkl")
    
    print(f"{i}. {vs_name}")
    print("   " + "─" * 70)
    
    # Carregar metadados se existir
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            print(f"   📄 Arquivo: {metadata.get('pdf_filename', 'N/A')}")
            print(f"   📝 Textos: {metadata.get('num_texts', 0)}")
            print(f"   📊 Tabelas: {metadata.get('num_tables', 0)}")
            print(f"   🖼️  Imagens: {metadata.get('num_images', 0)}")
            print(f"   ⏰ Processado: {metadata.get('processed_at', 'N/A')}")
        except:
            print("   ⚠️  Metadados não disponíveis")
    else:
        print("   ⚠️  Metadados não disponíveis")
    
    # Tamanho do vectorstore
    total_size = 0
    for root, dirs, files in os.walk(vs_path):
        total_size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    
    size_mb = total_size / (1024 * 1024)
    print(f"   💾 Tamanho: {size_mb:.2f} MB")
    print(f"   📂 Localização: {vs_path}")
    
    print()
    print(f"   🚀 Para consultar:")
    print(f"      python consultar_vectorstore.py {vs_name}")
    print()

print("=" * 80)
print("💡 DICAS:")
print("=" * 80)
print()
print("• Para processar um novo PDF:")
print('  python processar_e_salvar.py "seu_arquivo.pdf"')
print()
print("• Para consultar um vectorstore:")
print("  python consultar_vectorstore.py nome_do_vectorstore")
print()
print("• Para deletar um vectorstore:")
print("  rm -rf vectorstores/nome_do_vectorstore")
print()
print("=" * 80)

