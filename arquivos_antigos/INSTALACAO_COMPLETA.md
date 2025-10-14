# ✅ Instalação Completa - Multi-modal RAG com LangChain

## 📊 Status da Instalação

### ✅ Dependências do Sistema (macOS)
- ✅ **Homebrew**: Gerenciador de pacotes
- ✅ **Poppler** (25.10.0): Processamento de PDFs
- ✅ **Tesseract** (5.5.1): OCR para extração de texto
- ✅ **Libmagic** (5.46): Detecção de tipos de arquivo

### ✅ Ambiente Python
- ✅ **Python 3.13**: Instalado
- ✅ **Ambiente Virtual**: Criado em `venv/`
- ✅ **Dependências Python**: Todas instaladas (ver `requirements.txt`)

### ✅ Bibliotecas Principais Instaladas
```
langchain (0.3.27)
langchain-community (0.3.31)
langchain-core (0.3.79)
langchain-openai (0.3.35)
langchain-groq (0.3.8)
chromadb (1.1.1)
unstructured (0.18.15)
openai (2.3.0)
tiktoken (0.12.0)
jupyter (1.1.1)
```

### ✅ Chaves de API Configuradas
- ✅ **OpenAI API Key**: Configurada
- ✅ **Groq API Key**: Configurada  
- ✅ **LangChain API Key**: Configurada

### ✅ Arquivos do Projeto
```
multimodal-rag-langchain/
├── .env                      ✅ Chaves de API
├── .env.example             ✅ Template de variáveis
├── env.example              ✅ Template alternativo
├── .gitignore               ✅ Arquivos ignorados
├── requirements.txt         ✅ Dependências Python
├── setup.sh                 ✅ Script de instalação
├── multimodal_rag.py        ✅ Script principal
├── README.md                ✅ Documentação completa
├── QUICKSTART.md            ✅ Guia de início rápido
├── content/
│   └── attention.pdf        ✅ PDF de exemplo (2.1 MB)
└── venv/                    ✅ Ambiente virtual
```

## 🚀 Como Executar Agora

### Método 1: Execução Direta

```bash
# 1. Navegar até o diretório
cd /Users/rcfranco/multimodal-rag-langchain

# 2. Ativar ambiente virtual
source venv/bin/activate

# 3. Executar o script
python multimodal_rag.py
```

### Método 2: Com Jupyter Notebook

```bash
# 1. Ativar ambiente virtual
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

# 2. Iniciar Jupyter
jupyter notebook

# 3. Criar um novo notebook e importar o código
```

## ⚙️ O Que o Script Faz

O script `multimodal_rag.py` executa as seguintes etapas:

### 1️⃣ Extração de Dados (30-60 segundos)
- Carrega o PDF `attention.pdf`
- Extrai texto, tabelas e imagens usando Unstructured
- Usa Poppler e Tesseract para processamento

### 2️⃣ Geração de Resumos (2-3 minutos)
- **Textos e Tabelas**: Resumidos com Groq (Llama 3.1)
- **Imagens**: Descritas com OpenAI (GPT-4o-mini)
- Pausas entre chamadas para evitar rate limits

### 3️⃣ Criação do Vectorstore (30 segundos)
- Gera embeddings com OpenAI
- Armazena no ChromaDB
- Configura MultiVectorRetriever

### 4️⃣ Testes do Sistema (1-2 minutos)
- Executa 3 perguntas de exemplo
- Mostra respostas e fontes consultadas

**Tempo Total Estimado: 5-8 minutos**

## 📝 Exemplos de Uso

### Exemplo 1: Perguntas Simples

```python
# Pergunta sobre o documento
response = chain.invoke("What is the attention mechanism?")
print(response)
```

### Exemplo 2: Com Fontes

```python
# Pergunta com contexto das fontes
response_with_sources = chain_with_sources.invoke("Who are the authors?")
print("Resposta:", response_with_sources['response'])
print(f"Fontes: {len(response_with_sources['context']['texts'])} textos")
```

### Exemplo 3: Processar Seu PDF

```python
# 1. Coloque seu PDF em content/
# 2. Modifique a linha 30 do script:
file_path = output_path + 'seu_arquivo.pdf'
```

## 🔧 Configurações e Ajustes

### Reduzir Tempo de Processamento

Se quiser processar mais rápido (com risco de rate limit):

```python
# No script, linha ~135 e ~150, reduza o sleep:
time.sleep(0.2)  # Reduzir de 0.5 para 0.2
```

### Usar Modelos Diferentes

```python
# Trocar para modelo maior do Groq (linha ~122):
model = ChatGroq(temperature=0.5, model="llama-3.1-70b-versatile")

# Trocar para GPT-4 (linha ~176):
chain = prompt | ChatOpenAI(model="gpt-4o") | StrOutputParser()
```

### Ajustar Extração do PDF

```python
# Linha ~55, ajustar parâmetros:
chunks = partition_pdf(
    filename=file_path,
    strategy="fast",              # Mais rápido, menos preciso
    max_characters=5000,           # Chunks menores
    extract_image_block_types=[],  # Desabilitar imagens para teste
)
```

## 🎯 Próximos Passos Sugeridos

### 1. Testar com Outro PDF
```bash
# Baixar outro paper
curl -L -o content/outro_paper.pdf https://example.com/paper.pdf

# Editar multimodal_rag.py linha 30
file_path = output_path + 'outro_paper.pdf'

# Executar
python multimodal_rag.py
```

### 2. Criar Interface Interativa

Instalar Streamlit:
```bash
pip install streamlit
```

Criar `app.py`:
```python
import streamlit as st
# ... código do RAG aqui ...

st.title("Multi-modal RAG")
question = st.text_input("Faça sua pergunta:")
if question:
    response = chain.invoke(question)
    st.write(response)
```

Executar:
```bash
streamlit run app.py
```

### 3. Adicionar Múltiplos PDFs

```python
import glob

# Processar todos os PDFs em content/
pdf_files = glob.glob("content/*.pdf")
for pdf_file in pdf_files:
    chunks = partition_pdf(filename=pdf_file, ...)
    # ... processar cada PDF
```

### 4. Salvar Vectorstore em Disco

```python
# Salvar ChromaDB persistente
vectorstore = Chroma(
    collection_name="multi_modal_rag",
    embedding_function=OpenAIEmbeddings(),
    persist_directory="./chroma_db"  # Adicionar esta linha
)
```

Depois você pode recarregar sem processar tudo novamente:
```python
# Carregar vectorstore existente
vectorstore = Chroma(
    collection_name="multi_modal_rag",
    embedding_function=OpenAIEmbeddings(),
    persist_directory="./chroma_db"
)
```

## 🐛 Troubleshooting

### Problema: Rate Limit do Groq
**Mensagem**: `Rate limit reached for model llama-3.1-8b-instant`

**Solução**: O script já tem delays. Se ainda ocorrer:
```python
# Aumentar o delay (linha ~135, ~150, ~185)
time.sleep(1.0)  # Aumentar para 1 segundo
```

### Problema: SSL Certificate Error (NLTK)
**Mensagem**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solução**: Isso é apenas um warning do NLTK e não afeta o funcionamento. Para corrigir:
```bash
/Applications/Python\ 3.13/Install\ Certificates.command
```

### Problema: Deprecation Warnings do LangChain
**Mensagem**: `LangChainDeprecationWarning`

**Solução**: São avisos, não erros. Para corrigir, atualize os imports:
```python
# Trocar:
from langchain.vectorstores import Chroma
# Por:
from langchain_community.vectorstores import Chroma

# Trocar:
from langchain.embeddings import OpenAIEmbeddings
# Por:
from langchain_openai import OpenAIEmbeddings
```

### Problema: Memória Insuficiente
**Mensagem**: `MemoryError` ou sistema lento

**Solução**: Processar PDF menor ou ajustar parâmetros:
```python
max_characters=5000,
combine_text_under_n_chars=1000,
```

## 📞 Suporte

- **Documentação LangChain**: https://python.langchain.com/docs/
- **Unstructured Docs**: https://docs.unstructured.io/
- **ChromaDB Docs**: https://docs.trychroma.com/
- **OpenAI API**: https://platform.openai.com/docs/
- **Groq API**: https://console.groq.com/docs/

## ✅ Checklist Final

Antes de executar, confirme:

- [x] Ambiente virtual ativado (`source venv/bin/activate`)
- [x] Arquivo `.env` configurado com as chaves de API
- [x] PDF presente em `content/attention.pdf`
- [x] Dependências do sistema instaladas (poppler, tesseract, libmagic)
- [x] Todas as dependências Python instaladas

**Se todos os itens acima estiverem marcados, você está pronto para executar!**

```bash
python multimodal_rag.py
```

---

**🎉 Instalação 100% Completa! Pronto para usar!**

