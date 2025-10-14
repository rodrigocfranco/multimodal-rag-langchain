# 📄 Sistema RAG Multimodal

Sistema simples para fazer perguntas sobre PDFs usando IA.

## 🚀 Uso Rápido

### 1. Adicionar PDFs
```bash
python adicionar_pdf.py "seu_arquivo.pdf"
```

### 2. Fazer Perguntas (Terminal)
```bash
python consultar.py              # Básico (rápido)
python consultar_com_rerank.py   # Com reranker (preciso +35%)
```

### 3. Usar via API (n8n)
```bash
python consultar.py --api              # Básico
python consultar_com_rerank.py --api   # Com reranker (recomendado)
```

Depois use: `POST http://localhost:5000/query`

---

## 📋 O Que Faz

- 📄 Extrai texto, tabelas e imagens de PDFs
- 🤖 Gera resumos com IA (Groq + OpenAI)
- 💾 Salva em banco vetorial (não reprocessa)
- 🔍 Busca em TODOS os PDFs automaticamente
- 💬 Chat terminal ou API REST

---

## ⚙️ Instalação

### 1. Dependências do Sistema (macOS)
```bash
brew install poppler tesseract libmagic
```

### 2. Python
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar API Keys
Edite `.env`:
```
OPENAI_API_KEY=sua_chave
GROQ_API_KEY=sua_chave
COHERE_API_KEY=sua_chave  # Para reranking (opcional mas recomendado)
```

---

## 💡 Exemplos

### Terminal:
```bash
python consultar.py

🤔 Pergunta: Quais são as classes de antidiabéticos?
🤖 [Busca automaticamente no PDF correto]
📄 Fonte: diabetes.pdf
```

### API (n8n):
```bash
# Iniciar API
python consultar.py --api

# Request
POST http://localhost:5000/query
{"question": "sua pergunta"}

# Response
{"answer": "resposta", "sources": ["pdf1.pdf"]}
```

---

## 📁 Arquivos

- `adicionar_pdf.py` → Adicionar PDF ao knowledge base
- `consultar.py` → Consultar (terminal ou API)
- `test_installation.py` → Testar instalação
- `requirements.txt` → Dependências

---

## 🔧 Solução de Problemas

```bash
# Testar instalação
python test_installation.py

# Verificar PDFs
ls -lh content/

# Verificar knowledge base
ls -lh knowledge_base/
```

---

**Sistema otimizado: 2 scripts principais + metadados + API integrada** 🎉
