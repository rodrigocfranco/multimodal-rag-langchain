# 🌐 Integração com n8n - API REST

## 🎯 Como Usar o Sistema RAG via API (n8n)

Criei uma API REST completa para você integrar com n8n, Make, Zapier ou qualquer sistema HTTP!

---

## 🚀 Instalação e Configuração

### 1. Instalar Dependências da API

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

# Instalar Flask
pip install flask flask-cors
```

### 2. Iniciar o Servidor

```bash
python api_rest.py
```

**Servidor inicia em:** `http://localhost:5000`

---

## 📡 Endpoints Disponíveis

### 1️⃣ **Health Check**

**GET** `http://localhost:5000/health`

**Resposta:**
```json
{
    "status": "ok",
    "message": "API RAG Multimodal está funcionando!",
    "version": "1.0"
}
```

---

### 2️⃣ **Listar Vectorstores**

**GET** `http://localhost:5000/vectorstores`

**Resposta:**
```json
{
    "vectorstores": [
        {
            "name": "attention",
            "pdf_filename": "attention.pdf",
            "num_texts": 12,
            "num_tables": 0,
            "num_images": 6,
            "processed_at": "2025-10-13 12:30:15"
        },
        {
            "name": "Manejo_da_terapia_antidiabética_no_DM2",
            "pdf_filename": "Manejo da terapia antidiabética no DM2.pdf",
            "num_texts": 28,
            "num_tables": 6,
            "num_images": 12,
            "processed_at": "2025-10-13 14:45:30"
        }
    ],
    "count": 2
}
```

---

### 3️⃣ **Query Completa (com fontes)**

**POST** `http://localhost:5000/query`

**Body:**
```json
{
    "vectorstore": "Manejo_da_terapia_antidiabética_no_DM2",
    "question": "Quais são as classes de antidiabéticos mencionados?",
    "include_sources": true
}
```

**Resposta:**
```json
{
    "answer": "As classes de antidiabéticos mencionados incluem: metformina, sulfoniluréias, inibidores DPP-4, agonistas GLP-1...",
    "vectorstore": "Manejo_da_terapia_antidiabética_no_DM2",
    "pdf_filename": "Manejo da terapia antidiabética no DM2.pdf",
    "sources": {
        "num_texts": 4,
        "num_images": 1,
        "texts": [
            {
                "index": 0,
                "preview": "A metformina é o medicamento de primeira linha...",
                "page_number": 3,
                "content_type": "text"
            },
            {
                "index": 1,
                "preview": "Tabela 1: Classes de antidiabéticos...",
                "page_number": 5,
                "content_type": "table"
            }
        ],
        "images": [
            {
                "index": 0,
                "size_kb": 45.2
            }
        ]
    }
}
```

---

### 4️⃣ **Query Simples (para n8n)** ⭐

**POST** `http://localhost:5000/query-simple`

**Body:**
```json
{
    "vectorstore": "Manejo_da_terapia_antidiabética_no_DM2",
    "question": "Qual a dose de metformina?"
}
```

**Resposta:**
```json
{
    "answer": "A dose inicial recomendada de metformina é de 500-850mg..."
}
```

**💡 Use este endpoint para n8n!** Mais simples e direto.

---

### 5️⃣ **Info do Vectorstore**

**GET** `http://localhost:5000/info/nome_do_vectorstore`

**Exemplo:** `http://localhost:5000/info/attention`

**Resposta:**
```json
{
    "pdf_filename": "attention.pdf",
    "num_texts": 12,
    "num_tables": 0,
    "num_images": 6,
    "processed_at": "2025-10-13 12:30:15",
    "version": "v2_corrigido"
}
```

---

## 🔌 Integração com n8n

### **Workflow n8n Básico:**

```
1. [Webhook Trigger]
   ↓
2. [HTTP Request]
   • Method: POST
   • URL: http://localhost:5000/query-simple
   • Body JSON:
     {
       "vectorstore": "{{ $json.vectorstore }}",
       "question": "{{ $json.question }}"
     }
   ↓
3. [Responder]
   • {{ $json.answer }}
```

### **Exemplo de Request no n8n:**

**Node HTTP Request:**
```
Method: POST
URL: http://localhost:5000/query-simple

Headers:
  Content-Type: application/json

Body (JSON):
{
  "vectorstore": "Manejo_da_terapia_antidiabética_no_DM2",
  "question": "{{$json.question}}"
}
```

**Response Path:** `$.answer`

---

## 🧪 Testar a API

### **Com curl:**

```bash
# 1. Health check
curl http://localhost:5000/health

# 2. Listar vectorstores
curl http://localhost:5000/vectorstores

# 3. Query simples
curl -X POST http://localhost:5000/query-simple \
  -H "Content-Type: application/json" \
  -d '{
    "vectorstore": "attention",
    "question": "What is the attention mechanism?"
  }'

# 4. Query completa
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "vectorstore": "attention",
    "question": "What is the attention mechanism?",
    "include_sources": true
  }'
```

### **Com Python:**

```python
import requests

# Query simples
response = requests.post('http://localhost:5000/query-simple', json={
    "vectorstore": "attention",
    "question": "What is the attention mechanism?"
})

print(response.json()['answer'])
```

### **Com n8n HTTP Request Node:**

```json
{
  "method": "POST",
  "url": "http://localhost:5000/query-simple",
  "body": {
    "vectorstore": "attention",
    "question": "What is multihead attention?"
  },
  "headers": {
    "Content-Type": "application/json"
  }
}
```

---

## 🔒 Segurança e Produção

### **Adicionar Autenticação (Opcional):**

```python
# No api_rest.py, adicionar:
from functools import wraps

API_KEY = os.getenv("API_KEY", "sua-chave-secreta")

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key')
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/query-simple', methods=['POST'])
@require_api_key  # ← Adicionar proteção
def query_simple():
    ...
```

**Usar no n8n:**
```
Headers:
  X-API-Key: sua-chave-secreta
```

---

## 📊 Exemplo Completo no n8n

### **Workflow: Chatbot RAG via WhatsApp/Telegram**

```
1. [Webhook/Trigger]
   • Recebe mensagem do usuário
   
2. [Set Node] - Preparar dados
   • vectorstore: "Manejo_da_terapia_antidiabética_no_DM2"
   • question: {{$json.message}}

3. [HTTP Request] - Consultar RAG
   • POST http://localhost:5000/query-simple
   • Body: { vectorstore, question }

4. [Responder]
   • Enviar {{$json.answer}} de volta
```

### **Workflow: Processar Múltiplas Perguntas**

```
1. [Schedule Trigger]
   • Diariamente às 9h

2. [Code Node] - Lista de perguntas
   const questions = [
     "Resumo do documento",
     "Principais recomendações",
     "Contraindicações"
   ];
   return questions.map(q => ({question: q}));

3. [HTTP Request] - Para cada pergunta
   • POST /query-simple
   • Loop sobre questões

4. [Aggregate] - Consolidar respostas

5. [Send Email] - Enviar relatório
```

---

## 🌐 Hospedar a API (Produção)

### **Opção 1: Railway**

```bash
# Criar railway.json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python api_rest.py",
    "restartPolicyType": "ON_FAILURE"
  }
}

# Fazer deploy
railway up
```

### **Opção 2: Render**

```bash
# Criar render.yaml
services:
  - type: web
    name: rag-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python api_rest.py
```

### **Opção 3: Docker**

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "api_rest.py"]
```

---

## ❓ FAQ

### **Q: A API retorna imagens?**
R: Sim! O sistema processa imagens com GPT-4o-mini e usa no contexto da resposta.

### **Q: Posso fazer múltiplas queries simultâneas?**
R: Sim! A API suporta múltiplas conexões. Use gunicorn para produção:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api_rest:app
```

### **Q: Como usar HTTPS?**
R: Use um proxy reverso (nginx) ou hospede em plataforma (Railway, Render).

### **Q: Tem limite de taxa?**
R: Depende dos limites da OpenAI/Groq. Adicione rate limiting se necessário.

---

## 🚀 Quick Start

```bash
# 1. Instalar dependências
pip install flask flask-cors

# 2. Processar um PDF
python processar_e_salvar.py "seu_arquivo.pdf"

# 3. Iniciar API
python api_rest.py

# 4. Testar
curl -X POST http://localhost:5000/query-simple \
  -H "Content-Type: application/json" \
  -d '{"vectorstore": "seu_arquivo", "question": "teste"}'

# 5. Integrar com n8n!
```

---

**✅ API REST pronta para integração com n8n!** 🌐

Quer que eu crie exemplos específicos de workflows do n8n?
