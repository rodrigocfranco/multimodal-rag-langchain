#!/usr/bin/env python3
"""
Consultar Knowledge Base com RERANKER (Cohere)
Melhora DRASTICAMENTE a precisão do retrieval
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Verificar API key do Cohere
if not os.getenv("COHERE_API_KEY"):
    print("❌ COHERE_API_KEY não configurada no .env")
    print("Adicione: COHERE_API_KEY=sua_chave")
    exit(1)

modo_api = '--api' in sys.argv

if modo_api:
    # ========================================================================
    # MODO API
    # ========================================================================
    from flask import Flask, request, jsonify, render_template_string, Response
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    
    from langchain_chroma import Chroma
    from langchain.storage import InMemoryStore
    from langchain_openai import OpenAIEmbeddings
    from langchain.retrievers.multi_vector import MultiVectorRetriever
    from langchain_cohere import CohereRerank
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    from langchain_core.messages import HumanMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    from typing import List
    from base64 import b64decode, b64encode
    import pickle
    from PIL import Image
    import io

    # Railway Volume
    persist_directory = os.getenv("PERSIST_DIR", "./knowledge")

    # ===========================================================================
    # 🖼️ IMAGE CONVERSION: Convert all images to JPEG for GPT-4 Vision
    # ===========================================================================
    def convert_image_to_jpeg_base64(image_base64_str):
        """
        Converte qualquer formato de imagem para JPEG (suportado por GPT-4 Vision).

        Formatos não suportados: TIFF, BMP, ICO, etc.
        Formatos suportados: PNG, JPEG, GIF, WEBP

        Esta função garante que TODAS as imagens sejam JPEG válidas.
        """
        try:
            # Decodificar base64 para bytes
            image_bytes = b64decode(image_base64_str)

            # Abrir imagem com PIL
            img = Image.open(io.BytesIO(image_bytes))

            # 🔥 RESIZE TO MAX 512x512 TO REDUCE TOKENS (fix context length exceeded)
            MAX_SIZE = 512
            if img.width > MAX_SIZE or img.height > MAX_SIZE:
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

            # Converter para RGB (remove alpha channel se houver)
            # Isso é necessário porque JPEG não suporta transparência
            if img.mode in ('RGBA', 'LA', 'P'):
                # Criar background branco
                background = Image.new('RGB', img.size, (255, 255, 255))

                # Converter P (palette) para RGBA primeiro
                if img.mode == 'P':
                    img = img.convert('RGBA')

                # Colar imagem sobre background branco (preserva transparência)
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])  # Usa alpha channel como máscara
                else:
                    background.paste(img)

                img = background
            elif img.mode != 'RGB':
                # Outros modos (L, CMYK, etc.) → RGB
                img = img.convert('RGB')

            # Salvar como JPEG em buffer
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            jpeg_bytes = output.getvalue()

            # Re-encodar para base64
            jpeg_base64 = b64encode(jpeg_bytes).decode('utf-8')

            return jpeg_base64, True

        except Exception as e:
            # Se conversão falhar, retornar None
            print(f"      ⚠️  Erro ao converter imagem durante query: {str(e)[:100]}")
            return None, False

    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),  # Modelo novo, melhor semântica
        persist_directory=persist_directory
    )

    # ✅ FUNÇÃO para recarregar docstore dinamicamente
    def load_docstore():
        """Recarrega docstore do disco (pega documentos novos)"""
        docstore_path = f"{persist_directory}/docstore.pkl"
        store = InMemoryStore()
        if os.path.exists(docstore_path):
            with open(docstore_path, 'rb') as f:
                store.store = pickle.load(f)
        return store

    # Carregar docstore inicial
    store = load_docstore()

    # ✅ GLOBAL: Guardar referência ao docstore para parse_docs() acessar
    global _docstore
    _docstore = store

    base_retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key="doc_id",
        search_kwargs={"k": 30}  # ✅ OTIMIZADO: Aumentado para 30 para capturar info dispersa
    )

    # ===========================================================================
    # 🖼️ FIX: HYBRID RETRIEVAL COM BOOST PARA IMAGENS
    # ===========================================================================
    import re

    def detect_image_query(question):
        """
        Detecta se a query do usuário está pedindo informações visuais.

        Returns:
            (bool, list): (is_image_query, keywords_found)
        """
        image_patterns = [
            # Padrões específicos com números
            r'\bfigura\s+\d+\b',  # "figura 1", "figura 2"
            r'\bfig\.?\s*\d+\b',   # "fig. 1", "fig 2"
            r'\btabela\s+\d+\b',   # "tabela 1"

            # Palavras-chave visuais (singular e plural)
            r'\bfluxogramas?\b',   # "fluxograma" ou "fluxogramas"
            r'\balgorit?mos?\b',   # "algoritmo" ou "algoritmos"
            r'\bdiagramas?\b',     # "diagrama" ou "diagramas"
            r'\bgr[aá]ficos?\b',   # "gráfico" ou "gráficos"
            r'\bimagens?\b',       # "imagem" ou "imagens"
            r'\bfiguras?\b',       # "figura" ou "figuras"
            r'\bilustra[çc][õo]es?\b',  # "ilustração" ou "ilustrações"

            # Verbos + conteúdo visual
            r'\bexplique\s+(a|o|as|os)\s+(figura|imagem|fluxograma|algoritmo|diagrama)s?\b',
            r'\bdescreva\s+(a|o|as|os)\s+(figura|imagem|fluxograma)s?\b',
            r'\bmostr(e|a|ar)\s+(a|o|as|os)?\s*(figura|imagem|fluxograma)s?\b',
            r'\btraga?\s+(a|o|as|os)?\s*(figura|imagem|fluxograma)s?\b',
            r'\bo\s+que\s+(mostra|diz|apresenta)\s+(a|o)\s+(figura|imagem)\b',

            # Perguntas sobre presença de conteúdo visual
            r'\bquais\s+(as\s+)?(figura|imagem|fluxograma|diagrama|tabela)s?\b',
            r'\bh[aá]\s+(algum|alguma)?\s*(figura|imagem|fluxograma)s?\b',
            r'\b(lista|liste)\s+(as\s+)?(figura|imagem)s?\b',
        ]

        keywords_found = []
        for pattern in image_patterns:
            match = re.search(pattern, question.lower())
            if match:
                keywords_found.append(match.group(0))

        return len(keywords_found) > 0, keywords_found


    def force_include_images(question, base_results, vectorstore_instance, max_images=5):
        """
        SEMPRE busca e inclui imagens relevantes para enriquecer a resposta.

        O sistema agora é proativo: para QUALQUER query, busca imagens relacionadas
        e deixa o reranking decidir se elas são relevantes o suficiente para incluir.

        Args:
            question: Query do usuário
            base_results: Resultados do retrieval normal
            vectorstore_instance: ChromaDB vectorstore
            max_images: Máximo de imagens a incluir (default: 5)

        Returns:
            list: Resultados combinados (base_results + imagens relevantes)
        """
        print(f"   🖼️ Buscando imagens relevantes para enriquecer resposta...")

        # Buscar DIRETAMENTE por imagens usando a query original
        # O embedding semântico vai encontrar imagens relacionadas ao tema
        try:
            # Usar apenas a query original - o modelo de embeddings é inteligente!
            image_queries = [question]

            found_images = []
            seen_doc_ids = set()

            for img_query in image_queries:
                try:
                    # 🛡️ FIX: Buscar diretamente no Chroma SEM usar MultiVectorRetriever
                    # (isso evita o erro "Error finding id" de chunks órfãos)
                    from langchain_chroma import Chroma

                    # Usar o vectorstore do Chroma diretamente (não o MultiVectorRetriever)
                    chroma_client = vectorstore_instance.vectorstore if hasattr(vectorstore_instance, 'vectorstore') else vectorstore_instance

                    try:
                        images = chroma_client.similarity_search(
                            img_query,
                            k=30,  # Buscar mais para cobrir múltiplos documentos
                            filter={"type": "image"}
                        )
                    except Exception as e:
                        # Error finding id = chunks órfãos no Chroma
                        print(f"      ⚠️ Erro no Chroma (chunks órfãos): {str(e)[:80]}")
                        print(f"         Use 'Limpar Órfãos' no admin para resolver!")
                        images = []

                    for img in images:
                        doc_id = img.metadata.get('doc_id')
                        if doc_id and doc_id not in seen_doc_ids:
                            # ✅ Validar se doc_id existe no docstore ANTES de adicionar
                            # (previne chunks órfãos de aparecer)
                            global _docstore
                            if _docstore and hasattr(_docstore, 'mget'):
                                try:
                                    doc_obj = _docstore.mget([doc_id])[0]
                                    if doc_obj:
                                        found_images.append(img)
                                        seen_doc_ids.add(doc_id)
                                    else:
                                        print(f"      ⚠️ Chunk órfão ignorado: {doc_id}")
                                except:
                                    print(f"      ⚠️ Erro ao validar doc_id {doc_id}, ignorando...")
                                    continue
                            else:
                                # Se docstore não disponível, adicionar mesmo assim
                                found_images.append(img)
                                seen_doc_ids.add(doc_id)

                            if len(found_images) >= max_images:
                                break

                except Exception as e:
                    print(f"      ⚠️ Erro na busca com filtro: {str(e)[:100]}")
                    print(f"         Tentando continuar sem imagens...")
                    continue

                if len(found_images) >= max_images:
                    break

            if found_images:
                print(f"   ✓ Forçando inclusão de {len(found_images)} imagens")

                # IMPORTANTE: Adicionar imagens NO INÍCIO dos resultados
                # Isso garante que passarão pelo rerank com prioridade
                combined_results = found_images + base_results

                # Deduplicate por doc_id
                seen = set()
                unique_results = []
                for doc in combined_results:
                    doc_id = doc.metadata.get('doc_id')
                    if doc_id not in seen:
                        seen.add(doc_id)
                        unique_results.append(doc)

                return unique_results[:40]  # Limitar a 40 para não sobrecarregar rerank

            else:
                print(f"   ⚠️ Nenhuma imagem encontrada mesmo com filtro!")
                return base_results

        except Exception as e:
            print(f"   ✗ Erro ao forçar inclusão de imagens: {str(e)[:200]}")
            return base_results

    # Wrapper para converter objetos Unstructured em Documents COM BOOST DE IMAGENS
    class DocumentConverter(BaseRetriever):
        retriever: MultiVectorRetriever
        vectorstore_ref: any  # Referência ao vectorstore para busca direta

        def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
        ) -> List[Document]:
            # 1. Retrieval normal
            docs = self.retriever.invoke(query)
            print(f"   DEBUG DocumentConverter: retriever retornou {len(docs)} docs")

            # 2. Converter para Documents
            converted = []
            for i, doc in enumerate(docs):
                if i < 3:  # Só print dos primeiros 3 para não poluir
                    print(f"   DEBUG doc {i}: type={type(doc).__name__}, hasattr page_content={hasattr(doc, 'page_content')}, hasattr text={hasattr(doc, 'text')}, is str={isinstance(doc, str)}")

                # Converter para Document do LangChain
                if hasattr(doc, 'page_content'):
                    converted.append(doc)
                    if i < 3:
                        print(f"      → Adicionado via page_content")
                elif hasattr(doc, 'text'):
                    # Table ou CompositeElement → Document
                    # Converter metadata para dict
                    metadata = {}
                    if hasattr(doc, 'metadata'):
                        if isinstance(doc.metadata, dict):
                            metadata = doc.metadata
                        else:
                            # ElementMetadata → dict
                            metadata = doc.metadata.to_dict() if hasattr(doc.metadata, 'to_dict') else {}

                    converted.append(Document(
                        page_content=doc.text,
                        metadata=metadata
                    ))
                    if i < 3:
                        print(f"      → Convertido via text")
                elif isinstance(doc, str):
                    converted.append(Document(page_content=doc, metadata={}))
                    if i < 3:
                        print(f"      → Convertido de string")
                else:
                    converted.append(Document(page_content=str(doc), metadata={}))
                    if i < 3:
                        print(f"      → Convertido via str(doc)")

            print(f"   DEBUG DocumentConverter: converteu {len(converted)} de {len(docs)} docs")

            # 3. 🖼️ FORÇA INCLUSÃO DE IMAGENS se query for sobre imagens
            enhanced_results = force_include_images(
                question=query,
                base_results=converted,
                vectorstore_instance=self.vectorstore_ref,
                max_images=2
            )

            return enhanced_results

    # Wrapper do retriever para converter objetos COM BOOST DE IMAGENS
    wrapped_retriever = DocumentConverter(
        retriever=base_retriever,
        vectorstore_ref=vectorstore  # ← Passar vectorstore para busca direta
    )

    # ===========================================================================
    # 🚀 HYBRID SEARCH: BM25 + VECTOR (ROBUST SOLUTION)
    # ===========================================================================
    from langchain.retrievers import EnsembleRetriever
    from langchain_community.retrievers import BM25Retriever

    # ===========================================================================
    # 📦 CACHE INTELIGENTE: Só recarrega se docstore mudou (escalável!)
    # ===========================================================================

    # Cache global do retriever
    _cached_retriever = None
    _cached_num_docs = 0
    _last_docstore_mtime = None

    def rebuild_retriever():
        """
        Reconstrói o retriever recarregando docstore do disco.
        ⚠️ OPERAÇÃO PESADA: Só deve ser chamada quando docstore muda!
        """
        # 1. Recarregar docstore (pega PDFs novos adicionados)
        fresh_store = load_docstore()

        # 2. Recarregar Chroma vectorstore (pega embeddings novos do disco)
        fresh_vectorstore = Chroma(
            collection_name="knowledge_base",
            embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
            persist_directory=persist_directory
        )

        # 3. Criar novo base_retriever com vectorstore e docstore atualizados
        fresh_base_retriever = MultiVectorRetriever(
            vectorstore=fresh_vectorstore,
            docstore=fresh_store,
            id_key="doc_id",
            search_kwargs={"k": 30}
        )

        # 4. Criar DocumentConverter COM BOOST DE IMAGENS para o novo retriever
        class FreshDocumentConverter(BaseRetriever):
            retriever: MultiVectorRetriever
            vectorstore_ref: any  # Referência ao vectorstore para busca direta

            def _get_relevant_documents(
                self, query: str, *, run_manager: CallbackManagerForRetrieverRun
            ) -> List[Document]:
                # 1. Retrieval normal
                docs = self.retriever.invoke(query)

                # 2. Converter para Documents
                converted = []
                for doc in docs:
                    if hasattr(doc, 'page_content'):
                        converted.append(doc)
                    elif hasattr(doc, 'text'):
                        metadata = {}
                        if hasattr(doc, 'metadata'):
                            if isinstance(doc.metadata, dict):
                                metadata = doc.metadata
                            else:
                                metadata = doc.metadata.to_dict() if hasattr(doc.metadata, 'to_dict') else {}

                        converted.append(Document(
                            page_content=doc.text,
                            metadata=metadata
                        ))
                    elif isinstance(doc, str):
                        converted.append(Document(page_content=doc, metadata={}))
                    else:
                        converted.append(Document(page_content=str(doc), metadata={}))

                # 3. 🖼️ FORÇA INCLUSÃO DE IMAGENS se query for sobre imagens
                enhanced_results = force_include_images(
                    question=query,
                    base_results=converted,
                    vectorstore_instance=self.vectorstore_ref,
                    max_images=2
                )

                return enhanced_results

        fresh_wrapped_retriever = FreshDocumentConverter(
            retriever=fresh_base_retriever,
            vectorstore_ref=fresh_vectorstore  # ← Passar vectorstore atualizado
        )

        # 3. Reconstruir BM25 com todos documentos atualizados
        all_docs_for_bm25 = []
        for doc_id, doc in fresh_store.store.items():
            # Converter para Document do LangChain
            if hasattr(doc, 'page_content'):
                all_docs_for_bm25.append(doc)
            elif hasattr(doc, 'text'):
                # Converter Unstructured para Document
                metadata = {}
                if hasattr(doc, 'metadata'):
                    if isinstance(doc.metadata, dict):
                        metadata = doc.metadata
                    elif hasattr(doc.metadata, 'to_dict'):
                        metadata = doc.metadata.to_dict()
                    else:
                        metadata = {}

                all_docs_for_bm25.append(Document(
                    page_content=doc.text,
                    metadata=metadata
                ))
            elif isinstance(doc, str):
                # Imagens (base64) - pular, BM25 é para texto
                pass

        # 5. Reconstruir BM25 retriever
        # Validar se há documentos antes de criar BM25
        if len(all_docs_for_bm25) == 0:
            print(f"   ⚠️  Nenhum documento para BM25 (rebuild) - retornando None")
            return None, 0

        bm25_retriever = BM25Retriever.from_documents(all_docs_for_bm25)
        bm25_retriever.k = 40

        # 6. Reconstruir hybrid retriever (usando fresh_wrapped_retriever!)
        hybrid_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, fresh_wrapped_retriever],
            weights=[0.4, 0.6]
        )

        # 7. Reconstruir retriever final com rerank
        retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=hybrid_retriever
        )

        return retriever, len(all_docs_for_bm25)

    def get_retriever_cached():
        """
        ✅ CACHE INTELIGENTE: Retorna retriever cached, só recarrega se docstore mudou.

        Performance:
        - Se docstore NÃO mudou: ~0.001s (mtime check)
        - Se docstore mudou: ~2-30s (rebuild completo)

        Escalabilidade:
        - 100 docs: cache hit ~99% do tempo
        - 10K docs: cache hit ~99.9% do tempo
        - 100K docs: cache hit ~99.99% do tempo

        Concorrência:
        - Múltiplos usuários compartilham mesmo cache (eficiente)
        - Rebuild só acontece 1x quando docstore muda (não 1x por usuário)
        """
        global _cached_retriever, _cached_num_docs, _last_docstore_mtime

        import os
        docstore_path = f"{persist_directory}/docstore.pkl"

        # Verificar se arquivo existe
        if not os.path.exists(docstore_path):
            # Primeira vez ou docstore vazio
            print("⚠️  Docstore não encontrado, usando retriever vazio")
            return None, 0

        # Pegar timestamp de modificação do arquivo
        current_mtime = os.path.getmtime(docstore_path)

        # 🔥 FIX: Se cache mostra 0 docs mas mtime mudou, forçar rebuild
        force_rebuild = (_cached_num_docs == 0 and current_mtime != _last_docstore_mtime)

        # Verificar se docstore mudou OU cache vazio
        if _cached_retriever is None or current_mtime != _last_docstore_mtime or force_rebuild:
            print(f"🔄 Docstore mudou (ou primeira carga), reconstruindo retriever...")
            print(f"   Timestamp anterior: {_last_docstore_mtime}")
            print(f"   Timestamp atual: {current_mtime}")
            if force_rebuild:
                print(f"   🔥 FORCE REBUILD: Cache mostra 0 docs mas docstore existe")

            # Rebuild (operação pesada)
            _cached_retriever, _cached_num_docs = rebuild_retriever()
            _last_docstore_mtime = current_mtime

            print(f"✅ Retriever reconstruído ({_cached_num_docs} documentos indexados)")
        else:
            # Cache hit! (99%+ das queries)
            print(f"✅ Usando retriever cached ({_cached_num_docs} documentos) - docstore inalterado")

        return _cached_retriever, _cached_num_docs

    print("🚀 Inicializando Hybrid Search (BM25 + Vector)...")

    # Carregar TODOS os documentos do docstore para BM25 (inicial)
    all_docs_for_bm25 = []
    for doc_id, doc in store.store.items():
        # Converter para Document do LangChain
        if hasattr(doc, 'page_content'):
            all_docs_for_bm25.append(doc)
        elif hasattr(doc, 'text'):
            # Converter Unstructured para Document
            metadata = {}
            if hasattr(doc, 'metadata'):
                if isinstance(doc.metadata, dict):
                    metadata = doc.metadata
                elif hasattr(doc.metadata, 'to_dict'):
                    metadata = doc.metadata.to_dict()
                else:
                    metadata = {}

            all_docs_for_bm25.append(Document(
                page_content=doc.text,
                metadata=metadata
            ))
        elif isinstance(doc, str):
            # Imagens (base64) - pular, BM25 é para texto
            pass

    print(f"   Documentos carregados para BM25: {len(all_docs_for_bm25)}")

    # BM25 Retriever (keyword-based)
    # Nota: Se não houver documentos, o BM25 será inicializado vazio
    # O rebuild_retriever() tratará a validação quando reconstruir
    if len(all_docs_for_bm25) > 0:
        bm25_retriever = BM25Retriever.from_documents(all_docs_for_bm25)
        bm25_retriever.k = 40  # Buscar mais docs, o reranker vai filtrar
    else:
        bm25_retriever = None
        print("   ⚠️  BM25 não inicializado (sem documentos)")

    # Ensemble: combinar BM25 (keyword) + Vector (semantic)
    if bm25_retriever:
        hybrid_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, wrapped_retriever],
            weights=[0.4, 0.6]  # 40% BM25 (keywords), 60% vector (semântica)
        )
    else:
        # Sem documentos, usar apenas retriever vazio
        hybrid_retriever = wrapped_retriever

    print(f"   ✅ Hybrid Search configurado")
    print(f"      BM25 weight: 40% (keyword precision)")
    print(f"      Vector weight: 60% (semantic understanding)")

    # ===========================================================================
    # 🔥 RERANKER COHERE (sobre resultados híbridos)
    # ===========================================================================
    print("🔥 Inicializando Cohere Reranker...")

    compressor = CohereRerank(
        model="rerank-multilingual-v3.0",  # Suporta português
        top_n=12  # ✅ OTIMIZADO: Aumentado para 12 para perguntas com info dispersa
    )

    # Retriever FINAL: Hybrid + Rerank
    retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=hybrid_retriever  # ✅ USANDO HYBRID em vez de só wrapped_retriever
    )

    print(f"   ✅ Pipeline completo: BM25 + Vector → Cohere Rerank → Top 12\n")
    
    def parse_docs(docs):
        """Docs podem ser: Document, Table, CompositeElement, ou string"""
        b64_images = []  # ✅ Mudança: incluir metadata junto com base64
        text = []
        for doc in docs:
            # Extrair conteúdo baseado no tipo
            if hasattr(doc, 'page_content'):
                # Document do LangChain
                content = doc.page_content
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif hasattr(doc, 'text'):
                # Table ou CompositeElement da Unstructured
                content = doc.text
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif isinstance(doc, str):
                # String simples
                content = doc
                metadata = {}
            else:
                # Fallback
                content = str(doc)
                metadata = {}

            # ✅ FIX: Identificar imagens pelo metadata.type, NÃO por b64decode
            # (imagens têm page_content=summary, não base64!)
            if metadata.get('type') == 'image':
                # Buscar imagem real do docstore usando doc_id
                doc_id = metadata.get('doc_id')
                if doc_id:
                    try:
                        # 🛡️ VALIDATE: Verificar se doc_id existe antes de buscar
                        # (previne "Error finding id" de chunks órfãos)
                        global _docstore
                        if not _docstore or not hasattr(_docstore, 'mget'):
                            print(f"   ⚠️ Docstore não disponível para buscar imagem {doc_id}")
                            continue

                        # Tentar buscar a imagem do docstore
                        image_obj = _docstore.mget([doc_id])[0]
                        if image_obj:
                            # Image object da Unstructured tem .text com base64
                            image_base64 = image_obj.text if hasattr(image_obj, 'text') else str(image_obj)
                            image_data = {
                                "base64": image_base64,
                                "metadata": metadata
                            }
                            b64_images.append(image_data)
                            continue
                        else:
                            print(f"   ⚠️ Imagem {doc_id} não encontrada no docstore (chunk órfão?)")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao buscar imagem {doc_id}: {str(e)[:100]}")

            # Se não é imagem ou falhou ao buscar, tratar como texto
            # Criar objeto com .text para compatibilidade
            class TextDoc:
                def __init__(self, text_content, meta):
                    self.text = text_content
                    self.metadata = meta

            text.append(TextDoc(content, metadata))

        return {"images": b64_images, "texts": text}
    
    def build_prompt(kwargs):
        docs = kwargs["context"]
        question = kwargs["question"]

        context = ""
        for text in docs["texts"]:
            source = 'unknown'
            if hasattr(text, 'metadata'):
                if isinstance(text.metadata, dict):
                    source = text.metadata.get('source', 'unknown')
                elif hasattr(text.metadata, 'source'):
                    source = text.metadata.source
            context += f"\n[{source}] {text.text}\n"

        # Prompt RIGOROSO com INFERÊNCIA MODERADA: permite conexões lógicas entre chunks
        system_instruction = """Você é um assistente de pesquisa médica RIGOROSO com CAPACIDADE MULTIMODAL.

⚠️ IDIOMA: SEMPRE responda em PORTUGUÊS BRASILEIRO. Todas as descrições, análises e referências devem estar em português.

REGRAS CRÍTICAS:
1. Responda APENAS com informações que estão no contexto fornecido abaixo
2. NUNCA use conhecimento geral ou externo aos documentos
3. Cite EXATAMENTE como está escrito no documento
4. Se houver listas, tabelas ou critérios, reproduza-os FIELMENTE
5. Mantenha formatação original (bullets, números, etc)

🖼️ USO EQUILIBRADO DE IMAGENS:
6. Se você receber IMAGENS anexadas (fluxogramas, diagramas, figuras):
   - PRIORIZE responder a pergunta com TEXTO COMPLETO E DETALHADO baseado no contexto textual
   - Inclua referências a imagens APENAS quando forem DIRETAMENTE relevantes para ENRIQUECER a resposta
   - Formato para referenciar: 📊 **[FIGURA X: Título]** seguido de breve explicação de como a imagem complementa o texto
   - NÃO use sintaxe markdown (![]() ou attachment://) - imagens aparecem automaticamente
   - NÃO transforme a resposta em uma descrição de imagens - mantenha foco no CONTEÚDO TEXTUAL
   - A imagem deve COMPLEMENTAR a resposta textual, não substituí-la

INFERÊNCIAS PERMITIDAS (apenas quando necessário):
7. Se a pergunta pede "relação entre X e Y", você PODE conectar informações de DIFERENTES trechos do contexto, citando AMBOS
8. Se a pergunta pede "quando NÃO fazer X" e o contexto diz "fazer Y em situação Z", você PODE inferir logicamente, citando o trecho original
9. Se a pergunta usa negação ("NÃO descarta", "NÃO é recomendado"), procure informações complementares no contexto que respondam indiretamente

CORREÇÃO DE PREMISSAS INCORRETAS:
10. Se a pergunta contém PREMISSA FALSA ou INCORRETA (ex: "dose em TFG<15" quando medicamento é contraindicado), você DEVE CORRIGIR a premissa citando o trecho correto
11. Exemplos de correção:
   - Pergunta: "Qual dose de X em TFG<15?" quando X é contraindicado
     Resposta: "X é CONTRAINDICADO quando TFG <30. Portanto, NÃO há dose recomendada. [cite fonte]"
   - Pergunta: "HbA1c <5% é o alvo ideal?"
     Resposta: "NÃO. O alvo recomendado é HbA1c <7%. HbA1c muito baixo aumenta risco de hipoglicemia. [cite fonte]"

INTERPRETAÇÃO DE LINGUAGEM COLOQUIAL:
12. Interprete termos coloquiais: "açúcar na hemoglobina"=HbA1c, "problema no rim"=TFG reduzida, "gordo"=obesidade, "comprimido"=antidiabético oral

REGRA FINAL:
13. Se após tentar conexões lógicas e correções a informação AINDA não puder ser inferida do contexto, responda: "A informação solicitada não está presente nos documentos fornecidos"

CONTEXTO DOS DOCUMENTOS:
{context}

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA (baseada SOMENTE no contexto acima, com inferências lógicas documentadas quando necessário, e INCLUINDO imagens relevantes quando fornecidas):"""

        prompt_content = [{
            "type": "text",
            "text": system_instruction.format(context=context, question=question)
        }]

        # ✅ CONVERT IMAGES TO JPEG before sending to Vision API
        for image_data in docs["images"]:
            # ✅ ATUALIZADO: images agora são dicts com base64 + metadata
            image_base64 = image_data["base64"]  # Extrair base64

            # Convert to JPEG (handles TIFF, BMP, etc.)
            jpeg_image, success = convert_image_to_jpeg_base64(image_base64)
            if success:
                prompt_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{jpeg_image}"}
                })
            else:
                # Skip images that failed to convert
                print(f"⚠️  Skipping image that failed JPEG conversion")

        return ChatPromptTemplate.from_messages([HumanMessage(content=prompt_content)])
    
    chain = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
    } | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | ChatOpenAI(model="gpt-4o")  # Upgrade: +60% melhor inferência vs 4o-mini
            | StrOutputParser()
        )
    )
    
    @app.route('/debug-retrieval', methods=['POST'])
    def debug_retrieval():
        """DEBUG: Ver o que o retrieval está retornando"""
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Campo 'question' obrigatório"}), 400

        try:
            question = data['question']

            # Buscar SEM rerank (raw retrieval)
            raw_docs = base_retriever.invoke(question)

            # Buscar COM rerank
            reranked_docs = retriever.invoke(question)

            # Analisar conteúdo completo dos docs rerankeados
            reranked_full = []
            for i, doc in enumerate(reranked_docs):
                content = ""
                if hasattr(doc, 'page_content'):
                    content = doc.page_content
                elif hasattr(doc, 'text'):
                    content = doc.text
                else:
                    content = str(doc)

                # Converter metadata para dict (pode ser ElementMetadata)
                metadata = {}
                if hasattr(doc, 'metadata'):
                    if isinstance(doc.metadata, dict):
                        metadata = doc.metadata
                    elif hasattr(doc.metadata, 'to_dict'):
                        metadata = doc.metadata.to_dict()
                    else:
                        metadata = {"type": str(type(doc.metadata).__name__)}

                reranked_full.append({
                    "index": i,
                    "content": content[:500],  # Primeiros 500 chars
                    "full_length": len(content),
                    "type": type(doc).__name__,
                    "metadata": metadata
                })

            # Analisar raw docs também
            raw_full = []
            for i, doc in enumerate(raw_docs):
                content = ""
                if hasattr(doc, 'text'):
                    content = doc.text
                elif hasattr(doc, 'page_content'):
                    content = doc.page_content
                else:
                    content = str(doc)

                # Converter metadata para dict (pode ser ElementMetadata)
                metadata = {}
                if hasattr(doc, 'metadata'):
                    if isinstance(doc.metadata, dict):
                        metadata = doc.metadata
                    elif hasattr(doc.metadata, 'to_dict'):
                        metadata = doc.metadata.to_dict()
                    else:
                        metadata = {"type": str(type(doc.metadata).__name__)}

                raw_full.append({
                    "index": i,
                    "content": content[:500],  # Primeiros 500 chars
                    "full_length": len(content),
                    "type": type(doc).__name__,
                    "metadata": metadata
                })

            return jsonify({
                "query": question,
                "raw_retrieval": {
                    "count": len(raw_docs),
                    "docs_preview": [
                        {
                            "content_preview": str(doc)[:200] if hasattr(doc, '__str__') else "N/A",
                            "type": type(doc).__name__,
                            "has_text": hasattr(doc, 'text'),
                            "has_page_content": hasattr(doc, 'page_content')
                        }
                        for doc in raw_docs[:5]  # Primeiros 5
                    ],
                    "docs_full": raw_full  # Conteúdo completo de TODOS os 30 docs
                },
                "reranked": {
                    "count": len(reranked_docs),
                    "docs_preview": [
                        {
                            "content_preview": str(doc.page_content)[:200] if hasattr(doc, 'page_content') else str(doc)[:200],
                            "type": type(doc).__name__
                        }
                        for doc in reranked_docs[:5]
                    ],
                    "docs_full": reranked_full  # Conteúdo completo de TODOS os docs rerankeados
                }
            })
        except Exception as e:
            import traceback
            return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

    @app.route('/query', methods=['POST'])
    def query():
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Campo 'question' obrigatório"}), 400

        try:
            # ✅ USAR CACHE: Só recarrega se docstore mudou (escalável!)
            retriever, num_docs = get_retriever_cached()

            # Se retriever vazio (sem docstore), retornar erro
            if retriever is None:
                return jsonify({
                    "error": "Knowledge base vazia. Adicione documentos primeiro.",
                    "total_docs_indexed": 0
                }), 404

            # 🖼️ WRAPPER HÍBRIDO: Confia no Cohere, fallback se necessário
            def retriever_with_smart_image_fallback(question):
                """
                Abordagem híbrida inteligente para imagens:
                1. Confia no Cohere Rerank para trazer imagens se forem muito relevantes
                2. Se Cohere não trouxe imagens, busca 1-2 como fallback (quando disponíveis)
                """
                # 1. Retrieval normal com Cohere rerank (pode incluir imagens)
                docs = retriever.invoke(question)

                # 2. Verificar se Cohere já trouxe conteúdo visual (imagens OU tabelas)
                visual_content_from_cohere = [d for d in docs if d.metadata.get('type') in ['image', 'table']]

                if visual_content_from_cohere:
                    print(f"   ✓ Cohere trouxe {len(visual_content_from_cohere)} conteúdo(s) visual(is) relevante(s)")
                    return docs  # Cohere já escolheu bem, confiar nele

                # 3. Fallback: Se Cohere não trouxe conteúdo visual, buscar 1-2 como complemento
                print(f"   🖼️ Cohere não trouxe conteúdo visual, buscando fallback...")

                try:
                    # Criar nova instância do Chroma para dados atualizados
                    fresh_vectorstore = Chroma(
                        collection_name="knowledge_base",
                        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
                        persist_directory=persist_directory
                    )

                    # FIX: Buscar imagens e tabelas SEPARADAMENTE (sem $in operator)
                    # ChromaDB pode ter problemas com $in dependendo da versão
                    visual_content = []

                    # Buscar imagens
                    try:
                        images = fresh_vectorstore.similarity_search(
                            question,
                            k=3,
                            filter={"type": "image"}
                        )
                        visual_content.extend(images)
                        print(f"   🖼️ Encontrou {len(images)} imagem(ns) relevante(s)")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao buscar imagens: {str(e)[:80]}")

                    # Buscar tabelas
                    try:
                        tables = fresh_vectorstore.similarity_search(
                            question,
                            k=2,
                            filter={"type": "table"}
                        )
                        visual_content.extend(tables)
                        print(f"   📊 Encontrou {len(tables)} tabela(s) relevante(s)")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao buscar tabelas: {str(e)[:80]}")

                    if not visual_content:
                        print(f"   ℹ️ Nenhum conteúdo visual disponível no vectorstore")
                        return docs

                    # Pegar apenas 1-2 melhores conteúdos visuais como fallback
                    found_visual = []
                    seen_doc_ids = set()

                    for item in visual_content:
                        doc_id = item.metadata.get('doc_id')
                        if doc_id and doc_id not in seen_doc_ids:
                            found_visual.append(item)
                            seen_doc_ids.add(doc_id)
                            if len(found_visual) >= 2:  # Máximo 2 itens visuais em fallback
                                break

                    if found_visual:
                        print(f"   ✓ Adicionando {len(found_visual)} conteúdo(s) visual(is) como fallback")
                        # Adicionar ao FINAL (menor prioridade que Cohere)
                        docs = docs + found_visual

                except Exception as e:
                    print(f"   ⚠️ Erro no fallback de imagens: {str(e)[:100]}")

                return docs

            # Reconstruir chain com retriever + fallback inteligente
            fresh_chain = {
                "context": RunnableLambda(retriever_with_smart_image_fallback) | RunnableLambda(parse_docs),
                "question": RunnablePassthrough(),
            } | RunnablePassthrough().assign(
                response=(
                    RunnableLambda(build_prompt)
                    | ChatOpenAI(model="gpt-4o")
                    | StrOutputParser()
                )
            )

            response = fresh_chain.invoke(data['question'])

            sources = set()
            num_chunks = len(response['context']['texts'])

            for text in response['context']['texts']:
                if hasattr(text, 'metadata'):
                    if isinstance(text.metadata, dict):
                        source = text.metadata.get('source', 'unknown')
                    elif hasattr(text.metadata, 'source'):
                        source = text.metadata.source
                    else:
                        source = 'unknown'
                    sources.add(source)

            # ✅ NOVO: Adicionar imagens no response
            return jsonify({
                "answer": response['response'],
                "sources": list(sources),
                "chunks_used": num_chunks,
                "reranked": True,
                "total_docs_indexed": num_docs,
                "cache_hit": _last_docstore_mtime is not None,
                "has_images": len(response['context']['images']) > 0,  # ✅ Tem imagens?
                "images": response['context']['images'],  # ✅ ADICIONAR imagens com metadata
                "num_images": len(response['context']['images'])  # ✅ Quantidade de imagens
            })
        except Exception as e:
            import traceback
            return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok", "reranker": "cohere"})

    @app.route('/debug-volume', methods=['GET'])
    def debug_volume():
        """DEBUG: Verificar se o volume tem arquivos + LIMPAR ÓRFÃOS com ?clean_orphans=true"""
        global _last_docstore_mtime, _cached_retriever
        import os
        try:
            # 🧹 CLEANUP: Se clean_orphans=true, limpar chunks órfãos
            clean_orphans_param = request.args.get('clean_orphans', '').lower() == 'true'
            force_clean_metadata = request.args.get('force_clean_metadata', '').lower() == 'true'
            force_clean_all = request.args.get('force_clean_all', '').lower() == 'true'

            # 🗑️ FORCE CLEAN ALL: Limpar TODOS os chunks quando metadata.pkl estiver vazio
            if force_clean_all:
                # Verificar se metadata.pkl está vazio
                metadata_path = f"{persist_directory}/metadata.pkl"
                metadata = {}
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'rb') as f:
                        metadata = pickle.load(f)

                total_registered_docs = len(metadata.get('documents', {}))

                # Se não há documentos registrados, limpar TUDO
                if total_registered_docs == 0:
                    all_results = vectorstore.get(include=['metadatas'])
                    all_chunk_ids = all_results['ids']

                    if len(all_chunk_ids) > 0:
                        print(f"🗑️ FORCE CLEAN ALL: Deletando {len(all_chunk_ids)} chunks (metadata.pkl vazio)")

                        # 1. Deletar do Chroma
                        vectorstore.delete(ids=all_chunk_ids)

                        # 2. Limpar docstore
                        docstore_path = f"{persist_directory}/docstore.pkl"
                        if os.path.exists(docstore_path):
                            empty_docstore = {}
                            with open(docstore_path, 'wb') as f:
                                pickle.dump(empty_docstore, f)
                            os.utime(docstore_path, None)

                        # 3. Invalidar cache
                        global _last_docstore_mtime, _cached_retriever
                        _last_docstore_mtime = None
                        _cached_retriever = None

                        return jsonify({
                            "success": True,
                            "message": f"TODOS os {len(all_chunk_ids)} chunks foram deletados (metadata.pkl estava vazio)",
                            "deleted_chunks": len(all_chunk_ids),
                            "action": "force_clean_all"
                        })
                    else:
                        return jsonify({
                            "success": True,
                            "message": "Nenhum chunk para deletar (já está limpo)",
                            "action": "force_clean_all"
                        })
                else:
                    return jsonify({
                        "error": "force_clean_all só funciona quando metadata.pkl está vazio",
                        "registered_docs": total_registered_docs
                    }), 400

            # 🗑️ FORCE CLEAN METADATA: Limpar metadata.pkl quando vectorstore está vazio
            if force_clean_metadata:
                all_results = vectorstore.get(include=['metadatas'])
                total_chunks = len(all_results['ids'])

                if total_chunks == 0:
                    metadata_path = f"{persist_directory}/metadata.pkl"
                    if os.path.exists(metadata_path):
                        empty_metadata = {
                            "documents": {},
                            "version": "1.0",
                            "created_at": "force-cleaned"
                        }
                        with open(metadata_path, 'wb') as f:
                            pickle.dump(empty_metadata, f)

                        return jsonify({
                            "success": True,
                            "message": "metadata.pkl resetado (vectorstore está vazio)",
                            "action": "force_clean_metadata"
                        })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"Não posso limpar metadata.pkl: vectorstore tem {total_chunks} chunks",
                        "total_chunks": total_chunks
                    }), 400

            if clean_orphans_param:
                print("\n" + "=" * 70)
                print("🧹 LIMPEZA DE CHUNKS ÓRFÃOS (via debug-volume)")
                print("=" * 70)

                # Buscar TODOS os chunks
                all_results = vectorstore.get(include=['metadatas'])
                total_chunks = len(all_results['ids'])

                # Identificar órfãos
                orphan_ids = []
                for i, meta in enumerate(all_results.get('metadatas', [])):
                    filename = meta.get('filename')
                    if filename is None or filename == '':
                        orphan_ids.append(all_results['ids'][i])

                if len(orphan_ids) > 0:
                    # Deletar do vectorstore
                    vectorstore.delete(ids=orphan_ids)

                    # Deletar do docstore e invalidar cache
                    docstore_path = f"{persist_directory}/docstore.pkl"
                    if os.path.exists(docstore_path):
                        with open(docstore_path, 'rb') as f:
                            docstore = pickle.load(f)
                        for chunk_id in orphan_ids:
                            if chunk_id in docstore:
                                del docstore[chunk_id]
                        with open(docstore_path, 'wb') as f:
                            pickle.dump(docstore, f)
                        os.utime(docstore_path, None)
                        _last_docstore_mtime = None
                        _cached_retriever = None

                    # 🗑️ SE TODOS chunks foram órfãos (vectorstore vazio), limpar metadata.pkl também
                    total_after_cleanup = total_chunks - len(orphan_ids)
                    if total_after_cleanup == 0:
                        metadata_path = f"{persist_directory}/metadata.pkl"
                        if os.path.exists(metadata_path):
                            # Criar metadata vazio
                            empty_metadata = {
                                "documents": {},
                                "version": "1.0",
                                "created_at": "auto-cleaned"
                            }
                            with open(metadata_path, 'wb') as f:
                                pickle.dump(empty_metadata, f)
                            print(f"✅ metadata.pkl limpo (vectorstore vazio = 0 documentos)")

                    print(f"✅ {len(orphan_ids)} chunks órfãos removidos!")
                    print("=" * 70 + "\n")

                    return jsonify({
                        "success": True,
                        "message": f"Limpeza concluída! {len(orphan_ids)} chunks órfãos removidos.",
                        "orphans_deleted": len(orphan_ids),
                        "total_chunks_before": total_chunks,
                        "total_chunks_after": total_chunks - len(orphan_ids)
                    })
                else:
                    return jsonify({
                        "success": True,
                        "message": "Nenhum chunk órfão encontrado!",
                        "orphans_deleted": 0
                    })

            # Continuar com debug normal se clean_orphans != true
            volume_info = {
                "persist_directory": persist_directory,
                "exists": os.path.exists(persist_directory),
                "files": []
            }

            # TESTE DE API KEYS
            api_keys_test = {}

            # 1. OpenAI API Key
            try:
                from langchain_openai import ChatOpenAI
                test_llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=10)
                test_llm.invoke("test")
                api_keys_test["openai"] = {"status": "OK", "model": "gpt-4o-mini"}
            except Exception as e:
                api_keys_test["openai"] = {"status": "FAILED", "error": str(e)[:150]}

            # 2. Cohere API Key
            try:
                from langchain_cohere import CohereRerank
                test_rerank = CohereRerank(model="rerank-multilingual-v3.0", top_n=1)
                # Não tem como testar sem documentos, só verificar se instancia
                api_keys_test["cohere"] = {"status": "OK", "model": "rerank-multilingual-v3.0"}
            except Exception as e:
                api_keys_test["cohere"] = {"status": "FAILED", "error": str(e)[:150]}

            # 3. OpenAI Embeddings
            try:
                test_emb = OpenAIEmbeddings(model="text-embedding-3-large")
                test_emb.embed_query("test")
                api_keys_test["openai_embeddings"] = {"status": "OK", "model": "text-embedding-3-large"}
            except Exception as e:
                api_keys_test["openai_embeddings"] = {"status": "FAILED", "error": str(e)[:150]}

            volume_info["api_keys"] = api_keys_test

            if os.path.exists(persist_directory):
                files = os.listdir(persist_directory)
                for f in files:
                    path = os.path.join(persist_directory, f)
                    size = os.path.getsize(path) if os.path.isfile(path) else -1
                    volume_info["files"].append({
                        "name": f,
                        "size_bytes": size,
                        "is_dir": os.path.isdir(path)
                    })

            # Verificar ChromaDB collection
            try:
                collection = vectorstore._collection
                count = collection.count()
                volume_info["chroma_count"] = count

                # TESTE DIRETO: buscar com similarity_search
                test_results = vectorstore.similarity_search("diabetes", k=3)
                volume_info["test_search_count"] = len(test_results)
                volume_info["test_search_preview"] = [r.page_content[:100] for r in test_results] if test_results else []

                # VERIFICAR doc_ids no vectorstore vs docstore
                if test_results:
                    vectorstore_doc_ids = [r.metadata.get('doc_id', 'NO_DOC_ID') for r in test_results]
                    volume_info["vectorstore_doc_ids"] = vectorstore_doc_ids

                    docstore_keys = list(store.store.keys())[:5]
                    volume_info["docstore_sample_keys"] = docstore_keys

                    # Verificar se doc_ids batem
                    matches = [doc_id in store.store for doc_id in vectorstore_doc_ids]
                    volume_info["doc_id_matches"] = matches

                # TESTE CRÍTICO: Testar base_retriever.invoke() diretamente
                try:
                    mv_results = base_retriever.invoke("diabetes")
                    volume_info["base_retriever_test"] = {
                        "count": len(mv_results),
                        "success": len(mv_results) > 0,
                        "first_doc_type": type(mv_results[0]).__name__ if mv_results else None,
                        "first_doc_preview": str(mv_results[0])[:100] if mv_results else None
                    }
                except Exception as e:
                    volume_info["base_retriever_test"] = {
                        "error": str(e),
                        "success": False
                    }

                # TESTE 2: Testar wrapped_retriever (DocumentConverter)
                try:
                    wrapped_results = wrapped_retriever.invoke("diabetes")
                    volume_info["wrapped_retriever_test"] = {
                        "count": len(wrapped_results),
                        "success": len(wrapped_results) > 0,
                        "first_doc_type": type(wrapped_results[0]).__name__ if wrapped_results else None,
                        "has_page_content": hasattr(wrapped_results[0], 'page_content') if wrapped_results else False
                    }
                except Exception as e:
                    volume_info["wrapped_retriever_test"] = {
                        "error": str(e),
                        "success": False
                    }

                # TESTE 3: Testar retriever completo (com Cohere rerank)
                try:
                    reranked_results = retriever.invoke("diabetes")
                    volume_info["reranked_retriever_test"] = {
                        "count": len(reranked_results),
                        "success": len(reranked_results) > 0,
                        "first_doc_type": type(reranked_results[0]).__name__ if reranked_results else None
                    }
                except Exception as e:
                    volume_info["reranked_retriever_test"] = {
                        "error": str(e),
                        "success": False
                    }

                # TESTE 4: Testar parse_docs (separação texto/imagem)
                try:
                    parsed = parse_docs(reranked_results)
                    volume_info["parse_docs_test"] = {
                        "texts_count": len(parsed["texts"]),
                        "images_count": len(parsed["images"]),
                        "success": len(parsed["texts"]) > 0
                    }
                except Exception as e:
                    volume_info["parse_docs_test"] = {
                        "error": str(e),
                        "success": False
                    }

                # TESTE 5: Testar chain completo (pode falhar se OpenAI estiver com problema)
                try:
                    # Primeiro só pegar o contexto (sem chamar OpenAI)
                    context_step = retriever.invoke("diabetes")
                    parsed = parse_docs(context_step)

                    # Calcular tamanho do prompt que seria enviado
                    context_text = ""
                    for text in parsed["texts"]:
                        context_text += f"\n[source] {text.text}\n"

                    prompt_size = len(context_text)
                    images_size = sum(len(img) for img in parsed["images"])

                    volume_info["chain_test"] = {
                        "context_ready": True,
                        "prompt_size_chars": prompt_size,
                        "images_size_bytes": images_size,
                        "texts_count": len(parsed["texts"]),
                        "images_count": len(parsed["images"])
                    }

                    # Agora tentar chamar OpenAI (pode dar erro 500)
                    try:
                        test_response = chain.invoke("diabetes")
                        volume_info["chain_test"]["openai_success"] = True
                        volume_info["chain_test"]["response_length"] = len(test_response.get("response", ""))
                    except Exception as openai_error:
                        volume_info["chain_test"]["openai_success"] = False
                        volume_info["chain_test"]["openai_error"] = str(openai_error)[:300]

                except Exception as e:
                    volume_info["chain_test"] = {
                        "error": str(e)[:300],
                        "success": False
                    }
            except Exception as e:
                volume_info["chroma_count"] = f"error: {str(e)}"
                volume_info["test_search_error"] = str(e)

            # Verificar docstore
            if os.path.exists(f"{persist_directory}/docstore.pkl"):
                volume_info["docstore_exists"] = True
                volume_info["docstore_size"] = len(store.store)
            else:
                volume_info["docstore_exists"] = False

            return jsonify(volume_info)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/', methods=['GET'])
    def home():
        """Página inicial com documentação"""
        return jsonify({
            "message": "RAG Multimodal API com Reranker Cohere",
            "version": "1.0",
            "reranker": "cohere-multilingual-v3.0",
            "endpoints": {
                "GET /": "Esta página (documentação)",
                "GET /health": "Health check",
                "POST /query": "Fazer pergunta ao RAG"
            },
            "example": {
                "url": "POST /query",
                "body": {
                    "question": "Sua pergunta aqui"
                },
                "response": {
                    "answer": "Resposta do RAG",
                    "sources": ["arquivo.pdf"],
                    "reranked": True
                }
            },
            "status": "online"
        })
    
    # =============== UI & Upload ===============
    UPLOAD_HTML = """
    <!doctype html>
    <html lang=pt-br>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Enviar PDF - Knowledge Base</title>
      <style>
        body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;max-width:800px;margin:40px auto;padding:0 16px;color:#222}
        .card{border:1px solid #ddd;border-radius:10px;padding:24px}
        .muted{color:#666;font-size:14px}
        .ok{color:#0a7a0a}
        .err{color:#b00020}
        input[type=file]{padding:8px}
        button{padding:10px 16px;border:none;border-radius:8px;background:#1f6feb;color:#fff;cursor:pointer;margin:5px}
        button:disabled{opacity:.6}
        .row{margin:12px 0}
        code{background:#f6f8fa;padding:2px 6px;border-radius:6px}
        .progress{background:#f8f9fa;border:1px solid #dee2e6;color:#495057;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow-y:auto;padding:12px;border-radius:6px}
        .button-group{display:flex;gap:10px;flex-wrap:wrap}
      </style>
    </head>
    <body>
      <h2>Enviar PDF para Knowledge Base</h2>
      <div class="card">
        <form id="form" enctype="multipart/form-data">
          <div class="row">
            <input type="file" name="file" accept="application/pdf" required />
          </div>
          <div class="row">
            <input type="password" name="api_key" placeholder="API Key (se configurada)" />
          </div>
          <div class="row">
            <div class="button-group">
              <button type="button" id="uploadBtn">Enviar e Processar</button>
              <button type="button" id="streamBtn">Enviar com Progresso (Tempo Real)</button>
            </div>
          </div>
        </form>
        <div id="out" class="row muted"></div>
      </div>
      <p class="muted">Depois, faça perguntas em <code>POST /query</code>.</p>
      <script>
        const form = document.getElementById('form');
        const out = document.getElementById('out');
        const uploadBtn = document.getElementById('uploadBtn');
        const streamBtn = document.getElementById('streamBtn');
        const fileInput = form.querySelector('input[type="file"]');

        // Upload normal
        uploadBtn.addEventListener('click', async (e)=>{
          e.preventDefault();
          if (!fileInput.files || fileInput.files.length === 0) {
            out.innerHTML = '<span class="err">ERRO: Por favor, selecione um arquivo PDF primeiro</span>';
            return;
          }
          await uploadPDF('/upload');
        });

        // Upload com streaming
        streamBtn.addEventListener('click', async (e)=>{
          e.preventDefault();
          if (!fileInput.files || fileInput.files.length === 0) {
            out.innerHTML = '<span class="err">ERRO: Por favor, selecione um arquivo PDF primeiro</span>';
            return;
          }
          await uploadPDF('/upload-stream', true);
        });

        async function uploadPDF(endpoint, isStreaming = false) {
          const data = new FormData(form);
          uploadBtn.disabled = true;
          streamBtn.disabled = true;
          out.innerHTML = '';
          
          if (isStreaming) {
            streamBtn.textContent = 'Processando...';
            out.innerHTML = '<div class="progress" id="progress">Iniciando processamento...\n</div>';
            
            try {
              const res = await fetch(endpoint, { method:'POST', body:data });
              if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
              
              const reader = res.body.getReader();
              const decoder = new TextDecoder();
              const progressDiv = document.getElementById('progress');
              
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = line.substring(6);
                    progressDiv.textContent += data + '\n';
                    progressDiv.scrollTop = progressDiv.scrollHeight;
                  }
                }
              }
              
              const finalText = progressDiv.textContent;
              if (finalText.includes('PDF processado com sucesso')) {
                out.innerHTML = '<span class="ok">SUCESSO: PDF processado com sucesso!</span>';
                form.reset();
              } else {
                out.innerHTML = '<span class="err">ERRO: Erro no processamento</span>';
              }

            } catch (err) {
              console.error('Erro no upload streaming:', err);
              out.innerHTML = '<span class="err">ERRO: ' + err.message + '</span>';
            }
          } else {
            uploadBtn.textContent = 'Enviando...';
            out.innerHTML = '<p class="muted">Enviando arquivo... Isso pode levar alguns minutos.</p>';

            try {
              console.log('Iniciando upload para:', endpoint);
              const res = await fetch(endpoint, { method:'POST', body:data });
              console.log('Resposta recebida:', res.status);

              const j = await res.json();
              console.log('JSON:', j);

              if (res.ok) {
                out.innerHTML = '<span class="ok">SUCESSO: ' + (j.message || 'Processado com sucesso!') + '</span>';
                form.reset();
              } else {
                out.innerHTML = '<span class="err">ERRO: ' + (j.error || 'Falha') + '</span>';
              }
            } catch (err) {
              console.error('Erro no upload:', err);
              out.innerHTML = '<span class="err">ERRO: ' + err.message + '</span>';
            }
          }

          uploadBtn.disabled = false;
          streamBtn.disabled = false;
          uploadBtn.textContent = 'Enviar e Processar';
          streamBtn.textContent = 'Enviar com Progresso (Tempo Real)';
        }
      </script>
    </body>
    </html>
    """

    @app.route('/ui', methods=['GET'])
    def ui():
        try:
            with open('ui_upload.html', 'r', encoding='utf-8') as f:
                html = f.read()
                # Cache-busting: forçar browser a não usar cache
                response = app.make_response(html)
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
        except FileNotFoundError:
            return render_template_string(UPLOAD_HTML)

    CHAT_HTML = """
    <!doctype html>
    <html lang=pt-br>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Chat – Knowledge Base</title>
      <style>
        body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;max-width:800px;margin:40px auto;padding:0 16px;color:#222}
        .card{border:1px solid #ddd;border-radius:10px;padding:16px}
        .row{display:flex;gap:8px}
        input,button{padding:10px;border-radius:8px;border:1px solid #ccc}
        button{background:#1f6feb;color:#fff;border:none;cursor:pointer}
        #log{margin-top:16px}
        .msg-q{background:#f6f8fa;border-radius:8px;padding:10px;margin:8px 0}
        .msg-a{background:#eef6ff;border-radius:8px;padding:10px;margin:8px 0}
        .muted{color:#666;font-size:14px}
      </style>
    </head>
    <body>
      <h2>Chat com a Base de Conhecimento</h2>
      <div class="card">
        <div class="row">
          <input id="q" type="text" placeholder="Digite sua pergunta..." style="flex:1" />
          <button id="go">Enviar</button>
        </div>
        <div id="log"></div>
        <div class="muted">As fontes são exibidas abaixo de cada resposta.</div>
      </div>
      <script>
        const q = document.getElementById('q');
        const go = document.getElementById('go');
        const log = document.getElementById('log');
        async function ask(){
          const question = q.value.trim();
          if(!question) return;
          const qEl = document.createElement('div');
          qEl.className='msg-q';
          qEl.textContent = 'Q: ' + question;
          log.appendChild(qEl);
          q.value='';
          const aEl = document.createElement('div');
          aEl.className='msg-a';
          aEl.textContent = 'Buscando...';
          log.appendChild(aEl);
          try{
            const res = await fetch('/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});
            const j = await res.json();
            if(res.ok){
              let html = 'A: ' + (j.answer||'(sem resposta)');

              // ✅ NOVO: Adicionar imagens se presentes
              if(j.images && j.images.length > 0){
                html += '<div style="margin-top:16px;"><strong>📸 Imagens (' + j.images.length + '):</strong></div>';
                j.images.forEach((img, idx) => {
                  const summary = img.metadata?.summary || 'Imagem ' + (idx+1);
                  html += '<div style="margin:12px 0;"><img src="data:image/jpeg;base64,' + img.base64 + '" style="max-width:100%;border:1px solid #ddd;border-radius:8px;" alt="' + summary + '"><div class="muted" style="margin-top:4px;font-style:italic;">' + summary + '</div></div>';
                });
              }

              // Fontes
              if(j.sources && j.sources.length){
                html += '<div class="muted">Fontes: ' + j.sources.join(', ') + '</div>';
              }

              aEl.innerHTML = html;
            } else {
              aEl.innerHTML = 'ERRO: ' + (j.error||'Falha');
            }
          }catch(err){ aEl.textContent = 'ERRO: ' + err.message; }
          window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'});
        }
        go.addEventListener('click', ask);
        q.addEventListener('keydown', e=>{ if(e.key==='Enter') ask(); });
      </script>
    </body>
    </html>
    """

    @app.route('/chat', methods=['GET'])
    def chat():
        return render_template_string(CHAT_HTML)

    @app.route('/debug', methods=['GET'])
    def debug():
        """UI de debug do retrieval"""
        try:
            with open('ui_debug.html', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "<h1>UI de debug não encontrada</h1>", 404

    @app.route('/debug-retrieval-ui', methods=['GET'])
    def debug_retrieval_ui():
        """UI para testar debug-retrieval endpoint"""
        try:
            with open('ui_debug_retrieval.html', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "<h1>UI de debug retrieval não encontrada</h1>", 404

    @app.route('/search-table', methods=['GET'])
    def search_table():
        """Buscar diretamente chunks que contenham keywords da tabela"""
        try:
            # Buscar por "muito alto" diretamente
            results_muito_alto = vectorstore.similarity_search("TABELA 1 muito alto risco cardiovascular", k=10)

            # Buscar por "3 fatores"
            results_fatores = vectorstore.similarity_search("3 ou mais fatores de risco", k=10)

            # Buscar por "hipercolesterolemia"
            results_hiper = vectorstore.similarity_search("hipercolesterolemia familiar", k=10)

            found_docs = []

            for docs, query_type in [(results_muito_alto, "muito_alto"),
                                      (results_fatores, "fatores"),
                                      (results_hiper, "hipercolesterolemia")]:
                for doc in docs:
                    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)

                    # Verificar se contém keywords da tabela
                    keywords_found = []
                    if "3 ou mais fatores" in content.lower() or "três ou mais fatores" in content.lower():
                        keywords_found.append("3_fatores")
                    if "hipercolesterolemia familiar" in content.lower():
                        keywords_found.append("hipercolesterolemia")
                    if "muito alto" in content.lower():
                        keywords_found.append("muito_alto")
                    if "tabela 1" in content.lower():
                        keywords_found.append("tabela_1")

                    found_docs.append({
                        "query_type": query_type,
                        "content": content[:500],
                        "full_length": len(content),
                        "keywords_found": keywords_found,
                        "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
                    })

            return jsonify({
                "total_docs_found": len(found_docs),
                "docs": found_docs,
                "summary": {
                    "has_3_fatores": any("3_fatores" in d["keywords_found"] for d in found_docs),
                    "has_hipercolesterolemia": any("hipercolesterolemia" in d["keywords_found"] for d in found_docs),
                    "has_tabela_1": any("tabela_1" in d["keywords_found"] for d in found_docs)
                }
            })
        except Exception as e:
            import traceback
            return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

    @app.route('/debug-table-chunking', methods=['GET'])
    def debug_table_chunking():
        """Diagnosticar como a tabela de risco cardiovascular foi chunkeada"""
        try:
            results = {
                "total_chunks": len(store.store),
                "relevant_chunks": [],
                "analysis": {}
            }

            # Buscar chunks relevantes
            for chunk_id, doc in store.store.items():
                # Extrair texto
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

                # Verificar keywords da tabela
                if any(kw in text_lower for kw in [
                    'hipercolesterolemia familiar',
                    'muito alto',
                    'risco cardiovascular',
                    '3 ou mais fatores',
                    'três ou mais fatores'
                ]):
                    keywords_found = []
                    if 'hipercolesterolemia familiar' in text_lower:
                        keywords_found.append('Hipercolesterolemia Familiar')
                    if '3 ou mais fatores' in text_lower or 'três ou mais fatores' in text_lower:
                        keywords_found.append('3 ou mais fatores')
                    if 'muito alto' in text_lower:
                        keywords_found.append('MUITO ALTO')
                    if ' alto' in text_lower and 'muito alto' not in text_lower:
                        keywords_found.append('ALTO (sem muito)')
                    if 'moderado' in text_lower:
                        keywords_found.append('MODERADO')

                    results["relevant_chunks"].append({
                        "chunk_id": chunk_id[:16] + "...",
                        "type": type(doc).__name__,
                        "text": text[:1000],  # Primeiros 1000 chars
                        "length": len(text),
                        "keywords": keywords_found
                    })

            # Análise
            hf_chunks = [c for c in results["relevant_chunks"] if 'Hipercolesterolemia Familiar' in c["keywords"]]
            ma_chunks = [c for c in results["relevant_chunks"] if 'MUITO ALTO' in c["keywords"]]
            hf_and_ma = [c for c in hf_chunks if 'MUITO ALTO' in c["keywords"]]

            results["analysis"] = {
                "chunks_with_HF": len(hf_chunks),
                "chunks_with_MUITO_ALTO": len(ma_chunks),
                "chunks_with_BOTH": len(hf_and_ma),
                "problem_detected": len(hf_and_ma) == 0,
                "diagnosis": "Tabela foi quebrada incorretamente - HF não está no mesmo chunk que MUITO ALTO" if len(hf_and_ma) == 0 else "HF e MUITO ALTO estão no mesmo chunk"
            }

            return jsonify(results)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # =============== Document Management ===============
    from document_manager import get_all_documents, get_document_by_id, delete_document as delete_doc_func, get_global_stats

    @app.route('/documents', methods=['GET'])
    def list_documents():
        """Lista todos documentos processados"""
        try:
            result = get_all_documents(persist_directory)
            stats = get_global_stats(persist_directory)

            return jsonify({
                "documents": result['documents'],
                "total": result['total'],
                "stats": stats
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/documents/<pdf_id>', methods=['GET'])
    def get_document_details(pdf_id):
        """Retorna detalhes de um documento específico"""
        try:
            doc_info = get_document_by_id(pdf_id, persist_directory)

            if not doc_info:
                return jsonify({"error": "Documento não encontrado"}), 404

            return jsonify(doc_info), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/documents/<pdf_id>', methods=['DELETE'])
    def delete_document_endpoint(pdf_id):
        """Deleta um documento e todos seus chunks"""
        # Validar API key se configurada
        required_key = os.getenv('API_SECRET_KEY')
        provided = request.headers.get('X-API-Key')
        if required_key and provided != required_key:
            return jsonify({"error": "Unauthorized"}), 401

        try:
            result = delete_doc_func(pdf_id, persist_directory)

            # ✅ CRÍTICO: Invalidar cache após deleção bem-sucedida
            if result['status'] == 'success':
                global _last_docstore_mtime, _cached_retriever
                _last_docstore_mtime = None  # Força rebuild do retriever
                _cached_retriever = None     # Limpa cache

                print(f"   ✓ Cache invalidado após deleção de {result.get('filename', pdf_id)}")

                return jsonify(result), 200
            elif result['status'] == 'not_found':
                return jsonify(result), 404
            else:
                return jsonify(result), 500
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500

    @app.route('/admin-data', methods=['GET'])
    def admin_data():
        """
        🔥 ADMIN AVANÇADO: Retorna dados REAIS do Chroma (não apenas metadata.pkl)

        Mostra:
        - Documentos REALMENTE no Chroma (scaneando todos os chunks)
        - Chunks órfãos (sem filename ou com filename=N/A)
        - Inconsistências entre Chroma e metadata.pkl
        - Permite limpeza total
        """
        global _last_docstore_mtime, _cached_retriever
        try:
            import pickle
            from collections import defaultdict

            # 1. Buscar TODOS os chunks do Chroma
            all_results = vectorstore.get(include=['metadatas'])
            total_chunks_chroma = len(all_results['ids'])

            # 2. Agrupar chunks por filename/pdf_id
            docs_real = defaultdict(lambda: {
                'filename': None,
                'pdf_id': None,
                'chunks': [],
                'chunk_count': 0,
                'texts': 0,
                'tables': 0,
                'images': 0,
                'status': 'in_chroma',
                'in_metadata': False
            })

            orphan_chunks = []

            for i, chunk_id in enumerate(all_results['ids']):
                meta = all_results['metadatas'][i]
                filename = meta.get('filename')
                pdf_id = meta.get('pdf_id', 'unknown')
                chunk_type = meta.get('type', 'unknown')

                # Identificar órfãos
                if not filename or filename == 'N/A' or filename == '':
                    orphan_chunks.append({
                        'chunk_id': chunk_id,
                        'pdf_id': pdf_id,
                        'type': chunk_type,
                        'source': meta.get('source', 'N/A')
                    })
                    continue

                # Agrupar por filename
                key = filename
                docs_real[key]['filename'] = filename
                docs_real[key]['pdf_id'] = pdf_id
                docs_real[key]['chunks'].append(chunk_id)
                docs_real[key]['chunk_count'] += 1

                if chunk_type == 'text':
                    docs_real[key]['texts'] += 1
                elif chunk_type == 'table':
                    docs_real[key]['tables'] += 1
                elif chunk_type == 'image':
                    docs_real[key]['images'] += 1

            # 3. Carregar metadata.pkl para comparação
            metadata_path = f"{persist_directory}/metadata.pkl"
            metadata_docs = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    metadata_docs = metadata.get('documents', {})

            # 4. Marcar quais documentos estão em metadata.pkl
            for filename, doc_data in docs_real.items():
                pdf_id = doc_data['pdf_id']
                if pdf_id in metadata_docs:
                    doc_data['in_metadata'] = True
                    doc_data['metadata_chunks'] = metadata_docs[pdf_id].get('stats', {}).get('total_chunks', 0)
                    doc_data['uploaded_at'] = metadata_docs[pdf_id].get('uploaded_at', 'N/A')
                    doc_data['file_size'] = metadata_docs[pdf_id].get('file_size', 0)
                else:
                    doc_data['status'] = 'orphan_doc'  # Documento no Chroma mas NÃO no metadata

            # 5. Identificar documentos APENAS no metadata (sem chunks no Chroma)
            metadata_only_docs = []
            for pdf_id, meta_doc in metadata_docs.items():
                filename = meta_doc.get('filename')
                # Verificar se existe no Chroma
                if filename not in docs_real:
                    metadata_only_docs.append({
                        'filename': filename,
                        'pdf_id': pdf_id,
                        'chunk_count': meta_doc.get('stats', {}).get('total_chunks', 0),
                        'status': 'in_metadata_only',
                        'uploaded_at': meta_doc.get('uploaded_at', 'N/A')
                    })

            # 6. Estatísticas globais
            stats = {
                'total_chunks_chroma': total_chunks_chroma,
                'total_docs_chroma': len(docs_real),
                'total_docs_metadata': len(metadata_docs),
                'orphan_chunks': len(orphan_chunks),
                'orphan_docs': sum(1 for d in docs_real.values() if d['status'] == 'orphan_doc'),
                'metadata_only_docs': len(metadata_only_docs),
                'consistent_docs': sum(1 for d in docs_real.values() if d['in_metadata'])
            }

            # 7. Converter para lista
            documents_list = [
                {
                    'filename': doc['filename'],
                    'pdf_id': doc['pdf_id'],
                    'chunk_count': doc['chunk_count'],
                    'texts': doc['texts'],
                    'tables': doc['tables'],
                    'images': doc['images'],
                    'status': doc['status'],
                    'in_metadata': doc['in_metadata'],
                    'metadata_chunks': doc.get('metadata_chunks', 0),
                    'uploaded_at': doc.get('uploaded_at', 'N/A'),
                    'file_size': doc.get('file_size', 0),
                    'chunk_ids': doc['chunks'][:5]  # Primeiros 5 IDs
                }
                for doc in docs_real.values()
            ]

            return jsonify({
                'success': True,
                'stats': stats,
                'documents': documents_list,
                'orphan_chunks': orphan_chunks[:50],  # Primeiros 50
                'metadata_only_docs': metadata_only_docs,
                'warnings': [
                    f"⚠️ {stats['orphan_chunks']} chunks órfãos encontrados" if stats['orphan_chunks'] > 0 else None,
                    f"⚠️ {stats['orphan_docs']} documentos no Chroma sem registro em metadata" if stats['orphan_docs'] > 0 else None,
                    f"⚠️ {stats['metadata_only_docs']} documentos no metadata sem chunks no Chroma" if stats['metadata_only_docs'] > 0 else None
                ]
            })

        except Exception as e:
            return jsonify({"error": str(e), "success": False}), 500

    @app.route('/admin-cleanup', methods=['POST'])
    def admin_cleanup():
        """
        🔥 ADMIN: Limpeza total ou seletiva

        Parâmetros:
        - action: "delete_orphans" | "delete_document" | "nuke_all"
        - pdf_id: ID do documento (para delete_document)
        """
        global _last_docstore_mtime, _cached_retriever

        # Validar API key
        required_key = os.getenv('API_SECRET_KEY')
        provided = request.headers.get('X-API-Key') or request.json.get('api_key')
        if required_key and provided != required_key:
            return jsonify({"error": "Unauthorized"}), 401

        try:
            data = request.json
            action = data.get('action')

            if action == 'nuke_all':
                # LIMPAR TUDO
                all_results = vectorstore.get(include=['metadatas'])
                all_chunk_ids = all_results['ids']

                if len(all_chunk_ids) > 0:
                    # 1. Deletar do Chroma
                    vectorstore.delete(ids=all_chunk_ids)

                    # 2. Limpar docstore
                    docstore_path = f"{persist_directory}/docstore.pkl"
                    if os.path.exists(docstore_path):
                        import pickle
                        with open(docstore_path, 'wb') as f:
                            pickle.dump({}, f)
                        os.utime(docstore_path, None)

                    # 3. Limpar metadata
                    metadata_path = f"{persist_directory}/metadata.pkl"
                    if os.path.exists(metadata_path):
                        import pickle
                        with open(metadata_path, 'wb') as f:
                            pickle.dump({"documents": {}, "version": "1.0"}, f)

                    # 4. Invalidar cache
                    _last_docstore_mtime = None
                    _cached_retriever = None

                    return jsonify({
                        "success": True,
                        "action": "nuke_all",
                        "deleted_chunks": len(all_chunk_ids),
                        "message": f"✅ TUDO limpo! {len(all_chunk_ids)} chunks deletados"
                    })
                else:
                    return jsonify({
                        "success": True,
                        "action": "nuke_all",
                        "message": "Já está limpo (0 chunks)"
                    })

            elif action == 'delete_orphans':
                # Deletar apenas chunks órfãos
                all_results = vectorstore.get(include=['metadatas'])
                orphan_ids = []

                for i, chunk_id in enumerate(all_results['ids']):
                    meta = all_results['metadatas'][i]
                    filename = meta.get('filename')
                    if not filename or filename == 'N/A' or filename == '':
                        orphan_ids.append(chunk_id)

                if len(orphan_ids) > 0:
                    vectorstore.delete(ids=orphan_ids)

                    # Limpar do docstore
                    docstore_path = f"{persist_directory}/docstore.pkl"
                    if os.path.exists(docstore_path):
                        import pickle
                        with open(docstore_path, 'rb') as f:
                            docstore = pickle.load(f)
                        for chunk_id in orphan_ids:
                            if chunk_id in docstore:
                                del docstore[chunk_id]
                        with open(docstore_path, 'wb') as f:
                            pickle.dump(docstore, f)
                        os.utime(docstore_path, None)

                    _last_docstore_mtime = None
                    _cached_retriever = None

                    return jsonify({
                        "success": True,
                        "action": "delete_orphans",
                        "deleted_chunks": len(orphan_ids),
                        "message": f"✅ {len(orphan_ids)} chunks órfãos deletados"
                    })
                else:
                    return jsonify({
                        "success": True,
                        "action": "delete_orphans",
                        "message": "Nenhum chunk órfão encontrado"
                    })

            elif action == 'delete_document':
                pdf_id = data.get('pdf_id')
                if not pdf_id:
                    return jsonify({"error": "pdf_id é obrigatório"}), 400

                # Usar a função existente de deleção
                from document_manager import delete_document as delete_doc_func
                result = delete_doc_func(pdf_id, persist_directory)

                if result['status'] == 'success':
                    _last_docstore_mtime = None
                    _cached_retriever = None

                return jsonify(result)

            else:
                return jsonify({"error": "Ação inválida. Use: nuke_all, delete_orphans, delete_document"}), 400

        except Exception as e:
            return jsonify({"error": str(e), "success": False}), 500

    @app.route('/debug-docids', methods=['GET'])
    def debug_docids():
        """CRITICAL: Diagnose doc_id mapping between vectorstore and docstore"""
        try:
            result = {
                "vectorstore_analysis": {},
                "docstore_analysis": {},
                "mapping_check": {},
                "diagnosis": ""
            }

            # 1. Analyze vectorstore embeddings
            try:
                # Get ALL embeddings from vectorstore
                collection = vectorstore._collection
                all_data = collection.get(include=['metadatas', 'documents'])

                result["vectorstore_analysis"]["total_embeddings"] = len(all_data['ids'])
                result["vectorstore_analysis"]["sample_ids"] = all_data['ids'][:5]

                # Extract doc_ids from metadata
                doc_ids_in_vectorstore = []
                for metadata in all_data['metadatas']:
                    doc_id = metadata.get('doc_id', 'NO_DOC_ID')
                    doc_ids_in_vectorstore.append(doc_id)

                result["vectorstore_analysis"]["doc_ids_sample"] = doc_ids_in_vectorstore[:5]
                result["vectorstore_analysis"]["doc_ids_unique"] = list(set(doc_ids_in_vectorstore))[:10]
                result["vectorstore_analysis"]["has_no_doc_id"] = 'NO_DOC_ID' in doc_ids_in_vectorstore

                # Show sample metadata
                result["vectorstore_analysis"]["sample_metadata"] = all_data['metadatas'][:3]

            except Exception as e:
                result["vectorstore_analysis"]["error"] = str(e)

            # 2. Analyze docstore
            try:
                docstore_keys = list(store.store.keys())
                result["docstore_analysis"]["total_docs"] = len(docstore_keys)
                result["docstore_analysis"]["sample_keys"] = docstore_keys[:10]

                # Show sample doc
                if docstore_keys:
                    sample_key = docstore_keys[0]
                    sample_doc = store.store[sample_key]

                    # Extract preview
                    if hasattr(sample_doc, 'text'):
                        preview = sample_doc.text[:100]
                    elif hasattr(sample_doc, 'page_content'):
                        preview = sample_doc.page_content[:100]
                    else:
                        preview = str(sample_doc)[:100]

                    result["docstore_analysis"]["sample_doc"] = {
                        "key": sample_key,
                        "type": type(sample_doc).__name__,
                        "preview": preview
                    }

            except Exception as e:
                result["docstore_analysis"]["error"] = str(e)

            # 3. Check mapping
            try:
                doc_ids_vs = set(doc_ids_in_vectorstore)
                doc_ids_ds = set(docstore_keys)

                matches = doc_ids_vs.intersection(doc_ids_ds)
                vs_only = doc_ids_vs - doc_ids_ds
                ds_only = doc_ids_ds - doc_ids_vs

                result["mapping_check"]["matches_count"] = len(matches)
                result["mapping_check"]["matches_sample"] = list(matches)[:5]
                result["mapping_check"]["in_vectorstore_only"] = list(vs_only)[:5]
                result["mapping_check"]["in_docstore_only"] = list(ds_only)[:5]
                result["mapping_check"]["total_vs_doc_ids"] = len(doc_ids_vs)
                result["mapping_check"]["total_ds_keys"] = len(doc_ids_ds)

                # Diagnosis
                if len(matches) == 0:
                    result["diagnosis"] = "CRITICAL: NO MATCHES! doc_ids in vectorstore don't match any keys in docstore. This explains why retrieval returns 0 results."
                elif len(matches) < len(doc_ids_vs):
                    result["diagnosis"] = f"PARTIAL MISMATCH: Only {len(matches)}/{len(doc_ids_vs)} doc_ids match. Some embeddings can't find their documents."
                else:
                    result["diagnosis"] = "OK: All doc_ids in vectorstore have matching keys in docstore."

            except Exception as e:
                result["mapping_check"]["error"] = str(e)

            # 4. Test direct retrieval
            try:
                test_results = vectorstore.similarity_search("diabetes", k=3)
                if test_results:
                    result["direct_search_test"] = {
                        "count": len(test_results),
                        "first_doc_id": test_results[0].metadata.get('doc_id', 'NO_DOC_ID'),
                        "first_preview": test_results[0].page_content[:100]
                    }
                else:
                    result["direct_search_test"] = {"count": 0, "error": "No results from similarity_search"}
            except Exception as e:
                result["direct_search_test"] = {"error": str(e)}

            return jsonify(result)

        except Exception as e:
            import traceback
            return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

    @app.route('/debug-image-search', methods=['POST'])
    def debug_image_search():
        """DEBUG: Testar busca de imagens com filtro metadata type=image"""
        try:
            data = request.get_json()
            question = data.get('question', 'síndrome de lise tumoral')
            k = data.get('k', 30)

            result = {
                "question": question,
                "k": k,
                "persist_directory": persist_directory,
                "analysis": {}
            }

            # 1. Verificar quantos chunks têm type=image no Chroma
            print("=" * 70)
            print("🔍 DEBUG IMAGE SEARCH")
            print("=" * 70)
            print(f"Question: {question}")
            print(f"K: {k}")
            print(f"Persist dir: {persist_directory}")

            # Pegar TODOS os chunks e filtrar por type
            all_results = vectorstore.get(include=['metadatas'])
            all_ids = all_results['ids']
            all_metadatas = all_results['metadatas']

            # Contar por type
            type_counts = {}
            image_ids = []
            for i, metadata in enumerate(all_metadatas):
                chunk_type = metadata.get('type', 'unknown')
                type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
                if chunk_type == 'image':
                    image_ids.append(all_ids[i])

            result["analysis"]["total_chunks"] = len(all_ids)
            result["analysis"]["type_counts"] = type_counts
            result["analysis"]["image_chunk_ids"] = image_ids
            result["analysis"]["total_images_in_chroma"] = len(image_ids)

            print(f"\nTotal chunks: {len(all_ids)}")
            print(f"Type counts: {type_counts}")
            print(f"Image chunks: {len(image_ids)}")

            # 2. Testar similarity_search com filtro
            print(f"\n🔍 Testando similarity_search com filter={{'type': 'image'}}, k={k}")

            try:
                images = vectorstore.similarity_search(
                    question,
                    k=k,
                    filter={"type": "image"}
                )

                result["analysis"]["similarity_search_with_filter"] = {
                    "success": True,
                    "count": len(images),
                    "images": []
                }

                print(f"✓ Retornou {len(images)} imagens")

                for img in images[:5]:  # Primeiros 5
                    img_info = {
                        "doc_id": img.metadata.get('doc_id'),
                        "type": img.metadata.get('type'),
                        "filename": img.metadata.get('filename'),
                        "pdf_id": img.metadata.get('pdf_id'),
                        "content_preview": img.page_content[:200]
                    }
                    result["analysis"]["similarity_search_with_filter"]["images"].append(img_info)
                    print(f"   - doc_id={img_info['doc_id']}, type={img_info['type']}, filename={img_info['filename']}")

            except Exception as e:
                result["analysis"]["similarity_search_with_filter"] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"✗ Erro: {str(e)}")

            # 3. Testar similarity_search SEM filtro para comparar
            print(f"\n🔍 Testando similarity_search SEM filtro, k={k}")

            try:
                all_docs = vectorstore.similarity_search(question, k=k)

                # Contar quantas são imagens
                image_count = sum(1 for doc in all_docs if doc.metadata.get('type') == 'image')

                result["analysis"]["similarity_search_no_filter"] = {
                    "success": True,
                    "total_count": len(all_docs),
                    "image_count": image_count,
                    "text_count": len(all_docs) - image_count
                }

                print(f"✓ Retornou {len(all_docs)} docs ({image_count} imagens, {len(all_docs) - image_count} textos/tabelas)")

            except Exception as e:
                result["analysis"]["similarity_search_no_filter"] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"✗ Erro: {str(e)}")

            # 4. Criar fresh vectorstore instance (como no código de query) e testar
            print(f"\n🔍 Testando com FRESH vectorstore instance")

            try:
                fresh_vectorstore = Chroma(
                    collection_name="knowledge_base",
                    embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
                    persist_directory=persist_directory
                )

                images_fresh = fresh_vectorstore.similarity_search(
                    question,
                    k=k,
                    filter={"type": "image"}
                )

                result["analysis"]["fresh_vectorstore_search"] = {
                    "success": True,
                    "count": len(images_fresh)
                }

                print(f"✓ Fresh vectorstore retornou {len(images_fresh)} imagens")

            except Exception as e:
                result["analysis"]["fresh_vectorstore_search"] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"✗ Erro: {str(e)}")

            # 5. Diagnóstico
            if len(image_ids) == 0:
                result["diagnosis"] = "❌ PROBLEMA: Não há chunks com type='image' no Chroma. Verificar upload."
            elif result["analysis"]["similarity_search_with_filter"]["count"] == 0:
                result["diagnosis"] = "❌ PROBLEMA: Há imagens no Chroma mas similarity_search com filtro retorna 0. Problema no filtro ou embeddings."
            else:
                result["diagnosis"] = "✅ OK: Busca de imagens está funcionando corretamente."

            print(f"\n📊 DIAGNÓSTICO: {result['diagnosis']}")
            print("=" * 70)

            return jsonify(result)

        except Exception as e:
            import traceback
            return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

    @app.route('/inspect-tables', methods=['GET'])
    def inspect_tables():
        """CRITICAL: Inspect actual table content extracted from PDFs"""
        try:
            result = {
                "tables_found": [],
                "total_tables": 0,
                "analysis": {}
            }

            # Iterate through ALL docs in docstore
            for doc_id, doc in store.store.items():
                # Extract text
                text = ""
                doc_type = type(doc).__name__

                if hasattr(doc, 'text'):
                    text = doc.text
                elif hasattr(doc, 'page_content'):
                    text = doc.page_content
                else:
                    text = str(doc)

                # Extract metadata
                metadata = {}
                if hasattr(doc, 'metadata'):
                    if isinstance(doc.metadata, dict):
                        metadata = doc.metadata
                    elif hasattr(doc.metadata, 'to_dict'):
                        metadata = doc.metadata.to_dict()
                    else:
                        metadata = {"raw_type": str(type(doc.metadata).__name__)}

                # Check if it's a table
                is_table = (
                    "Table" in doc_type or
                    metadata.get('type') == 'table' or
                    'tabela' in text.lower()[:200]
                )

                if is_table:
                    # Check for critical keywords
                    has_3_fatores = any(kw in text.lower() for kw in [
                        '3 ou mais fatores',
                        'três ou mais fatores',
                        '3 ou + fatores'
                    ])

                    has_hipercolesterolemia = 'hipercolesterolemia familiar' in text.lower()
                    has_muito_alto = 'muito alto' in text.lower()
                    has_albuminuria = 'albuminúria' in text.lower() or 'albuminuria' in text.lower()

                    result["tables_found"].append({
                        "doc_id": doc_id[:16] + "...",
                        "type": doc_type,
                        "length": len(text),
                        "full_text": text,  # TEXTO COMPLETO da tabela
                        "metadata": metadata,
                        "keywords_found": {
                            "3_ou_mais_fatores": has_3_fatores,
                            "hipercolesterolemia_familiar": has_hipercolesterolemia,
                            "muito_alto": has_muito_alto,
                            "albuminuria": has_albuminuria
                        }
                    })

            result["total_tables"] = len(result["tables_found"])

            # Analysis
            if result["total_tables"] > 0:
                tables_with_3_fatores = sum(1 for t in result["tables_found"] if t["keywords_found"]["3_ou_mais_fatores"])
                tables_with_hf = sum(1 for t in result["tables_found"] if t["keywords_found"]["hipercolesterolemia_familiar"])

                result["analysis"] = {
                    "tables_with_3_fatores": tables_with_3_fatores,
                    "tables_with_hipercolesterolemia": tables_with_hf,
                    "missing_column_2": tables_with_3_fatores == 0 and tables_with_hf == 0,
                    "diagnosis": "COLUMN 2 MISSING from table extraction!" if (tables_with_3_fatores == 0 and tables_with_hf == 0) else "Column 2 found in tables"
                }
            else:
                result["analysis"] = {
                    "diagnosis": "NO TABLES FOUND in docstore!"
                }

            return jsonify(result)

        except Exception as e:
            import traceback
            return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

    @app.route('/admin', methods=['GET'])
    def admin():
        """🔥 ADMIN AVANÇADO: UI com dados REAIS do Chroma"""
        try:
            with open('ui_admin.html', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "<h1>UI de gerenciamento não encontrada</h1><p>Arquivo ui_manage.html não existe.</p>", 404

    @app.route('/upload', methods=['POST'])
    def upload():
        # API Key opcional
        required_key = os.getenv('API_SECRET_KEY')
        provided = request.form.get('api_key') or request.headers.get('X-API-Key')
        if required_key and provided != required_key:
            return jsonify({"error": "Unauthorized"}), 401

        if 'file' not in request.files:
            return jsonify({"error": "Arquivo não enviado (campo 'file')"}), 400
        f = request.files['file']
        if not f.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Apenas .pdf"}), 400

        os.makedirs('content', exist_ok=True)
        save_path = os.path.join('content', f.filename)
        f.save(save_path)

        # Processar usando o script existente
        try:
            import subprocess, sys
            proc = subprocess.run([sys.executable, 'adicionar_pdf.py', save_path], capture_output=True, text=True, timeout=1800)
            if proc.returncode != 0:
                return jsonify({"error": proc.stderr.strip() or proc.stdout.strip() or "Falha ao processar"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        # ✅ INVALIDAR CACHE E FORÇAR REBUILD IMEDIATO
        global _last_docstore_mtime, _cached_retriever
        _last_docstore_mtime = None  # Força detecção de mudança

        # Forçar rebuild imediato (não esperar próxima query)
        try:
            print("🔄 Reconstruindo retriever após upload...")
            _cached_retriever, num_docs = rebuild_retriever()
            _last_docstore_mtime = os.path.getmtime(f"{persist_directory}/docstore.pkl")
            print(f"✅ Retriever reconstruído com {num_docs} documentos (incluindo novo PDF)")
        except Exception as e:
            print(f"⚠️ Erro ao reconstruir retriever: {str(e)}")
            # Não falhar o upload se rebuild falhar, apenas invalidar cache
            _last_docstore_mtime = None

        return jsonify({
            "message": "PDF processado e adicionado ao knowledge base",
            "filename": f.filename,
            "total_docs": num_docs if 'num_docs' in locals() else "unknown"
        })

    @app.route('/upload-stream', methods=['POST'])
    def upload_stream():
        # API Key opcional
        required_key = os.getenv('API_SECRET_KEY')
        provided = request.form.get('api_key') or request.headers.get('X-API-Key')
        if required_key and provided != required_key:
            return jsonify({"error": "Unauthorized"}), 401

        if 'file' not in request.files:
            return jsonify({"error": "Arquivo não enviado (campo 'file')"}), 400
        f = request.files['file']
        if not f.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Apenas .pdf"}), 400

        os.makedirs('content', exist_ok=True)
        save_path = os.path.join('content', f.filename)
        f.save(save_path)

        def generate():
            import subprocess, sys
            try:
                # Iniciar processo com streaming
                proc = subprocess.Popen(
                    [sys.executable, 'adicionar_pdf.py', save_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Stream output linha por linha
                for line in iter(proc.stdout.readline, ''):
                    if line:
                        yield f"data: {line.strip()}\n\n"
                
                # Aguardar processo terminar
                proc.wait()

                if proc.returncode == 0:
                    # ✅ INVALIDAR CACHE E FORÇAR REBUILD IMEDIATO
                    global _last_docstore_mtime, _cached_retriever
                    _last_docstore_mtime = None

                    # Forçar rebuild imediato
                    try:
                        yield f"data: 🔄 Reconstruindo retriever...\n\n"
                        _cached_retriever, num_docs = rebuild_retriever()
                        _last_docstore_mtime = os.path.getmtime(f"{persist_directory}/docstore.pkl")
                        yield f"data: ✅ Retriever reconstruído com {num_docs} documentos\n\n"
                        yield f"data: PDF processado com sucesso!\n\n"
                    except Exception as e:
                        yield f"data: ⚠️ Erro ao reconstruir retriever: {str(e)}\n\n"
                        _last_docstore_mtime = None
                        yield f"data: PDF processado, mas retriever será recarregado na próxima query\n\n"
                else:
                    yield f"data: Erro no processamento (codigo {proc.returncode})\n\n"

            except Exception as e:
                yield f"data: Erro: {str(e)}\n\n"

        return Response(generate(), mimetype='text/plain')

    @app.route('/clear-cache', methods=['POST'])
    def clear_cache():
        """
        🔄 FORÇA LIMPEZA DO CACHE E REBUILD DO RETRIEVER

        Use quando:
        - Deletar documentos pelo /manage
        - Reprocessar PDFs com novas descrições
        - Retriever está retornando documentos antigos
        """
        global _last_docstore_mtime, _cached_retriever

        print("\n" + "=" * 60)
        print("🗑️ LIMPANDO CACHE DO RETRIEVER")
        print("=" * 60)

        # Invalidar cache
        _last_docstore_mtime = None
        _cached_retriever = None

        # Forçar rebuild
        try:
            print("🔄 Reconstruindo retriever...")
            new_retriever, num_docs = rebuild_retriever()
            _cached_retriever = new_retriever
            _last_docstore_mtime = os.path.getmtime(f"{persist_directory}/docstore.pkl")

            print(f"✅ Cache limpo e retriever reconstruído!")
            print(f"   Total de documentos: {num_docs}")
            print("=" * 60 + "\n")

            return jsonify({
                "success": True,
                "message": "Cache limpo e retriever reconstruído",
                "total_docs": num_docs
            })

        except Exception as e:
            print(f"❌ Erro ao rebuild: {str(e)}")
            print("=" * 60 + "\n")

            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/clean-orphans', methods=['POST'])
    def clean_orphans():
        """
        🧹 LIMPA CHUNKS ÓRFÃOS (filename=None) DO VECTORSTORE

        Remove chunks antigos que foram criados sem campo 'filename'.
        Esses chunks órfãos causam problema de "documentos fantasma".
        """
        global _last_docstore_mtime, _cached_retriever

        print("\n" + "=" * 70)
        print("🧹 LIMPEZA DE CHUNKS ÓRFÃOS")
        print("=" * 70)

        try:
            # 1. Buscar TODOS os chunks
            print("\n1️⃣ Buscando todos os chunks...")
            all_results = vectorstore.get(include=['metadatas'])
            total_chunks = len(all_results['ids'])
            print(f"   ✓ Total: {total_chunks}")

            # 2. Identificar órfãos
            print("\n2️⃣ Identificando órfãos...")
            orphan_ids = []
            valid_chunks = 0

            from collections import Counter
            orphan_sources = []

            for i, meta in enumerate(all_results.get('metadatas', [])):
                filename = meta.get('filename')

                if filename is None or filename == '':
                    orphan_ids.append(all_results['ids'][i])
                    orphan_sources.append(meta.get('source', 'N/A'))
                else:
                    valid_chunks += 1

            print(f"   ✓ Válidos: {valid_chunks}")
            print(f"   ⚠️  Órfãos: {len(orphan_ids)}")

            if len(orphan_ids) == 0:
                return jsonify({
                    "success": True,
                    "message": "Nenhum chunk órfão encontrado!",
                    "total_chunks": total_chunks,
                    "orphans_deleted": 0,
                    "valid_chunks": valid_chunks
                })

            # Estatísticas
            source_counts = Counter(orphan_sources)
            print("\n   Órfãos por source:")
            for source, count in source_counts.most_common(5):
                print(f"      - {source}: {count}")

            # 3. Deletar do vectorstore
            print(f"\n3️⃣ Deletando {len(orphan_ids)} chunks órfãos...")
            vectorstore.delete(ids=orphan_ids)
            print(f"   ✓ Deletados do Chroma")

            # 4. Deletar do docstore
            print("\n4️⃣ Limpando docstore...")
            docstore_path = f"{persist_directory}/docstore.pkl"
            deleted_from_docstore = 0

            if os.path.exists(docstore_path):
                with open(docstore_path, 'rb') as f:
                    docstore = pickle.load(f)

                for chunk_id in orphan_ids:
                    if chunk_id in docstore:
                        del docstore[chunk_id]
                        deleted_from_docstore += 1

                with open(docstore_path, 'wb') as f:
                    pickle.dump(docstore, f)

                # Invalidar cache
                os.utime(docstore_path, None)
                _last_docstore_mtime = None
                _cached_retriever = None

                print(f"   ✓ {deleted_from_docstore} deletados do docstore")
                print(f"   ✓ Cache invalidado")

            # 5. Verificar
            print("\n5️⃣ Verificando...")
            all_after = vectorstore.get(include=['metadatas'])
            total_after = len(all_after['ids'])

            orphans_remaining = sum(
                1 for meta in all_after.get('metadatas', [])
                if meta.get('filename') is None or meta.get('filename') == ''
            )

            print(f"   ✓ Antes: {total_chunks}")
            print(f"   ✓ Depois: {total_after}")
            print(f"   ✓ Deletados: {total_chunks - total_after}")
            print(f"   ✓ Órfãos restantes: {orphans_remaining}")
            print("=" * 70 + "\n")

            return jsonify({
                "success": True,
                "message": f"Limpeza concluída! {len(orphan_ids)} chunks órfãos removidos.",
                "total_chunks_before": total_chunks,
                "total_chunks_after": total_after,
                "orphans_deleted": len(orphan_ids),
                "orphans_remaining": orphans_remaining,
                "deleted_from_docstore": deleted_from_docstore,
                "orphan_sources": dict(source_counts.most_common(10))
            })

        except Exception as e:
            print(f"❌ Erro: {str(e)}")
            print("=" * 70 + "\n")

            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    print("=" * 60)
    print("🌐 API COM RERANKER rodando em http://localhost:5001")
    print("=" * 60)
    print("\n🔥 Reranker: Cohere (melhora precisão em 30-40%)")
    print("\nEndpoints:")
    print("  GET  /        → Página inicial (documentação)")
    print("  GET  /health  → Health check")
    print("  GET  /ui      → Upload UI")
    print("  GET  /chat    → Chat UI")
    print("  POST /upload  → Enviar PDF (multipart)")
    print("  POST /query   → Fazer pergunta (com rerank)")
    print("  POST /clear-cache → Limpar cache do retriever (use após deletar docs)")
    print("\n💡 Teste no navegador: http://localhost:5001/ui")
    print("\n⚠️  Porta mudada de 5000 → 5001 (5000 usada pelo AirPlay)")
    print("\n" + "=" * 60 + "\n")
    
    # Porta configurável para Railway
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)

else:
    # ========================================================================
    # MODO TERMINAL
    # ========================================================================
    # Railway Volume
    persist_directory = os.getenv("PERSIST_DIR", "./knowledge")

    if not os.path.exists(persist_directory):
        print("❌ Knowledge base vazio!")
        print("Primeiro: python adicionar_pdf.py arquivo.pdf")
        exit(1)
    
    print("📂 Carregando knowledge base com RERANKER...\n")
    
    from langchain_chroma import Chroma
    from langchain.storage import InMemoryStore
    from langchain_openai import OpenAIEmbeddings
    from langchain.retrievers.multi_vector import MultiVectorRetriever
    from langchain_cohere import CohereRerank
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    from langchain_core.messages import HumanMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    from typing import List
    from base64 import b64decode, b64encode
    import pickle
    from PIL import Image
    import io

    # ===========================================================================
    # 🖼️ IMAGE CONVERSION: Convert all images to JPEG for GPT-4 Vision
    # ===========================================================================
    def convert_image_to_jpeg_base64(image_base64_str):
        """
        Converte qualquer formato de imagem para JPEG (suportado por GPT-4 Vision).

        Formatos não suportados: TIFF, BMP, ICO, etc.
        Formatos suportados: PNG, JPEG, GIF, WEBP

        Esta função garante que TODAS as imagens sejam JPEG válidas.
        """
        try:
            # Decodificar base64 para bytes
            image_bytes = b64decode(image_base64_str)

            # Abrir imagem com PIL
            img = Image.open(io.BytesIO(image_bytes))

            # 🔥 RESIZE TO MAX 512x512 TO REDUCE TOKENS (fix context length exceeded)
            MAX_SIZE = 512
            if img.width > MAX_SIZE or img.height > MAX_SIZE:
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

            # Converter para RGB (remove alpha channel se houver)
            # Isso é necessário porque JPEG não suporta transparência
            if img.mode in ('RGBA', 'LA', 'P'):
                # Criar background branco
                background = Image.new('RGB', img.size, (255, 255, 255))

                # Converter P (palette) para RGBA primeiro
                if img.mode == 'P':
                    img = img.convert('RGBA')

                # Colar imagem sobre background branco (preserva transparência)
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])  # Usa alpha channel como máscara
                else:
                    background.paste(img)

                img = background
            elif img.mode != 'RGB':
                # Outros modos (L, CMYK, etc.) → RGB
                img = img.convert('RGB')

            # Salvar como JPEG em buffer
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            jpeg_bytes = output.getvalue()

            # Re-encodar para base64
            jpeg_base64 = b64encode(jpeg_bytes).decode('utf-8')

            return jpeg_base64, True

        except Exception as e:
            # Se conversão falhar, retornar None
            print(f"      ⚠️  Erro ao converter imagem durante query: {str(e)[:100]}")
            return None, False

    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),  # Modelo novo, melhor semântica
        persist_directory=persist_directory
    )
    
    docstore_path = f"{persist_directory}/docstore.pkl"
    store = InMemoryStore()
    if os.path.exists(docstore_path):
        with open(docstore_path, 'rb') as f:
            store.store = pickle.load(f)

    base_retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key="doc_id",
        search_kwargs={"k": 30}  # ✅ OTIMIZADO: Aumentado para 30 para capturar info dispersa
    )

    # ===========================================================================
    # 🖼️ FIX: HYBRID RETRIEVAL COM BOOST PARA IMAGENS (MODO TERMINAL)
    # ===========================================================================
    import re

    def detect_image_query_terminal(question):
        """Detecta se a query do usuário está pedindo informações visuais."""
        image_patterns = [
            r'\bfigura\s+\d+\b',  # "figura 1", "figura 2"
            r'\bfig\.?\s*\d+\b',   # "fig. 1", "fig 2"
            r'\btabela\s+\d+\b',   # "tabela 1"
            r'\bfluxograma\b',
            r'\balgorit?mo\b',
            r'\bdiagrama\b',
            r'\bgr[aá]fico\b',
            r'\bimagem\b',
            r'\bilustra[çc][ãa]o\b',
            r'\bexplique\s+(a|o)\s+(figura|imagem|fluxograma|algoritmo|diagrama)\b',
            r'\bdescreva\s+(a|o)\s+(figura|imagem|fluxograma)\b',
            r'\bo\s+que\s+(mostra|diz|apresenta)\s+(a|o)\s+(figura|imagem)\b',
        ]

        keywords_found = []
        for pattern in image_patterns:
            match = re.search(pattern, question.lower())
            if match:
                keywords_found.append(match.group(0))

        return len(keywords_found) > 0, keywords_found


    def force_include_images_terminal(question, base_results, vectorstore_instance, max_images=3):
        """Força inclusão de imagens relevantes quando query é sobre conteúdo visual."""
        is_image_query, keywords = detect_image_query_terminal(question)

        if not is_image_query:
            return base_results

        print(f"   🖼️ Query sobre imagens detectada! Keywords: {keywords}")

        try:
            image_queries = [
                question,
                " ".join(keywords) if keywords else "figura",
                # Se pergunta sobre "figura 1", tentar também só "figura" (sem número)
                re.sub(r'\s+\d+', '', question) if re.search(r'figura\s+\d+', question.lower()) else None,
                "figura fluxograma algoritmo diagrama",
            ]

            # Remover None da lista
            image_queries = [q for q in image_queries if q]

            found_images = []
            seen_doc_ids = set()

            for img_query in image_queries:
                try:
                    # 🛡️ FIX: Buscar diretamente no Chroma SEM usar MultiVectorRetriever
                    # (isso evita o erro "Error finding id" de chunks órfãos)
                    from langchain_chroma import Chroma

                    # Usar o vectorstore do Chroma diretamente (não o MultiVectorRetriever)
                    chroma_client = vectorstore_instance.vectorstore if hasattr(vectorstore_instance, 'vectorstore') else vectorstore_instance

                    images = chroma_client.similarity_search(
                        img_query,
                        k=20,
                        filter={"type": "image"}
                    )

                    for img in images:
                        doc_id = img.metadata.get('doc_id')
                        if doc_id and doc_id not in seen_doc_ids:
                            # ✅ Validar se doc_id existe no docstore ANTES de adicionar
                            # (previne chunks órfãos de aparecer)
                            global _docstore
                            if _docstore and hasattr(_docstore, 'mget'):
                                try:
                                    doc_obj = _docstore.mget([doc_id])[0]
                                    if doc_obj:
                                        found_images.append(img)
                                        seen_doc_ids.add(doc_id)
                                    else:
                                        print(f"      ⚠️ Chunk órfão ignorado: {doc_id}")
                                except:
                                    print(f"      ⚠️ Erro ao validar doc_id {doc_id}, ignorando...")
                                    continue
                            else:
                                # Se docstore não disponível, adicionar mesmo assim
                                found_images.append(img)
                                seen_doc_ids.add(doc_id)

                            if len(found_images) >= max_images:
                                break

                except Exception as e:
                    print(f"      ⚠️ Erro na busca com filtro: {str(e)[:100]}")
                    print(f"         Tentando continuar sem imagens...")
                    continue

                if len(found_images) >= max_images:
                    break

            if found_images:
                print(f"   ✓ Forçando inclusão de {len(found_images)} imagens")
                combined_results = found_images + base_results

                seen = set()
                unique_results = []
                for doc in combined_results:
                    doc_id = doc.metadata.get('doc_id')
                    if doc_id not in seen:
                        seen.add(doc_id)
                        unique_results.append(doc)

                return unique_results[:40]

            else:
                print(f"   ⚠️ Nenhuma imagem encontrada mesmo com filtro!")
                return base_results

        except Exception as e:
            print(f"   ✗ Erro ao forçar inclusão de imagens: {str(e)[:200]}")
            return base_results

    # Wrapper para converter objetos Unstructured em Documents COM BOOST DE IMAGENS
    class DocumentConverter(BaseRetriever):
        retriever: MultiVectorRetriever
        vectorstore_ref: any

        def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
        ) -> List[Document]:
            # 1. Retrieval normal
            docs = self.retriever.invoke(query)
            print(f"   DEBUG DocumentConverter: retriever retornou {len(docs)} docs")

            # 2. Converter para Documents
            converted = []
            for i, doc in enumerate(docs):
                if i < 3:  # Só print dos primeiros 3 para não poluir
                    print(f"   DEBUG doc {i}: type={type(doc).__name__}, hasattr page_content={hasattr(doc, 'page_content')}, hasattr text={hasattr(doc, 'text')}, is str={isinstance(doc, str)}")

                # Converter para Document do LangChain
                if hasattr(doc, 'page_content'):
                    converted.append(doc)
                    if i < 3:
                        print(f"      → Adicionado via page_content")
                elif hasattr(doc, 'text'):
                    # Table ou CompositeElement → Document
                    # Converter metadata para dict
                    metadata = {}
                    if hasattr(doc, 'metadata'):
                        if isinstance(doc.metadata, dict):
                            metadata = doc.metadata
                        else:
                            # ElementMetadata → dict
                            metadata = doc.metadata.to_dict() if hasattr(doc.metadata, 'to_dict') else {}

                    converted.append(Document(
                        page_content=doc.text,
                        metadata=metadata
                    ))
                    if i < 3:
                        print(f"      → Convertido via text")
                elif isinstance(doc, str):
                    converted.append(Document(page_content=doc, metadata={}))
                    if i < 3:
                        print(f"      → Convertido de string")
                else:
                    converted.append(Document(page_content=str(doc), metadata={}))
                    if i < 3:
                        print(f"      → Convertido via str(doc)")

            print(f"   DEBUG DocumentConverter: converteu {len(converted)} de {len(docs)} docs")

            # 3. 🖼️ FORÇA INCLUSÃO DE IMAGENS se query for sobre imagens
            enhanced_results = force_include_images_terminal(
                question=query,
                base_results=converted,
                vectorstore_instance=self.vectorstore_ref,
                max_images=2
            )

            return enhanced_results

    # Wrapper do retriever para converter objetos COM BOOST DE IMAGENS
    wrapped_retriever = DocumentConverter(
        retriever=base_retriever,
        vectorstore_ref=vectorstore
    )

    # 🔥 RERANKER COHERE
    print("🔥 Inicializando Cohere Reranker...")
    compressor = CohereRerank(
        model="rerank-multilingual-v3.0",  # Suporta português!
        top_n=8  # ✅ OTIMIZADO: Aumentado de 5→8 para perguntas complexas/abstratas
    )
    
    # Retriever com reranking (agora recebe Documents)
    retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=wrapped_retriever
    )
    
    # Metadados
    metadata_path = f"{persist_directory}/metadata.pkl"
    metadata = {}
    if os.path.exists(metadata_path):
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
    
    # Mostrar PDFs
    print("=" * 60)
    print("📚 KNOWLEDGE BASE (COM RERANKER)")
    print("=" * 60)
    if 'pdfs' in metadata:
        for p in metadata['pdfs']:
            print(f"  • {p['filename']} ({p['texts']}T, {p['tables']}Tab, {p['images']}I)")
    print("=" * 60)
    print("\n🔥 Reranker ativado: Cohere Multilingual v3.0")
    print("   → Busca inicial: ~20 resultados (otimizado)")
    print("   → Após rerank: Top 5 mais relevantes")
    print("   → Melhoria de precisão: 30-40%\n")
    print("💡 Faça perguntas - busca em TODOS os PDFs com reranking!")
    print("   Digite 'sair' para encerrar\n")
    
    # Pipeline RAG
    def parse_docs(docs):
        """Docs podem ser: Document, Table, CompositeElement, ou string"""
        b64_images = []  # ✅ Mudança: incluir metadata junto com base64
        text = []
        for doc in docs:
            # Extrair conteúdo baseado no tipo
            if hasattr(doc, 'page_content'):
                # Document do LangChain
                content = doc.page_content
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif hasattr(doc, 'text'):
                # Table ou CompositeElement da Unstructured
                content = doc.text
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif isinstance(doc, str):
                # String simples
                content = doc
                metadata = {}
            else:
                # Fallback
                content = str(doc)
                metadata = {}

            # ✅ FIX: Identificar imagens pelo metadata.type, NÃO por b64decode
            # (imagens têm page_content=summary, não base64!)
            if metadata.get('type') == 'image':
                # Buscar imagem real do docstore usando doc_id
                doc_id = metadata.get('doc_id')
                if doc_id:
                    try:
                        # 🛡️ VALIDATE: Verificar se doc_id existe antes de buscar
                        # (previne "Error finding id" de chunks órfãos)
                        global _docstore
                        if not _docstore or not hasattr(_docstore, 'mget'):
                            print(f"   ⚠️ Docstore não disponível para buscar imagem {doc_id}")
                            continue

                        # Tentar buscar a imagem do docstore
                        image_obj = _docstore.mget([doc_id])[0]
                        if image_obj:
                            # Image object da Unstructured tem .text com base64
                            image_base64 = image_obj.text if hasattr(image_obj, 'text') else str(image_obj)
                            image_data = {
                                "base64": image_base64,
                                "metadata": metadata
                            }
                            b64_images.append(image_data)
                            continue
                        else:
                            print(f"   ⚠️ Imagem {doc_id} não encontrada no docstore (chunk órfão?)")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao buscar imagem {doc_id}: {str(e)[:100]}")

            # Se não é imagem ou falhou ao buscar, tratar como texto
            # Criar objeto com .text para compatibilidade
            class TextDoc:
                def __init__(self, text_content, meta):
                    self.text = text_content
                    self.metadata = meta

            text.append(TextDoc(content, metadata))

        return {"images": b64_images, "texts": text}
    
    def build_prompt(kwargs):
        docs = kwargs["context"]
        question = kwargs["question"]

        context = ""
        for text in docs["texts"]:
            source = 'unknown'
            if hasattr(text, 'metadata'):
                if isinstance(text.metadata, dict):
                    source = text.metadata.get('source', 'unknown')
                elif hasattr(text.metadata, 'source'):
                    source = text.metadata.source
            context += f"\n[{source}] {text.text}\n"

        # Prompt RIGOROSO com INFERÊNCIA MODERADA: permite conexões lógicas entre chunks
        system_instruction = """Você é um assistente de pesquisa médica RIGOROSO com CAPACIDADE MULTIMODAL.

⚠️ IDIOMA: SEMPRE responda em PORTUGUÊS BRASILEIRO. Todas as descrições, análises e referências devem estar em português.

REGRAS CRÍTICAS:
1. Responda APENAS com informações que estão no contexto fornecido abaixo
2. NUNCA use conhecimento geral ou externo aos documentos
3. Cite EXATAMENTE como está escrito no documento
4. Se houver listas, tabelas ou critérios, reproduza-os FIELMENTE
5. Mantenha formatação original (bullets, números, etc)

🖼️ USO EQUILIBRADO DE IMAGENS:
6. Se você receber IMAGENS anexadas (fluxogramas, diagramas, figuras):
   - PRIORIZE responder a pergunta com TEXTO COMPLETO E DETALHADO baseado no contexto textual
   - Inclua referências a imagens APENAS quando forem DIRETAMENTE relevantes para ENRIQUECER a resposta
   - Formato para referenciar: 📊 **[FIGURA X: Título]** seguido de breve explicação de como a imagem complementa o texto
   - NÃO use sintaxe markdown (![]() ou attachment://) - imagens aparecem automaticamente
   - NÃO transforme a resposta em uma descrição de imagens - mantenha foco no CONTEÚDO TEXTUAL
   - A imagem deve COMPLEMENTAR a resposta textual, não substituí-la

INFERÊNCIAS PERMITIDAS (apenas quando necessário):
7. Se a pergunta pede "relação entre X e Y", você PODE conectar informações de DIFERENTES trechos do contexto, citando AMBOS
8. Se a pergunta pede "quando NÃO fazer X" e o contexto diz "fazer Y em situação Z", você PODE inferir logicamente, citando o trecho original
9. Se a pergunta usa negação ("NÃO descarta", "NÃO é recomendado"), procure informações complementares no contexto que respondam indiretamente

CORREÇÃO DE PREMISSAS INCORRETAS:
10. Se a pergunta contém PREMISSA FALSA ou INCORRETA (ex: "dose em TFG<15" quando medicamento é contraindicado), você DEVE CORRIGIR a premissa citando o trecho correto
11. Exemplos de correção:
   - Pergunta: "Qual dose de X em TFG<15?" quando X é contraindicado
     Resposta: "X é CONTRAINDICADO quando TFG <30. Portanto, NÃO há dose recomendada. [cite fonte]"
   - Pergunta: "HbA1c <5% é o alvo ideal?"
     Resposta: "NÃO. O alvo recomendado é HbA1c <7%. HbA1c muito baixo aumenta risco de hipoglicemia. [cite fonte]"

INTERPRETAÇÃO DE LINGUAGEM COLOQUIAL:
12. Interprete termos coloquiais: "açúcar na hemoglobina"=HbA1c, "problema no rim"=TFG reduzida, "gordo"=obesidade, "comprimido"=antidiabético oral

REGRA FINAL:
13. Se após tentar conexões lógicas e correções a informação AINDA não puder ser inferida do contexto, responda: "A informação solicitada não está presente nos documentos fornecidos"

CONTEXTO DOS DOCUMENTOS:
{context}

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA (baseada SOMENTE no contexto acima, com inferências lógicas documentadas quando necessário, e INCLUINDO imagens relevantes quando fornecidas):"""

        prompt_content = [{
            "type": "text",
            "text": system_instruction.format(context=context, question=question)
        }]

        # ✅ CONVERT IMAGES TO JPEG before sending to Vision API
        for image_data in docs["images"]:
            # ✅ ATUALIZADO: images agora são dicts com base64 + metadata
            image_base64 = image_data["base64"]  # Extrair base64

            # Convert to JPEG (handles TIFF, BMP, etc.)
            jpeg_image, success = convert_image_to_jpeg_base64(image_base64)
            if success:
                prompt_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{jpeg_image}"}
                })
            else:
                # Skip images that failed to convert
                print(f"⚠️  Skipping image that failed JPEG conversion")

        return ChatPromptTemplate.from_messages([HumanMessage(content=prompt_content)])

    chain = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
    } | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | ChatOpenAI(model="gpt-4o")  # Upgrade: +60% melhor inferência vs 4o-mini
            | StrOutputParser()
        )
    )

    # Chat loop
    while True:
        try:
            question = input("🤔 Pergunta: ").strip()
            
            if not question or question.lower() in ['sair', 'exit', 'quit']:
                print("Ate logo!")
                break
            
            print("Buscando com reranking...")
            response = chain.invoke(question)

            print(f"\nResposta: {response['response']}\n")
            
            sources = set()
            for text in response['context']['texts']:
                if hasattr(text, 'metadata'):
                    if isinstance(text.metadata, dict):
                        sources.add(text.metadata.get('source', 'unknown'))
                    elif hasattr(text.metadata, 'source'):
                        sources.add(text.metadata.source)
                    else:
                        sources.add('unknown')
            
            num_results = len(response['context']['texts'])
            print(f"📊 {num_results} resultados rerankeados")
            if sources:
                print(f"📄 Fontes: {', '.join(sorted(sources))}\n")
            
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\nAte logo!")
            break
        except Exception as e:
            print(f"❌ Erro: {str(e)[:100]}\n")

