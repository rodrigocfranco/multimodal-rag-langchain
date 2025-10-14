#!/usr/bin/env python3
"""
Interface Web com Streamlit - RAG Multimodal
Interface gráfica bonita para interagir com seus PDFs
"""

import streamlit as st
import os
from dotenv import load_dotenv

# Configurar página
st.set_page_config(
    page_title="RAG Multimodal - Chat com PDFs",
    page_icon="📄",
    layout="wide"
)

# Carregar variáveis de ambiente
load_dotenv()

# CSS customizado
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stTextInput > div > div > input {
        font-size: 16px;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)

# Título
st.title("📄 Chat com PDFs - RAG Multimodal")
st.markdown("---")

# Sidebar para configurações
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Seleção de PDF
    content_dir = "./content/"
    if os.path.exists(content_dir):
        pdf_files = [f for f in os.listdir(content_dir) if f.endswith('.pdf')]
        if pdf_files:
            selected_pdf = st.selectbox(
                "Selecione um PDF:",
                pdf_files,
                key="pdf_selector"
            )
        else:
            st.error("Nenhum PDF encontrado no diretório content/")
            st.stop()
    else:
        st.error("Diretório content/ não encontrado")
        st.stop()
    
    st.markdown("---")
    
    # Botão para processar PDF
    if st.button("🔄 Processar PDF", type="primary"):
        st.session_state['pdf_processed'] = False
        st.session_state['messages'] = []
    
    st.markdown("---")
    
    # Informações
    st.markdown("### 💡 Como usar")
    st.markdown("""
    1. Selecione um PDF
    2. Clique em 'Processar PDF'
    3. Aguarde o processamento
    4. Faça suas perguntas!
    """)
    
    st.markdown("---")
    st.markdown("### 📊 Exemplos de Perguntas")
    st.markdown("""
    - What is the main topic?
    - Summarize the document
    - What are the key findings?
    - Explain the methodology
    """)

# Inicializar session state
if 'pdf_processed' not in st.session_state:
    st.session_state['pdf_processed'] = False
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'retriever' not in st.session_state:
    st.session_state['retriever'] = None
if 'chain' not in st.session_state:
    st.session_state['chain'] = None

# Função para processar PDF
@st.cache_resource(show_spinner=False)
def process_pdf(pdf_filename):
    """Processa o PDF e retorna o retriever e chain configurados"""
    
    import time
    from unstructured.partition.pdf import partition_pdf
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_openai import ChatOpenAI
    import uuid
    from langchain_community.vectorstores import Chroma
    from langchain.storage import InMemoryStore
    from langchain.schema.document import Document
    from langchain_openai import OpenAIEmbeddings
    from langchain.retrievers.multi_vector import MultiVectorRetriever
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    from langchain_core.messages import HumanMessage
    from base64 import b64decode
    
    file_path = content_dir + pdf_filename
    
    # 1. Extrair dados
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    progress_text.text("1/5 Extraindo dados do PDF...")
    progress_bar.progress(20)
    
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
    
    # Separar elementos
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
                chunk_els = chunk.metadata.orig_elements
                for el in chunk_els:
                    if "Image" in str(type(el)):
                        images_b64.append(el.metadata.image_base64)
        return images_b64
    
    images = get_images_base64(chunks)
    
    # 2. Gerar resumos
    progress_text.text("2/5 Gerando resumos dos textos...")
    progress_bar.progress(40)
    
    model = ChatGroq(temperature=0.5, model="llama-3.1-8b-instant")
    prompt_text = """
    You are an assistant tasked with summarizing tables and text.
    Give a concise summary of the table or text.
    
    Respond only with the summary, no additional comment.
    
    Table or text chunk: {element}
    """
    prompt = ChatPromptTemplate.from_template(prompt_text)
    summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()
    
    text_summaries = []
    for i, text in enumerate(texts):
        try:
            summary = summarize_chain.invoke(text)
            text_summaries.append(summary)
            time.sleep(0.5)
        except:
            text_summaries.append(text.text[:500])
    
    # Resumir tabelas
    table_summaries = []
    if len(tables) > 0:
        progress_text.text("3/5 Gerando resumos das tabelas...")
        progress_bar.progress(50)
        tables_html = [table.metadata.text_as_html for table in tables]
        for table_html in tables_html:
            try:
                summary = summarize_chain.invoke(table_html)
                table_summaries.append(summary)
                time.sleep(0.5)
            except:
                table_summaries.append(table_html[:500])
    
    # Resumir imagens
    image_summaries = []
    if len(images) > 0:
        progress_text.text("4/5 Gerando resumos das imagens...")
        progress_bar.progress(60)
        prompt_template = """Describe the image in detail."""
        messages = [
            (
                "user",
                [
                    {"type": "text", "text": prompt_template},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,{image}"},
                    },
                ],
            )
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()
        
        for image in images:
            try:
                summary = chain.invoke(image)
                image_summaries.append(summary)
                time.sleep(0.8)
            except:
                image_summaries.append("Image")
    
    # 3. Criar vectorstore
    progress_text.text("5/5 Criando banco de dados vetorial...")
    progress_bar.progress(80)
    
    vectorstore = Chroma(
        collection_name="streamlit_rag",
        embedding_function=OpenAIEmbeddings()
    )
    store = InMemoryStore()
    id_key = "doc_id"
    
    retriever = MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key=id_key,
    )
    
    # Adicionar ao vectorstore
    doc_ids = [str(uuid.uuid4()) for _ in texts]
    summary_texts = [
        Document(page_content=summary, metadata={id_key: doc_ids[i]}) 
        for i, summary in enumerate(text_summaries)
    ]
    retriever.vectorstore.add_documents(summary_texts)
    retriever.docstore.mset(list(zip(doc_ids, texts)))
    
    if len(tables) > 0:
        table_ids = [str(uuid.uuid4()) for _ in tables]
        summary_tables = [
            Document(page_content=summary, metadata={id_key: table_ids[i]}) 
            for i, summary in enumerate(table_summaries)
        ]
        retriever.vectorstore.add_documents(summary_tables)
        retriever.docstore.mset(list(zip(table_ids, tables)))
    
    if len(images) > 0:
        img_ids = [str(uuid.uuid4()) for _ in images]
        summary_img = [
            Document(page_content=summary, metadata={id_key: img_ids[i]}) 
            for i, summary in enumerate(image_summaries)
        ]
        retriever.vectorstore.add_documents(summary_img)
        retriever.docstore.mset(list(zip(img_ids, images)))
    
    # 4. Configurar chain
    def parse_docs(docs):
        b64 = []
        text = []
        for doc in docs:
            try:
                b64decode(doc)
                b64.append(doc)
            except:
                text.append(doc)
        return {"images": b64, "texts": text}
    
    def build_prompt(kwargs):
        docs_by_type = kwargs["context"]
        user_question = kwargs["question"]
        
        context_text = ""
        if len(docs_by_type["texts"]) > 0:
            for text_element in docs_by_type["texts"]:
                context_text += text_element.text
        
        prompt_template = f"""
        Answer the question based on the following context.
        Context: {context_text}
        Question: {user_question}
        """
        
        prompt_content = [{"type": "text", "text": prompt_template}]
        
        if len(docs_by_type["images"]) > 0:
            for image in docs_by_type["images"]:
                prompt_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                })
        
        return ChatPromptTemplate.from_messages([HumanMessage(content=prompt_content)])
    
    chain = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
    } | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | ChatOpenAI(model="gpt-4o-mini")
            | StrOutputParser()
        )
    )
    
    progress_bar.progress(100)
    progress_text.text("✅ PDF processado com sucesso!")
    time.sleep(1)
    progress_text.empty()
    progress_bar.empty()
    
    stats = {
        "texts": len(texts),
        "tables": len(tables),
        "images": len(images)
    }
    
    return retriever, chain, stats

# Área principal
if not st.session_state['pdf_processed']:
    st.info("👆 Selecione um PDF na barra lateral e clique em 'Processar PDF' para começar!")
    
    with st.spinner(f"Processando {selected_pdf}..."):
        try:
            retriever, chain, stats = process_pdf(selected_pdf)
            st.session_state['retriever'] = retriever
            st.session_state['chain'] = chain
            st.session_state['pdf_processed'] = True
            st.session_state['current_pdf'] = selected_pdf
            st.session_state['stats'] = stats
            st.success(f"✅ PDF processado! {stats['texts']} textos, {stats['tables']} tabelas, {stats['images']} imagens")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao processar PDF: {str(e)}")

else:
    # Mostrar estatísticas
    with st.expander("📊 Informações do Documento"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📄 PDF", st.session_state['current_pdf'])
        with col2:
            st.metric("📝 Textos", st.session_state['stats']['texts'])
        with col3:
            st.metric("📊 Tabelas", st.session_state['stats']['tables'])
        with col4:
            st.metric("🖼️ Imagens", st.session_state['stats']['images'])
    
    st.markdown("---")
    
    # Área de chat
    st.subheader("💬 Chat")
    
    # Mostrar mensagens anteriores
    for message in st.session_state['messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message:
                with st.expander("📚 Fontes consultadas"):
                    st.write(message["sources"])
    
    # Input de pergunta
    if question := st.chat_input("Digite sua pergunta aqui..."):
        # Adicionar pergunta do usuário
        st.session_state['messages'].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        
        # Gerar resposta
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    response = st.session_state['chain'].invoke(question)
                    answer = response['response']
                    sources_info = f"{len(response['context']['texts'])} textos, {len(response['context']['images'])} imagens"
                    
                    st.markdown(answer)
                    with st.expander("📚 Fontes consultadas"):
                        st.write(sources_info)
                    
                    # Salvar resposta
                    st.session_state['messages'].append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources_info
                    })
                except Exception as e:
                    st.error(f"Erro ao gerar resposta: {str(e)}")

# Rodapé
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
    🤖 Powered by LangChain, OpenAI & Groq | 📄 RAG Multimodal
</div>
""", unsafe_allow_html=True)

