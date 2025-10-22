#!/usr/bin/env python3
"""
Sistema de Gerenciamento de Documentos
Funções para criar, deletar e gerenciar documentos no knowledge base
"""

import os
import hashlib
import pickle
from typing import Dict, List, Optional


def generate_pdf_id(file_path: str) -> str:
    """
    Gera hash SHA256 único do arquivo PDF

    Args:
        file_path: Caminho completo do arquivo

    Returns:
        str: Hash SHA256 do arquivo (64 caracteres hexadecimais)

    Example:
        >>> generate_pdf_id("content/artigo.pdf")
        'a3f8b2c1d4e5f6789...'
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Ler em blocos de 4KB para eficiência com arquivos grandes
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def get_all_documents(persist_directory: str = "./knowledge") -> Dict:
    """
    Retorna lista de todos documentos processados

    Args:
        persist_directory: Diretório do knowledge base

    Returns:
        dict: {"documents": [...], "total": N}
    """
    metadata_path = f"{persist_directory}/metadata.pkl"

    if not os.path.exists(metadata_path):
        return {"documents": [], "total": 0}

    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    documents = []
    for pdf_id, doc_info in metadata.get('documents', {}).items():
        documents.append({
            "pdf_id": pdf_id,
            "filename": doc_info.get('filename', 'unknown'),
            "original_filename": doc_info.get('original_filename', doc_info.get('filename')),
            "uploaded_at": doc_info.get('uploaded_at'),
            "processed_at": doc_info.get('processed_at'),
            "file_size": doc_info.get('file_size', 0),
            "stats": doc_info.get('stats', {}),
            "status": doc_info.get('status', 'processed')
        })

    # Ordenar por data de upload (mais recente primeiro)
    documents.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)

    return {"documents": documents, "total": len(documents)}


def get_document_by_id(pdf_id: str, persist_directory: str = "./knowledge") -> Optional[Dict]:
    """
    Retorna informações detalhadas de um documento

    Args:
        pdf_id: ID do documento (hash SHA256)
        persist_directory: Diretório do knowledge base

    Returns:
        dict: Informações do documento ou None se não encontrado
    """
    metadata_path = f"{persist_directory}/metadata.pkl"

    if not os.path.exists(metadata_path):
        return None

    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    return metadata.get('documents', {}).get(pdf_id)


def delete_document(pdf_id: str, persist_directory: str = "./knowledge") -> Dict:
    """
    Remove TODOS os chunks/embeddings de um documento

    Args:
        pdf_id: Hash SHA256 do documento
        persist_directory: Diretório do knowledge base

    Returns:
        dict: {
            "status": "success|not_found|error",
            "deleted_chunks": N,
            "pdf_id": "...",
            "error": "..." (se houver erro)
        }
    """
    try:
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings

        # 1. Carregar vectorstore
        vectorstore = Chroma(
            collection_name="knowledge_base",
            embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
            persist_directory=persist_directory
        )

        # 2. Buscar filename do documento primeiro
        metadata_path = f"{persist_directory}/metadata.pkl"
        if not os.path.exists(metadata_path):
            return {"status": "not_found", "deleted_chunks": 0, "error": "Metadata não encontrado"}

        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)

        doc_info = metadata.get('documents', {}).get(pdf_id)
        if not doc_info:
            return {"status": "not_found", "deleted_chunks": 0, "error": "PDF não encontrado"}

        filename = doc_info.get('filename')

        # 3. Buscar chunks por MÚLTIPLOS critérios (garante deletar tudo)
        all_chunk_ids = set()

        # Estratégia 1: Buscar por pdf_id
        try:
            results = vectorstore.get(where={"pdf_id": pdf_id})
            all_chunk_ids.update(results.get('ids', []))
            print(f"   Encontrados {len(results.get('ids', []))} chunks por pdf_id")
        except:
            pass

        # Estratégia 2: Buscar por source (fallback para documentos antigos)
        try:
            results = vectorstore.get(where={"source": filename})
            all_chunk_ids.update(results.get('ids', []))
            print(f"   Encontrados {len(results.get('ids', []))} chunks por source")
        except:
            pass

        # Estratégia 3: Buscar TODOS e filtrar manualmente (último recurso)
        if len(all_chunk_ids) == 0:
            print(f"   ⚠️ Buscando todos chunks manualmente...")
            try:
                all_results = vectorstore.get(include=['metadatas'])
                for i, meta in enumerate(all_results.get('metadatas', [])):
                    if meta.get('pdf_id') == pdf_id or meta.get('source') == filename:
                        all_chunk_ids.add(all_results['ids'][i])
                print(f"   Encontrados {len(all_chunk_ids)} chunks por busca manual")
            except Exception as e:
                print(f"   ✗ Erro na busca manual: {str(e)}")

        chunk_ids = list(all_chunk_ids)

        if not chunk_ids:
            return {"status": "not_found", "deleted_chunks": 0, "pdf_id": pdf_id, "error": "Nenhum chunk encontrado"}

        # 3. Deletar do vectorstore
        vectorstore.delete(ids=chunk_ids)

        # 4. Deletar do docstore
        docstore_path = f"{persist_directory}/docstore.pkl"
        if os.path.exists(docstore_path):
            with open(docstore_path, 'rb') as f:
                docstore = pickle.load(f)

            for chunk_id in chunk_ids:
                docstore.pop(chunk_id, None)

            with open(docstore_path, 'wb') as f:
                pickle.dump(docstore, f)

        # 5. Atualizar metadata.pkl
        if 'documents' in metadata and pdf_id in metadata['documents']:
            del metadata['documents'][pdf_id]

            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)

        # 6. ✅ FORÇAR ATUALIZAÇÃO DO TIMESTAMP DO DOCSTORE
        # Isso invalida o cache do retriever automaticamente
        import time
        if os.path.exists(docstore_path):
            os.utime(docstore_path, None)  # Atualiza timestamp para "agora"
            print(f"   ✓ Timestamp do docstore atualizado (força rebuild do cache)")

        return {
            "status": "success",
            "deleted_chunks": len(chunk_ids),
            "pdf_id": pdf_id,
            "filename": filename
        }

    except Exception as e:
        return {
            "status": "error",
            "deleted_chunks": 0,
            "pdf_id": pdf_id,
            "error": str(e)
        }


def check_duplicate(file_path: str, persist_directory: str = "./knowledge") -> Optional[Dict]:
    """
    Verifica se um PDF já foi processado (por hash)

    Args:
        file_path: Caminho do arquivo a verificar
        persist_directory: Diretório do knowledge base

    Returns:
        dict: Informações do PDF existente ou None se não encontrado
    """
    pdf_id = generate_pdf_id(file_path)
    return get_document_by_id(pdf_id, persist_directory)


def get_global_stats(persist_directory: str = "./knowledge") -> Dict:
    """
    Retorna estatísticas globais do knowledge base

    Returns:
        dict: {
            "total_documents": N,
            "total_chunks": N,
            "total_size_bytes": N,
            "total_texts": N,
            "total_tables": N,
            "total_images": N
        }
    """
    metadata_path = f"{persist_directory}/metadata.pkl"

    if not os.path.exists(metadata_path):
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "total_size_bytes": 0,
            "total_texts": 0,
            "total_tables": 0,
            "total_images": 0
        }

    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    total_docs = len(metadata.get('documents', {}))
    total_chunks = 0
    total_size = 0
    total_texts = 0
    total_tables = 0
    total_images = 0

    for doc_info in metadata.get('documents', {}).values():
        stats = doc_info.get('stats', {})
        total_chunks += stats.get('total_chunks', 0)
        total_size += doc_info.get('file_size', 0)
        total_texts += stats.get('texts', 0)
        total_tables += stats.get('tables', 0)
        total_images += stats.get('images', 0)

    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "total_size_bytes": total_size,
        "total_texts": total_texts,
        "total_tables": total_tables,
        "total_images": total_images
    }


if __name__ == "__main__":
    # Testes básicos
    print("Testando document_manager.py...")

    # Listar documentos
    docs = get_all_documents()
    print(f"\nDocumentos: {docs['total']}")

    # Estatísticas
    stats = get_global_stats()
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Total size: {stats['total_size_bytes'] / 1024 / 1024:.2f} MB")
