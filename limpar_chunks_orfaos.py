#!/usr/bin/env python3
"""
Script para limpar chunks órfãos (filename=None) do vectorstore

Problema:
- Chunks antigos foram criados SEM campo 'filename' no metadata
- Quando documentos foram deletados, esses chunks ficaram órfãos
- Resultado: chunks com filename=None ainda respondem queries

Solução:
- Buscar TODOS os chunks do Chroma
- Identificar chunks com filename=None ou filename ausente
- Deletar esses chunks do vectorstore E docstore
- Preservar chunks válidos com filename preenchido
"""

import os
import pickle
from dotenv import load_dotenv

load_dotenv()

def limpar_chunks_orfaos(persist_directory: str = "./knowledge"):
    """Remove chunks órfãos (sem filename) do vectorstore"""

    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    print("=" * 70)
    print("🧹 LIMPEZA DE CHUNKS ÓRFÃOS")
    print("=" * 70)

    # 1. Carregar vectorstore
    print("\n1️⃣ Carregando vectorstore...")
    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
        persist_directory=persist_directory
    )

    # 2. Buscar TODOS os chunks
    print("2️⃣ Buscando todos os chunks...")
    all_results = vectorstore.get(include=['metadatas'])

    total_chunks = len(all_results['ids'])
    print(f"   ✓ Total de chunks no Chroma: {total_chunks}")

    # 3. Carregar docstore para validação profunda
    print("\n3️⃣ Carregando docstore...")
    import pickle
    docstore_path = f"{persist_directory}/docstore.pkl"
    docstore_ids = set()

    if os.path.exists(docstore_path):
        try:
            with open(docstore_path, 'rb') as f:
                docstore = pickle.load(f)
                docstore_ids = set(docstore.keys())
                print(f"   ✓ Docstore com {len(docstore_ids)} doc_ids válidos")
        except Exception as e:
            print(f"   ⚠️  Erro ao carregar docstore: {str(e)}")
    else:
        print(f"   ⚠️  Docstore não encontrado em {docstore_path}")

    # 4. Identificar chunks órfãos (DUAS VALIDAÇÕES)
    print("\n4️⃣ Identificando chunks órfãos...")
    orphan_chunk_ids = []
    valid_chunk_ids = []

    for i, meta in enumerate(all_results.get('metadatas', [])):
        chunk_id = all_results['ids'][i]
        filename = meta.get('filename')
        doc_id = meta.get('doc_id')
        source = meta.get('source', 'N/A')

        # VALIDAÇÃO 1: Chunk órfão = filename é None, vazio, ou ausente
        orphan_reason = None
        if filename is None or filename == '' or filename == 'N/A':
            orphan_reason = "filename_missing"
        # VALIDAÇÃO 2: doc_id não existe no docstore
        elif doc_id and docstore_ids and doc_id not in docstore_ids:
            orphan_reason = "doc_id_not_in_docstore"

        if orphan_reason:
            orphan_chunk_ids.append({
                'id': chunk_id,
                'source': source,
                'type': meta.get('type', 'unknown'),
                'reason': orphan_reason,
                'doc_id': doc_id
            })
        else:
            valid_chunk_ids.append(chunk_id)

    print(f"   ✓ Chunks válidos (com filename): {len(valid_chunk_ids)}")
    print(f"   ⚠️  Chunks órfãos (sem filename): {len(orphan_chunk_ids)}")

    if len(orphan_chunk_ids) == 0:
        print("\n✅ Nenhum chunk órfão encontrado! Vectorstore está limpo.")
        return

    # Mostrar estatísticas dos órfãos
    print("\n📊 Estatísticas dos chunks órfãos:")
    from collections import Counter
    orphan_sources = [c['source'] for c in orphan_chunk_ids]
    orphan_types = [c['type'] for c in orphan_chunk_ids]
    orphan_reasons = [c['reason'] for c in orphan_chunk_ids]

    source_counts = Counter(orphan_sources)
    type_counts = Counter(orphan_types)
    reason_counts = Counter(orphan_reasons)

    print("\n   Por razão:")
    for reason, count in reason_counts.most_common():
        reason_label = {
            'filename_missing': '❌ Sem filename',
            'doc_id_not_in_docstore': '🔗 doc_id não existe no docstore'
        }.get(reason, reason)
        print(f"      - {reason_label}: {count} chunks")

    print("\n   Por source:")
    for source, count in source_counts.most_common():
        print(f"      - {source}: {count} chunks")

    print("\n   Por tipo:")
    for chunk_type, count in type_counts.most_common():
        print(f"      - {chunk_type}: {count} chunks")

    # 4. Confirmar deleção
    print(f"\n⚠️  ATENÇÃO: Isso vai DELETAR {len(orphan_chunk_ids)} chunks órfãos!")
    print("   Chunks válidos serão preservados.")

    resposta = input("\n❓ Confirma deleção? (sim/não): ").strip().lower()

    if resposta not in ['sim', 's', 'yes', 'y']:
        print("\n❌ Operação cancelada pelo usuário.")
        return

    # 5. Deletar do vectorstore
    print("\n4️⃣ Deletando chunks órfãos do vectorstore...")
    orphan_ids_only = [c['id'] for c in orphan_chunk_ids]

    try:
        vectorstore.delete(ids=orphan_ids_only)
        print(f"   ✓ {len(orphan_ids_only)} chunks deletados do Chroma")
    except Exception as e:
        print(f"   ✗ Erro ao deletar do Chroma: {str(e)}")
        return

    # 6. Deletar do docstore
    print("\n5️⃣ Deletando do docstore...")
    docstore_path = f"{persist_directory}/docstore.pkl"

    if os.path.exists(docstore_path):
        try:
            with open(docstore_path, 'rb') as f:
                docstore = pickle.load(f)

            deleted_from_docstore = 0
            for chunk_id in orphan_ids_only:
                if chunk_id in docstore:
                    del docstore[chunk_id]
                    deleted_from_docstore += 1

            with open(docstore_path, 'wb') as f:
                pickle.dump(docstore, f)

            print(f"   ✓ {deleted_from_docstore} itens deletados do docstore")

            # Atualizar timestamp para invalidar cache
            os.utime(docstore_path, None)
            print(f"   ✓ Timestamp do docstore atualizado (invalida cache)")

        except Exception as e:
            print(f"   ⚠️  Erro ao limpar docstore: {str(e)}")
    else:
        print(f"   ℹ️  Docstore não existe em {docstore_path}")

    # 7. Verificar resultado
    print("\n6️⃣ Verificando resultado...")
    all_results_after = vectorstore.get(include=['metadatas'])
    total_after = len(all_results_after['ids'])

    orphans_remaining = sum(
        1 for meta in all_results_after.get('metadatas', [])
        if meta.get('filename') is None or meta.get('filename') == ''
    )

    print(f"   ✓ Chunks antes: {total_chunks}")
    print(f"   ✓ Chunks depois: {total_after}")
    print(f"   ✓ Chunks deletados: {total_chunks - total_after}")
    print(f"   ✓ Órfãos restantes: {orphans_remaining}")

    if orphans_remaining == 0:
        print("\n✅ SUCESSO! Todos os chunks órfãos foram removidos!")
    else:
        print(f"\n⚠️  Ainda há {orphans_remaining} chunks órfãos. Execute novamente.")

    print("\n" + "=" * 70)
    print("🎉 Limpeza concluída!")
    print("=" * 70)


if __name__ == "__main__":
    import sys

    # Permitir passar persist_directory como argumento
    persist_dir = sys.argv[1] if len(sys.argv) > 1 else "./knowledge"

    print(f"\n📂 Diretório: {persist_dir}")

    limpar_chunks_orfaos(persist_dir)
