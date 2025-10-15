# Multimodal RAG LangChain

Sistema completo de RAG (Retrieval-Augmented Generation) multimodal com LangChain que processa PDFs extraindo **textos, tabelas e imagens**, armazenando tudo em um knowledge base vetorizado e permitindo consultas inteligentes com reranking.

## Características

- **Extração Multimodal**: Processa textos, tabelas e imagens de PDFs
- **Resumos com IA**: Gera resumos automáticos de todos os elementos usando Llama 3.1
- **Reranking Inteligente**: Usa Cohere para melhorar precisão em 30-40%
- **API REST**: Endpoints para upload de PDFs e consultas
- **Interface Web**: UI para upload e chat interativo
- **Streaming**: Acompanhamento em tempo real do processamento
- **Deploy Fácil**: Pronto para Railway com Dockerfile otimizado

## Stack Tecnológica

- **LangChain**: Orquestração do RAG
- **Unstructured**: Extração de dados de PDFs
- **ChromaDB**: Vector store para embeddings
- **OpenAI**: Embeddings (text-embedding-3-small) + GPT-4o-mini (respostas)
- **Groq**: Llama 3.1 (resumos - gratuito!)
- **Cohere**: Reranking multilingue (gratuito!)
- **Flask**: API REST

## Requisitos

### Chaves de API (3 obrigatórias)

1. **OpenAI API Key**: https://platform.openai.com/api-keys
2. **Groq API Key**: https://console.groq.com/keys (gratuito!)
3. **Cohere API Key**: https://dashboard.cohere.com/api-keys (gratuito!)

### Python 3.11+

```bash
python --version  # Deve ser 3.11 ou superior
```

## Instalação Local

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/multimodal-rag-langchain.git
cd multimodal-rag-langchain
```

### 2. Crie ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale dependências

```bash
pip install -r requirements.txt
```

### 4. Configure variáveis de ambiente

```bash
cp env.example .env
```

Edite `.env` e adicione suas chaves:

```bash
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
COHERE_API_KEY=...
```

### 5. Adicione PDFs ao knowledge base

```bash
# Criar pasta content (se não existir)
mkdir -p content

# Adicionar um PDF
python adicionar_pdf.py content/seu_arquivo.pdf

# Ou apenas o nome (busca na pasta content)
python adicionar_pdf.py seu_arquivo.pdf
```

### 6. Inicie a API

```bash
python consultar_com_rerank.py --api
```

A API estará disponível em `http://localhost:5001`

## Deploy no Railway

### Método 1: Deploy Direto do GitHub (Recomendado)

1. **Fork este repositório** para sua conta GitHub

2. **Acesse Railway**: https://railway.app

3. **Crie novo projeto**:
   - Click em "New Project"
   - Selecione "Deploy from GitHub repo"
   - Escolha seu fork do repositório

4. **Configure variáveis de ambiente** no Railway:
   ```
   OPENAI_API_KEY=sk-proj-...
   GROQ_API_KEY=gsk_...
   COHERE_API_KEY=...
   ```

5. **Deploy automático**: Railway detecta o Dockerfile e faz deploy automaticamente

6. **Acesse sua API**: Railway fornece um URL público

### Método 2: Deploy via Railway CLI

```bash
# Instale Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link ao projeto (ou crie novo)
railway link

# Configure variáveis de ambiente
railway variables set OPENAI_API_KEY=sk-proj-...
railway variables set GROQ_API_KEY=gsk_...
railway variables set COHERE_API_KEY=...

# Deploy
railway up
```

## Uso da API

### Endpoints Disponíveis

#### GET `/`
Documentação da API

```bash
curl https://seu-app.railway.app/
```

#### GET `/health`
Health check

```bash
curl https://seu-app.railway.app/health
```

#### GET `/ui`
Interface web para upload de PDFs

```
https://seu-app.railway.app/ui
```

#### GET `/chat`
Interface web para chat interativo

```
https://seu-app.railway.app/chat
```

#### POST `/upload`
Enviar PDF para processar (multipart/form-data)

```bash
curl -X POST https://seu-app.railway.app/upload \
  -F "file=@arquivo.pdf"
```

#### POST `/upload-stream`
Enviar PDF com acompanhamento em tempo real

```bash
curl -X POST https://seu-app.railway.app/upload-stream \
  -F "file=@arquivo.pdf"
```

#### POST `/query`
Fazer pergunta ao knowledge base

```bash
curl -X POST https://seu-app.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual o tratamento para hipertensão?"}'
```

Resposta:
```json
{
  "answer": "O tratamento para hipertensão inclui...",
  "sources": ["artigo_hipertensao.pdf"],
  "reranked": true
}
```

## Uso do Terminal (Local)

### Consultar knowledge base

```bash
python consultar_com_rerank.py
```

Modo interativo com reranking ativado.

## Integração com n8n / Make / Zapier

Use os endpoints da API para integrar com automações:

### Exemplo n8n Workflow

1. **HTTP Request Node** → POST /upload
2. **Aguardar processamento**
3. **HTTP Request Node** → POST /query
4. **Processar resposta**

### Exemplo cURL completo

```bash
# 1. Upload PDF
curl -X POST https://seu-app.railway.app/upload \
  -F "file=@artigo.pdf"

# 2. Fazer pergunta
curl -X POST https://seu-app.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são os principais achados do artigo?"
  }'
```

## Estrutura do Projeto

```
multimodal-rag-langchain/
├── adicionar_pdf.py              # Script para adicionar PDFs
├── consultar_com_rerank.py       # API + Terminal com reranking
├── consultar.py                  # Terminal sem reranking (deprecado)
├── requirements.txt              # Dependências Python
├── Dockerfile                    # Container para Railway
├── railway.json                  # Configuração Railway
├── Procfile                      # Comando de start
├── runtime.txt                   # Versão Python
├── .env.example                  # Exemplo de variáveis
├── .gitignore                    # Arquivos ignorados
├── content/                      # PDFs fonte
└── knowledge_base/               # Vector store (não versionado)
```

## Como Funciona

### 1. Processamento de PDFs

```python
adicionar_pdf.py
├── Extrai elementos com Unstructured (hi_res strategy)
├── Separa textos, tabelas e imagens
├── Gera resumos com IA (Llama 3.1 via Groq)
├── Armazena no ChromaDB com embeddings OpenAI
└── Salva metadados para tracking
```

### 2. Consulta com Reranking

```python
consultar_com_rerank.py
├── Busca inicial: Top 10 resultados (busca vetorial)
├── Reranking: Cohere seleciona Top 5 mais relevantes
├── Monta contexto com textos e imagens
├── Envia para GPT-4o-mini com visão
└── Retorna resposta + fontes
```

## Variáveis de Ambiente

### Obrigatórias

```bash
OPENAI_API_KEY=sk-proj-...      # OpenAI (embeddings + GPT-4o-mini)
GROQ_API_KEY=gsk_...            # Groq (resumos com Llama)
COHERE_API_KEY=...              # Cohere (reranking)
```

### Opcionais

```bash
API_SECRET_KEY=...              # Proteger upload (opcional)
UNSTRUCTURED_STRATEGY=hi_res    # ou "fast" (padrão: hi_res)
LANGCHAIN_API_KEY=...           # Tracing (opcional)
LANGCHAIN_TRACING_V2=true       # Habilitar tracing
PORT=8080                       # Porta da API (Railway define auto)
```

## Troubleshooting

### Erro: "libGL.so.1 not found"

O Dockerfile já inclui `libgl1`. Se ocorrer localmente:

```bash
# Ubuntu/Debian
sudo apt-get install libgl1

# O script faz fallback automático para strategy="fast"
```

### Erro: "OPENAI_API_KEY not set"

Configure o `.env`:

```bash
cp env.example .env
# Edite .env e adicione suas chaves
```

### API não inicia no Railway

Verifique:
1. Variáveis de ambiente configuradas
2. Build logs no Railway dashboard
3. Health check em `/health`

### Reranking muito lento

O reranking adiciona ~1-2s por query. Para desabilitar, use `consultar.py` ao invés de `consultar_com_rerank.py`.

## Performance

- **Upload PDF**: 5-10 minutos (depende do tamanho e complexidade)
- **Consulta sem rerank**: ~2-3s
- **Consulta com rerank**: ~3-5s (melhora precisão em 30-40%)
- **Memory**: ~512MB RAM (Railway Free tier OK)

## Custos Estimados

### Processamento de 1 PDF (~50 páginas)

- **OpenAI Embeddings**: ~$0.01
- **OpenAI GPT-4o-mini (imagens)**: ~$0.05
- **Groq (resumos)**: GRÁTIS (limite generoso)
- **Cohere (reranking)**: GRÁTIS (1000 reqs/mês)

**Total: ~$0.06/PDF**

### Consultas

- **OpenAI GPT-4o-mini**: ~$0.001/query
- **Cohere Rerank**: GRÁTIS
- **Embeddings (busca)**: ~$0.0001/query

**Total: ~$0.001/query**

## Roadmap

- [ ] Adicionar suporte a mais formatos (DOCX, PPTX)
- [ ] Implementar cache de queries
- [ ] Adicionar autenticação JWT
- [ ] Dashboard de analytics
- [ ] Suporte a múltiplos idiomas no OCR
- [ ] Streaming de respostas (SSE)

## Licença

MIT License - veja LICENSE para detalhes

## Contribuindo

Pull requests são bem-vindos! Para mudanças maiores, abra uma issue primeiro.

## Suporte

- **Issues**: https://github.com/seu-usuario/multimodal-rag-langchain/issues
- **Documentação LangChain**: https://python.langchain.com/
- **Documentação Railway**: https://docs.railway.app/

## Créditos

Desenvolvido com:
- [LangChain](https://langchain.com)
- [Unstructured.io](https://unstructured.io)
- [ChromaDB](https://www.trychroma.com)
- [OpenAI](https://openai.com)
- [Groq](https://groq.com)
- [Cohere](https://cohere.com)

---

**Feito com ❤️ para comunidade de IA**
