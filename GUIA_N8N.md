# 🔗 Guia Completo: Consultar RAG via n8n

## 📋 Pré-requisitos

- ✅ PDFs já processados no knowledge base
- ✅ n8n instalado e rodando
- ✅ Python ambiente virtual ativado

---

## 🚀 PASSO 1: Iniciar a API REST

### Opção 1: API SEM Reranker (Mais Rápida)

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

python consultar.py --api
```

**Você verá:**
```
🌐 API rodando em http://localhost:5000
====================================
Endpoints disponíveis:
  POST /query  → Fazer pergunta
  GET  /health → Health check
====================================
```

### Opção 2: API COM Reranker (Mais Precisa) ⭐ RECOMENDADO

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

python consultar_com_rerank.py --api
```

**Você verá:**
```
🌐 API COM RERANKER rodando em http://localhost:5000
====================================
🔥 Reranker: Cohere (melhora precisão em 30-40%)
Endpoints:
  POST /query  → Fazer pergunta (com rerank)
  GET  /health → Health check
====================================
```

---

## 🔧 PASSO 2: Testar a API (Terminal)

Antes de configurar o n8n, vamos testar se a API está funcionando:

### Teste 1: Health Check

```bash
# Em outro terminal
curl http://localhost:5000/health
```

**Resposta esperada:**
```json
{
  "status": "ok",
  "reranker": "cohere"
}
```

### Teste 2: Fazer uma Pergunta

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Quais os critérios diagnósticos da síndrome de lise tumoral?"}'
```

**Resposta esperada:**
```json
{
  "answer": "Os critérios diagnósticos da síndrome de lise tumoral incluem...",
  "sources": ["Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf"],
  "reranked": true
}
```

✅ **Se funcionou, está pronto para o n8n!**

---

## 🎯 PASSO 3: Configurar no n8n

### 3.1. Criar Novo Workflow

1. Abra o n8n (normalmente em `http://localhost:5678`)
2. Clique em **"New workflow"**
3. Dê um nome: "RAG Multimodal Query"

### 3.2. Adicionar Trigger (Webhook)

1. Clique no **"+"** para adicionar node
2. Pesquise e selecione: **"Webhook"**
3. Configure:
   - **HTTP Method:** `POST`
   - **Path:** `rag-query`
   - **Response Mode:** `When Last Node Finishes`
   - **Response Code:** `200`

**URL gerada será algo como:**
```
http://localhost:5678/webhook/rag-query
```

### 3.3. Adicionar HTTP Request Node

1. Clique no **"+"** após o Webhook
2. Pesquise e selecione: **"HTTP Request"**
3. Configure:

#### ⚙️ Configurações Básicas:
- **Method:** `POST`
- **URL:** `http://localhost:5000/query`
- **Authentication:** `None`

#### ⚙️ Headers:
Clique em **"Add Option"** → **"Headers"**

| Name | Value |
|------|-------|
| `Content-Type` | `application/json` |

#### ⚙️ Body (JSON):
Clique em **"Body"** → **"JSON"**

```json
{
  "question": "={{ $json.question }}"
}
```

**Explicação:**
- `{{ $json.question }}` pega o campo `question` do webhook

### 3.4. Adicionar Response Node (Opcional)

Para formatar a resposta:

1. Adicione node **"Set"** ou **"Code"**
2. Configure para retornar resposta formatada

**Exemplo com Code Node:**
```javascript
const response = $input.first().json;

return [{
  json: {
    answer: response.answer,
    sources: response.sources,
    reranked: response.reranked || false
  }
}];
```

---

## 🧪 PASSO 4: Testar o Workflow n8n

### Teste via Postman/Insomnia/cURL:

```bash
curl -X POST http://localhost:5678/webhook/rag-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais os critérios diagnósticos da síndrome de lise tumoral?"
  }'
```

**Resposta esperada:**
```json
{
  "answer": "Os critérios diagnósticos incluem...",
  "sources": ["Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf"],
  "reranked": true
}
```

---

## 🌟 PASSO 5: Exemplos Avançados n8n

### Exemplo 1: Chatbot com Histórico

```
┌─────────────┐
│   Webhook   │  → Recebe pergunta
└──────┬──────┘
       │
┌──────▼──────┐
│  HTTP Req   │  → Consulta RAG
│  (RAG API)  │
└──────┬──────┘
       │
┌──────▼──────┐
│   Slack     │  → Envia resposta
│   (Send)    │
└─────────────┘
```

### Exemplo 2: Processar Múltiplas Perguntas

```
┌─────────────┐
│   Webhook   │  → Lista de perguntas
└──────┬──────┘
       │
┌──────▼──────┐
│  Split Out  │  → Separa perguntas
└──────┬──────┘
       │
┌──────▼──────┐
│  HTTP Req   │  → Query para cada
│  (Loop)     │
└──────┬──────┘
       │
┌──────▼──────┐
│  Aggregate  │  → Junta respostas
└─────────────┘
```

### Exemplo 3: Integração com Google Sheets

```
┌─────────────┐
│ Google      │
│ Sheets      │  → Trigger: Nova linha
│ (Trigger)   │
└──────┬──────┘
       │
┌──────▼──────┐
│  HTTP Req   │  → Consulta RAG
│  (RAG API)  │
└──────┬──────┘
       │
┌──────▼──────┐
│ Google      │  → Atualiza resposta
│ Sheets      │
│ (Update)    │
└─────────────┘
```

---

## 🔍 PASSO 6: Configuração JSON Completa n8n

Copie e importe no n8n (Menu → Import from File):

```json
{
  "name": "RAG Multimodal Query",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "rag-query",
        "responseMode": "lastNode",
        "options": {}
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [240, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:5000/query",
        "options": {
          "headers": {
            "header": [
              {
                "name": "Content-Type",
                "value": "application/json"
              }
            ]
          }
        },
        "bodyParametersJson": "={{ JSON.stringify({question: $json.question}) }}"
      },
      "name": "RAG Query",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [460, 300]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ $json }}"
      },
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [680, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "RAG Query", "type": "main", "index": 0}]]
    },
    "RAG Query": {
      "main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]
    }
  }
}
```

---

## ⚠️ Troubleshooting

### Erro: "Connection refused"

**Problema:** API não está rodando

**Solução:**
```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate
python consultar_com_rerank.py --api
```

### Erro: "CORS error"

**Problema:** CORS não configurado

**Solução:** Já está configurado! Se persistir, adicione headers:
```javascript
// No n8n HTTP Request
headers: {
  "Content-Type": "application/json",
  "Origin": "http://localhost:5678"
}
```

### Erro: "Empty response"

**Problema:** JSON malformado

**Solução:** Certifique-se que está enviando:
```json
{
  "question": "sua pergunta aqui"
}
```

### API Muito Lenta

**Problema:** Muitos documentos ou reranker ativo

**Soluções:**
1. Use API sem reranker: `python consultar.py --api`
2. Reduza número de documentos
3. Use cache no n8n

---

## 📊 Exemplo de Uso Completo

### 1. Iniciar API
```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate
python consultar_com_rerank.py --api
```

### 2. Configurar n8n
- Importar JSON acima
- Ativar workflow

### 3. Testar
```bash
curl -X POST http://localhost:5678/webhook/rag-query \
  -H "Content-Type: application/json" \
  -d '{"question": "O que é nefrite lúpica?"}'
```

### 4. Resposta
```json
{
  "answer": "Nefrite lúpica é uma manifestação renal do lúpus...",
  "sources": ["Artigo de Revisão - Nature Review Disease Primers - Nefrite Lúpica.pdf"],
  "reranked": true
}
```

---

## 🎯 Próximos Passos

1. ✅ **Deploy:** Use ngrok para expor API publicamente
2. ✅ **Segurança:** Adicione autenticação (API key)
3. ✅ **Escala:** Use gunicorn para múltiplos workers
4. ✅ **Monitoramento:** Log queries e respostas

---

## 📞 Suporte

Se tiver problemas:
1. Verifique se API está rodando (`curl http://localhost:5000/health`)
2. Teste endpoint direto (sem n8n)
3. Verifique logs da API no terminal
4. Verifique execução no n8n (botão "Executions")

---

**🎉 Pronto! Seu RAG está integrado com n8n!**

