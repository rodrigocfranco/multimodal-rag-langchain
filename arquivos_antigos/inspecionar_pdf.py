#!/usr/bin/env python3
"""
Inspetor de PDF - Ver o que foi extraído
Mostra os dados extraídos do PDF sem processar tudo
"""

import sys
import os
from unstructured.partition.pdf import partition_pdf

print("=" * 80)
print("🔍 INSPETOR DE PDF - Ver Dados Extraídos")
print("=" * 80)
print()

# Verificar argumentos
if len(sys.argv) < 2:
    print("❌ Uso: python inspecionar_pdf.py nome_do_arquivo.pdf")
    print()
    print("Exemplo:")
    print("  python inspecionar_pdf.py attention.pdf")
    print("  python inspecionar_pdf.py 'Manejo da terapia antidiabética no DM2.pdf'")
    sys.exit(1)

pdf_filename = sys.argv[1]
output_path = "./content/"
file_path = output_path + pdf_filename

if not os.path.exists(file_path):
    print(f"❌ Arquivo não encontrado: {file_path}")
    sys.exit(1)

# Obter tamanho do arquivo
file_size = os.path.getsize(file_path) / 1024 / 1024
print(f"📄 Arquivo: {pdf_filename}")
print(f"📏 Tamanho: {file_size:.2f} MB")
print()
print("⏳ Extraindo dados... (pode demorar alguns minutos)")
print()

# Extrair dados
chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image"],
    extract_image_block_to_payload=True,
    chunking_strategy="by_title",
    max_characters=10000,
    combine_text_under_n_chars=2000,
    new_after_n_chars=6000,
)

print("=" * 80)
print("📊 ESTATÍSTICAS DO DOCUMENTO")
print("=" * 80)
print()

# Contar elementos
tables = []
texts = []
for chunk in chunks:
    if "Table" in str(type(chunk)):
        tables.append(chunk)
    if "CompositeElement" in str(type(chunk)):
        texts.append(chunk)

def get_images_base64(chunks):
    images_b64 = []
    for chunk in chunks:
        if "CompositeElement" in str(type(chunk)):
            if hasattr(chunk.metadata, 'orig_elements'):
                chunk_els = chunk.metadata.orig_elements
                for el in chunk_els:
                    if "Image" in str(type(el)):
                        images_b64.append(el.metadata.image_base64)
    return images_b64

images = get_images_base64(chunks)

print(f"✅ Total de chunks extraídos: {len(chunks)}")
print(f"📝 Chunks de texto: {len(texts)}")
print(f"📊 Tabelas: {len(tables)}")
print(f"🖼️  Imagens: {len(images)}")
print()

# Mostrar amostra de textos
if len(texts) > 0:
    print("=" * 80)
    print("📝 AMOSTRA DE TEXTOS (primeiros 3)")
    print("=" * 80)
    print()
    
    for i, text in enumerate(texts[:3]):
        print(f"\n┌─ Texto {i+1} " + "─" * 68)
        print(f"│ Tipo: {type(text).__name__}")
        if hasattr(text, 'metadata') and hasattr(text.metadata, 'page_number'):
            print(f"│ Página: {text.metadata.page_number}")
        print(f"│ Tamanho: {len(text.text)} caracteres")
        print(f"│")
        print(f"│ Conteúdo (primeiros 300 caracteres):")
        print(f"│ {text.text[:300]}...")
        print(f"└" + "─" * 78)

# Mostrar amostra de tabelas
if len(tables) > 0:
    print("\n")
    print("=" * 80)
    print("📊 AMOSTRA DE TABELAS (primeira)")
    print("=" * 80)
    print()
    
    table = tables[0]
    print(f"┌─ Tabela 1 " + "─" * 68)
    print(f"│ Tipo: {type(table).__name__}")
    if hasattr(table, 'metadata') and hasattr(table.metadata, 'page_number'):
        print(f"│ Página: {table.metadata.page_number}")
    print(f"│")
    print(f"│ Conteúdo HTML (primeiros 500 caracteres):")
    if hasattr(table.metadata, 'text_as_html'):
        print(f"│ {table.metadata.text_as_html[:500]}...")
    else:
        print(f"│ {str(table)[:500]}...")
    print(f"└" + "─" * 78)

# Informações sobre imagens
if len(images) > 0:
    print("\n")
    print("=" * 80)
    print("🖼️  INFORMAÇÕES SOBRE IMAGENS")
    print("=" * 80)
    print()
    
    for i, image in enumerate(images[:5]):  # Mostrar info das primeiras 5
        image_size = len(image) / 1024
        print(f"• Imagem {i+1}: {image_size:.1f} KB (base64)")
    
    if len(images) > 5:
        print(f"... e mais {len(images) - 5} imagens")

# Análise de metadados
print("\n")
print("=" * 80)
print("🏷️  ANÁLISE DE METADADOS")
print("=" * 80)
print()

metadata_keys = set()
for chunk in chunks:
    if hasattr(chunk, 'metadata'):
        metadata_keys.update(dir(chunk.metadata))

# Filtrar apenas atributos relevantes
relevant_metadata = [k for k in metadata_keys if not k.startswith('_')]
print("Metadados disponíveis nos chunks:")
for key in sorted(relevant_metadata)[:15]:  # Mostrar primeiros 15
    print(f"  • {key}")

# Resumo final
print("\n")
print("=" * 80)
print("✅ RESUMO DA EXTRAÇÃO")
print("=" * 80)
print()

print(f"""
Documento analisado com sucesso!

📄 Arquivo: {pdf_filename}
📏 Tamanho: {file_size:.2f} MB

Elementos extraídos:
  ✅ {len(chunks)} chunks totais
  ✅ {len(texts)} chunks de texto
  ✅ {len(tables)} tabelas
  ✅ {len(images)} imagens

💡 Próximos passos:
  1. Use 'chat_terminal.py' para fazer perguntas interativas
  2. Use 'app_streamlit.py' para interface web
  3. Os dados extraídos estão prontos para RAG!
""")

print("=" * 80)

