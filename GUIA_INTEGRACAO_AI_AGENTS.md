# 🤖 Guia Completo: Integrar AI Agents com seu RAG

## 📋 Índice
1. [O que é e para que serve](#o-que-e)
2. [Visão Geral da Integração](#visao-geral)
3. [Seu Endpoint Já Está Pronto!](#endpoint-pronto)
4. [Passo a Passo: Integração com Diferentes Plataformas](#integracao-plataformas)
   - [n8n (No-Code)](#n8n)
   - [Make.com (No-Code)](#make)
   - [Zapier (No-Code)](#zapier)
   - [Custom Code (Para Desenvolvedores)](#custom-code)
5. [Exemplos Práticos de Uso](#exemplos-praticos)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 O que é e para que serve? {#o-que-e}

### O que você JÁ TEM:
Você já possui um **sistema RAG multimodal** (texto + tabelas + imagens) rodando na Railway. Ele:
- ✅ Processa PDFs médicos
- ✅ Responde perguntas usando GPT-4o
- ✅ Busca em documentos com alta precisão (Cohere Rerank)
- ✅ Entende imagens (GPT-4o Vision)

### O que você VAI TER:
Outros **AI Agents** (robôs/assistentes) poderão:
- 📞 Fazer perguntas ao seu RAG via HTTP
- 🤝 Usar seu conhecimento médico em workflows automatizados
- 🔗 Integrar com n8n, Make.com, Zapier, ou qualquer plataforma

### Exemplo Prático:
```
User pergunta no WhatsApp →
  AI Agent no n8n recebe →
    Agent consulta SEU RAG via HTTP →
      Seu RAG responde com base nos PDFs médicos →
        Agent formata e envia resposta no WhatsApp
```

---

## 🔍 Visão Geral da Integração {#visao-geral}

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent (n8n/Make/Zapier)               │
│  - Recebe pergunta do usuário                               │
│  - Pode processar antes/depois                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP POST Request
                 │ (JSON com a pergunta)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              SEU RAG na Railway (Já existe!)                │
│  URL: https://comfortable-tenderness-production.up.railway.app │
│  Endpoint: /query                                           │
│  Método: POST                                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Processa:
                 │ 1. Busca nos PDFs (Hybrid Search + Rerank)
                 │ 2. Inclui imagens se relevante
                 │ 3. Gera resposta com GPT-4o
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    Resposta (JSON)                          │
│  - response: "texto da resposta"                            │
│  - sources: ["documento1.pdf", "documento2.pdf"]            │
│  - num_chunks: 8                                            │
│  - has_images: true/false                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Seu Endpoint Já Está Pronto! {#endpoint-pronto}

### 📍 Informações do Endpoint

**URL Base:** `https://comfortable-tenderness-production.up.railway.app`

**Endpoint Principal:** `/query`

**Método HTTP:** `POST`

**Content-Type:** `application/json`

### 📤 Formato da Requisição

```json
{
  "question": "Quais critérios de muito alto risco cardiovascular em diabetes?"
}
```

### 📥 Formato da Resposta

```json
{
  "response": "Os critérios de muito alto risco cardiovascular em diabetes tipo 2 incluem:\n\n1. Hipercolesterolemia Familiar\n2. 3 ou mais fatores de risco\n3. Albuminúria >300mg/g\n4. TFG <30ml/min\n5. Retinopatia diabética proliferativa\n6. Síndrome coronariana aguda prévia",
  "sources": [
    "diretriz_diabetes_2025.pdf",
    "risco_cardiovascular.pdf"
  ],
  "num_chunks": 8,
  "has_images": false,
  "processing_time": 3.2
}
```

### 🔐 Segurança (Opcional)

Atualmente, o endpoint está **aberto** (sem autenticação). Se precisar proteger:

1. Adicione no Railway (variável de ambiente):
   ```
   API_SECRET_KEY=sua_chave_secreta_aqui
   ```

2. Envie no header da requisição:
   ```
   X-API-Key: sua_chave_secreta_aqui
   ```

---

## 🛠️ Passo a Passo: Integração com Diferentes Plataformas {#integracao-plataformas}

### 1️⃣ n8n (No-Code) {#n8n}

**O que é n8n?**
Plataforma open-source de automação visual (arrasta e solta).

#### Passo a Passo Detalhado:

**PASSO 1: Criar Workflow no n8n**

1. Acesse seu n8n
2. Clique em **"+ New Workflow"**
3. Dê um nome: **"RAG Medical Assistant"**

**PASSO 2: Adicionar Trigger (Gatilho)**

Escolha como seu workflow será acionado. Exemplos:

**Opção A - Webhook (Recomendado para testes):**
1. Procure por **"Webhook"** nos nodes
2. Arraste para o canvas
3. Configure:
   - **HTTP Method:** `GET` ou `POST`
   - **Path:** `medical-question` (ou qualquer nome)
4. n8n criará uma URL automática:
   ```
   https://seu-n8n.com/webhook/medical-question
   ```
5. **IMPORTANTE:** Copie essa URL para testar depois

**Opção B - Manual Trigger (Para testes manuais):**
1. Procure por **"Manual Trigger"**
2. Arraste para o canvas
3. Adicione um node **"Edit Fields"** para simular a pergunta:
   - Field Name: `question`
   - Field Value: `"Quais critérios de muito alto risco?"`

**PASSO 3: Adicionar Node HTTP Request**

1. Clique no **"+"** após o trigger
2. Procure por **"HTTP Request"**
3. Arraste para o canvas

**PASSO 4: Configurar HTTP Request**

Preencha os campos exatamente assim:

```
┌─────────────────────────────────────────────────────────┐
│ HTTP Request Configuration                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Authentication: None                                    │
│ (se você configurou API_SECRET_KEY, use "Generic       │
│  Credential Type" e adicione o header)                 │
│                                                         │
│ Request Method: POST                                    │
│                                                         │
│ URL: https://comfortable-tenderness-production.up.railway.app/query │
│                                                         │
│ Send Body: Yes                                          │
│                                                         │
│ Body Content Type: JSON                                 │
│                                                         │
│ Specify Body: Using JSON                                │
│                                                         │
│ JSON:                                                   │
│ {                                                       │
│   "question": "{{ $json.question }}"                    │
│ }                                                       │
│                                                         │
│ Options:                                                │
│   Response Format: JSON                                 │
│   Timeout: 30000 (30 segundos)                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Explicação do JSON:**
- `{{ $json.question }}`: Pega o valor do campo "question" que veio do trigger
- Se o trigger foi um Webhook com `?question=...`, ele captura automaticamente
- Se foi Manual, pega do campo que você configurou

**PASSO 5: Adicionar Node de Formatação (Opcional)**

Se quiser formatar a resposta antes de enviar:

1. Adicione node **"Code"** ou **"Set"**
2. Configure:

```javascript
// Exemplo: Extrair só a resposta
return [
  {
    json: {
      answer: $input.item.json.response,
      sources: $input.item.json.sources.join(', '),
      num_docs: $input.item.json.sources.length
    }
  }
];
```

**PASSO 6: Adicionar Node de Saída**

Escolha para onde enviar a resposta:

**Opção A - Responder no Webhook:**
1. Adicione node **"Respond to Webhook"**
2. Configure:
   - Response Body: `{{ $json.response }}`

**Opção B - Enviar por Email:**
1. Adicione node **"Send Email"**
2. Configure SMTP
3. Body: `{{ $json.response }}`

**Opção C - Enviar no WhatsApp (via Twilio/Evolution API):**
1. Adicione node **"Twilio"** ou **"HTTP Request"**
2. Configure API do WhatsApp
3. Message: `{{ $json.response }}`

**Opção D - Salvar em Banco de Dados:**
1. Adicione node **"Postgres"** ou **"MongoDB"**
2. Insira pergunta + resposta

**PASSO 7: Testar o Workflow**

**Teste Manual:**
1. Clique em **"Execute Workflow"** (botão de play no topo)
2. Veja os resultados em cada node (bolinhas verdes = sucesso)

**Teste via Webhook:**
1. Copie a URL do webhook
2. Abra o navegador ou Postman
3. Acesse:
   ```
   https://seu-n8n.com/webhook/medical-question?question=Quais%20critérios%20de%20muito%20alto%20risco?
   ```
4. Veja a resposta!

**PASSO 8: Ativar Workflow**

1. Clique no toggle **"Active"** no canto superior direito
2. Workflow agora roda automaticamente quando triggered!

---

#### Exemplo de Workflow Completo n8n:

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Webhook    │ ───> │ HTTP Request │ ───> │     Code     │ ───> │   Respond    │
│              │      │   (Seu RAG)  │      │   (Format)   │      │  to Webhook  │
│ Recebe       │      │ POST /query  │      │ Extrai info  │      │ Retorna JSON │
│ question     │      │              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
```

#### Workflow JSON para Importar (Copie e Cole no n8n):

```json
{
  "name": "RAG Medical Assistant",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "medical-question",
        "options": {}
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "https://comfortable-tenderness-production.up.railway.app/query",
        "method": "POST",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\"question\": \"{{ $json.question }}\"}",
        "options": {
          "timeout": 30000
        }
      },
      "name": "HTTP Request - RAG",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [450, 300]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ $json }}"
      },
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [650, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "HTTP Request - RAG", "type": "main", "index": 0}]]
    },
    "HTTP Request - RAG": {
      "main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]
    }
  }
}
```

**Como importar:**
1. No n8n, clique em **"Import from File"** ou **"Import from URL"**
2. Cole o JSON acima
3. Clique em **"Import"**
4. Pronto! Workflow importado

---

### 2️⃣ Make.com (Integromat) {#make}

**O que é Make.com?**
Plataforma visual de automação (similar ao n8n, mas SaaS).

#### Passo a Passo Detalhado:

**PASSO 1: Criar Novo Scenario**

1. Acesse https://make.com
2. Clique em **"Create a new scenario"**
3. Dê um nome: **"Medical RAG Assistant"**

**PASSO 2: Adicionar Trigger**

Exemplos de triggers:

**Opção A - Webhook:**
1. Clique no **"+"** inicial
2. Procure por **"Webhooks"**
3. Selecione **"Custom webhook"**
4. Clique em **"Add"** para criar novo webhook
5. Dê um nome: **"Medical Question"**
6. Copie a URL gerada
7. Clique em **"OK"**

**Opção B - Google Sheets:**
1. Procure **"Google Sheets"**
2. Selecione **"Watch Rows"**
3. Configure para monitorar uma planilha
4. Coluna A: Pergunta médica
5. Quando nova linha for adicionada, trigger dispara

**Opção C - Email:**
1. Procure **"Email"**
2. Selecione **"Watch emails"**
3. Configure sua caixa de email
4. Quando chegar email, extrai a pergunta do body

**PASSO 3: Adicionar Módulo HTTP**

1. Clique no **"+"** após o trigger
2. Procure por **"HTTP"**
3. Selecione **"Make a request"**

**PASSO 4: Configurar HTTP Request**

Preencha exatamente assim:

```
┌─────────────────────────────────────────────────────────┐
│ HTTP - Make a Request                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ URL: https://comfortable-tenderness-production.up.railway.app/query │
│                                                         │
│ Method: POST                                            │
│                                                         │
│ Headers:                                                │
│   Name: Content-Type                                    │
│   Value: application/json                               │
│                                                         │
│ Body Type: Raw                                          │
│                                                         │
│ Content Type: JSON (application/json)                   │
│                                                         │
│ Request content:                                        │
│ {                                                       │
│   "question": "{{1.question}}"                          │
│ }                                                       │
│                                                         │
│ Parse response: Yes                                     │
│                                                         │
│ Timeout: 30                                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Explicação:**
- `{{1.question}}`: Referência ao campo "question" do primeiro módulo (trigger)
- Se o trigger foi webhook, vai pegar do JSON recebido
- Se foi Google Sheets, vai pegar da coluna que você mapeou

**PASSO 5: Adicionar Ação de Saída**

Exemplos:

**Opção A - Webhook Response:**
1. Adicione módulo **"Webhooks"** > **"Webhook Response"**
2. Status: `200`
3. Body:
   ```json
   {
     "answer": "{{2.response}}",
     "sources": "{{join(2.sources; ', ')}}"
   }
   ```

**Opção B - Enviar Email:**
1. Adicione **"Email"** > **"Send an Email"**
2. To: Email do usuário
3. Subject: `Resposta da consulta médica`
4. Content:
   ```
   Pergunta: {{1.question}}

   Resposta:
   {{2.response}}

   Fontes consultadas:
   {{join(2.sources; '\n')}}
   ```

**Opção C - Atualizar Google Sheets:**
1. Adicione **"Google Sheets"** > **"Update a Row"**
2. Spreadsheet: Sua planilha
3. Coluna B: `{{2.response}}`
4. Coluna C: `{{join(2.sources; ', ')}}`

**Opção D - Enviar no Slack:**
1. Adicione **"Slack"** > **"Create a Message"**
2. Channel: #medical-bot
3. Text:
   ```
   *Pergunta:* {{1.question}}

   *Resposta:*
   {{2.response}}

   *Fontes:* {{join(2.sources; ', ')}}
   ```

**PASSO 6: Testar o Scenario**

1. Clique em **"Run once"** (botão play na parte inferior)
2. Se for webhook, faça uma requisição:
   ```bash
   curl -X POST https://hook.make.com/seu-webhook-id \
     -H "Content-Type: application/json" \
     -d '{"question": "Quais critérios de muito alto risco?"}'
   ```
3. Veja os resultados em cada módulo (check verde = sucesso)

**PASSO 7: Ativar Scenario**

1. Clique no toggle **"ON"** no canto inferior esquerdo
2. Configure o schedule se necessário:
   - Immediately (tempo real)
   - Every 15 minutes
   - Custom schedule

**PASSO 8: Monitorar Execuções**

1. Vá em **"History"** para ver todas execuções
2. Clique em cada execução para debug
3. Veja erros, tempos, dados processados

---

#### Blueprint para Importar no Make.com:

```json
{
  "name": "Medical RAG Assistant",
  "flow": [
    {
      "id": 1,
      "module": "gateway:CustomWebHook",
      "version": 1,
      "parameters": {
        "hook": "medical-question",
        "maxResults": 1
      }
    },
    {
      "id": 2,
      "module": "http:ActionSendData",
      "version": 3,
      "parameters": {},
      "mapper": {
        "url": "https://comfortable-tenderness-production.up.railway.app/query",
        "method": "POST",
        "headers": [
          {
            "name": "Content-Type",
            "value": "application/json"
          }
        ],
        "qs": [],
        "bodyType": "raw",
        "parseResponse": true,
        "timeout": 30,
        "shareCookies": false,
        "ca": "",
        "rejectUnauthorized": true,
        "followRedirect": true,
        "useQuerystring": false,
        "gzip": true,
        "useMtls": false,
        "contentType": "application/json",
        "body": "{\"question\": \"{{1.question}}\"}"
      }
    },
    {
      "id": 3,
      "module": "gateway:WebhookRespond",
      "version": 1,
      "parameters": {},
      "mapper": {
        "status": "200",
        "body": "{{2.response}}",
        "headers": []
      }
    }
  ],
  "metadata": {
    "version": 1
  }
}
```

---

### 3️⃣ Zapier {#zapier}

**O que é Zapier?**
Plataforma de automação mais popular (foco em integrações prontas).

#### Passo a Passo Detalhado:

**PASSO 1: Criar Novo Zap**

1. Acesse https://zapier.com
2. Clique em **"Create Zap"**
3. Dê um nome: **"Medical RAG Bot"**

**PASSO 2: Escolher Trigger**

Exemplos:

**Opção A - Google Forms:**
1. Trigger: **"Google Forms"**
2. Event: **"New Form Response"**
3. Conecte sua conta Google
4. Escolha o formulário médico
5. Campo "Pergunta" será a question

**Opção B - Typeform:**
1. Trigger: **"Typeform"**
2. Event: **"New Entry"**
3. Conecte sua conta Typeform
4. Mapeia campo da pergunta

**Opção C - Slack:**
1. Trigger: **"Slack"**
2. Event: **"New Message Posted to Channel"**
3. Channel: #medical-questions
4. Texto da mensagem = question

**Opção D - Email Parser:**
1. Trigger: **"Email Parser by Zapier"**
2. Configure um mailbox
3. Defina regex para extrair pergunta

**PASSO 3: Adicionar Ação Webhooks**

1. Clique em **"+"** para adicionar ação
2. Procure por **"Webhooks by Zapier"**
3. Action Event: **"POST"**
4. Clique em **"Continue"**

**PASSO 4: Configurar Webhook**

Preencha exatamente assim:

```
┌─────────────────────────────────────────────────────────┐
│ Webhooks by Zapier - POST                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ URL: https://comfortable-tenderness-production.up.railway.app/query │
│                                                         │
│ Payload Type: JSON                                      │
│                                                         │
│ Data:                                                   │
│   question: [Clique e selecione campo do trigger]      │
│   (Ex: Google Forms > Question)                         │
│                                                         │
│ Wrap Request In Array: No                               │
│                                                         │
│ Unflatten: No                                           │
│                                                         │
│ Headers:                                                │
│   Content-Type: application/json                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**PASSO 5: Testar a Ação**

1. Clique em **"Test action"**
2. Zapier enviará requisição real para seu RAG
3. Veja a resposta em "Response"
4. Verifique:
   - `response`: Resposta do RAG
   - `sources`: Lista de PDFs
   - `num_chunks`: Número de chunks

**PASSO 6: Adicionar Ação de Saída**

Exemplos:

**Opção A - Enviar Email:**
1. Action: **"Gmail"** > **"Send Email"**
2. To: Email do usuário (do trigger)
3. Subject: `Sua consulta médica`
4. Body:
   ```
   Pergunta: [Campo question do trigger]

   Resposta:
   [Campo response do Webhook]

   Documentos consultados:
   [Campo sources do Webhook]
   ```

**Opção B - Adicionar em Google Sheets:**
1. Action: **"Google Sheets"** > **"Create Spreadsheet Row"**
2. Spreadsheet: "Medical Questions Log"
3. Colunas:
   - A: Timestamp
   - B: [Question do trigger]
   - C: [Response do Webhook]
   - D: [Sources do Webhook]

**Opção C - Enviar no Slack:**
1. Action: **"Slack"** > **"Send Channel Message"**
2. Channel: #medical-bot
3. Message:
   ```
   :medical_symbol: *Nova Consulta*

   *Pergunta:*
   [Question]

   *Resposta:*
   [Response]

   *Fontes:* [Sources]
   ```

**Opção D - SMS via Twilio:**
1. Action: **"Twilio"** > **"Send SMS"**
2. To: Número do usuário
3. Message:
   ```
   Resposta: [Primeiros 300 chars do Response]

   Veja detalhes em [link]
   ```

**PASSO 7: Testar Zap Completo**

1. Clique em **"Test & Review"**
2. Zapier executa todo o fluxo
3. Verifique cada step (check verde = sucesso)
4. Veja o email/Slack/Sheet para confirmar

**PASSO 8: Publicar Zap**

1. Clique em **"Publish"**
2. Zap agora roda automaticamente!
3. Cada novo trigger dispara o fluxo

**PASSO 9: Monitorar**

1. Vá em **"Zap History"**
2. Veja todas execuções (sucesso/erro)
3. Clique em cada uma para debug
4. Filtre por data, status, etc.

---

### 4️⃣ Custom Code (Para Desenvolvedores) {#custom-code}

Se você ou seu desenvolvedor quiser integrar via código:

#### Python:

```python
import requests

def consultar_rag(pergunta):
    """
    Consulta o RAG médico via API

    Args:
        pergunta (str): Pergunta médica

    Returns:
        dict: Resposta com answer, sources, etc.
    """
    url = "https://comfortable-tenderness-production.up.railway.app/query"

    payload = {
        "question": pergunta
    }

    headers = {
        "Content-Type": "application/json"
        # Se tiver API key:
        # "X-API-Key": "sua_chave_secreta"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()  # Erro se status != 200

        data = response.json()

        return {
            "answer": data.get("response", ""),
            "sources": data.get("sources", []),
            "num_chunks": data.get("num_chunks", 0),
            "has_images": data.get("has_images", False)
        }

    except requests.exceptions.Timeout:
        return {"error": "Timeout após 30 segundos"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Erro na requisição: {str(e)}"}
    except ValueError:
        return {"error": "Resposta não é JSON válido"}


# Exemplo de uso
if __name__ == "__main__":
    pergunta = "Quais critérios de muito alto risco cardiovascular em diabetes?"

    resultado = consultar_rag(pergunta)

    if "error" in resultado:
        print(f"❌ Erro: {resultado['error']}")
    else:
        print(f"✅ Resposta:\n{resultado['answer']}\n")
        print(f"📚 Fontes: {', '.join(resultado['sources'])}")
        print(f"📊 Chunks usados: {resultado['num_chunks']}")
```

#### JavaScript (Node.js):

```javascript
const axios = require('axios');

async function consultarRAG(pergunta) {
    const url = 'https://comfortable-tenderness-production.up.railway.app/query';

    const payload = {
        question: pergunta
    };

    const config = {
        headers: {
            'Content-Type': 'application/json'
            // Se tiver API key:
            // 'X-API-Key': 'sua_chave_secreta'
        },
        timeout: 30000  // 30 segundos
    };

    try {
        const response = await axios.post(url, payload, config);

        return {
            answer: response.data.response || '',
            sources: response.data.sources || [],
            num_chunks: response.data.num_chunks || 0,
            has_images: response.data.has_images || false
        };

    } catch (error) {
        if (error.code === 'ECONNABORTED') {
            return { error: 'Timeout após 30 segundos' };
        } else if (error.response) {
            return { error: `Erro ${error.response.status}: ${error.response.data}` };
        } else {
            return { error: `Erro na requisição: ${error.message}` };
        }
    }
}

// Exemplo de uso
(async () => {
    const pergunta = 'Quais critérios de muito alto risco cardiovascular em diabetes?';

    const resultado = await consultarRAG(pergunta);

    if (resultado.error) {
        console.log(`❌ Erro: ${resultado.error}`);
    } else {
        console.log(`✅ Resposta:\n${resultado.answer}\n`);
        console.log(`📚 Fontes: ${resultado.sources.join(', ')}`);
        console.log(`📊 Chunks usados: ${resultado.num_chunks}`);
    }
})();
```

#### cURL (Linha de comando):

```bash
#!/bin/bash

# Consultar RAG via cURL

QUESTION="Quais critérios de muito alto risco cardiovascular em diabetes?"

curl -X POST "https://comfortable-tenderness-production.up.railway.app/query" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"$QUESTION\"}" \
  --max-time 30 \
  | python3 -m json.tool
```

#### PHP:

```php
<?php

function consultarRAG($pergunta) {
    $url = 'https://comfortable-tenderness-production.up.railway.app/query';

    $data = array('question' => $pergunta);
    $payload = json_encode($data);

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array(
        'Content-Type: application/json'
        // Se tiver API key:
        // 'X-API-Key: sua_chave_secreta'
    ));
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

    curl_close($ch);

    if ($httpCode === 200) {
        $data = json_decode($response, true);
        return array(
            'answer' => $data['response'] ?? '',
            'sources' => $data['sources'] ?? array(),
            'num_chunks' => $data['num_chunks'] ?? 0
        );
    } else {
        return array('error' => "HTTP $httpCode: $response");
    }
}

// Exemplo de uso
$pergunta = 'Quais critérios de muito alto risco cardiovascular em diabetes?';
$resultado = consultarRAG($pergunta);

if (isset($resultado['error'])) {
    echo "❌ Erro: {$resultado['error']}\n";
} else {
    echo "✅ Resposta:\n{$resultado['answer']}\n\n";
    echo "📚 Fontes: " . implode(', ', $resultado['sources']) . "\n";
}
?>
```

---

## 💡 Exemplos Práticos de Uso {#exemplos-praticos}

### Exemplo 1: Bot de WhatsApp com n8n

**Cenário:**
Paciente envia mensagem no WhatsApp → Bot responde usando RAG

**Workflow:**
1. **Trigger:** WhatsApp (via Evolution API ou Twilio)
2. **Node 1:** Extrair texto da mensagem
3. **Node 2:** HTTP Request para seu RAG
4. **Node 3:** Formatar resposta
5. **Node 4:** Enviar resposta no WhatsApp

**Configuração Especial:**
- Adicionar contexto: "Paciente: [nome]"
- Salvar histórico em banco
- Limitar tamanho da resposta (WhatsApp tem limite de caracteres)

---

### Exemplo 2: Sistema de Tickets (Zendesk/Freshdesk)

**Cenário:**
Cliente abre ticket → Sistema sugere resposta automaticamente

**Workflow:**
1. **Trigger:** Novo ticket criado
2. **Node 1:** Extrair pergunta do ticket
3. **Node 2:** Consultar RAG
4. **Node 3:** Criar nota interna com resposta sugerida
5. **Node 4:** Notificar agente

**Benefício:**
- Agente vê sugestão do RAG
- Pode editar antes de enviar
- Reduz tempo de resposta

---

### Exemplo 3: Chatbot em Site (Typebot/Botpress)

**Cenário:**
Visitante do site faz pergunta → Chatbot responde usando RAG

**Integração:**
1. Chatbot coleta pergunta
2. Faz webhook para n8n/Make
3. n8n consulta seu RAG
4. Retorna resposta formatada
5. Chatbot exibe resposta

**Vantagens:**
- Interface amigável no site
- Backend poderoso (seu RAG)
- Atualização fácil (só adicionar PDFs)

---

### Exemplo 4: Assistente Médico por Voz (Alexa/Google Assistant)

**Cenário:**
Médico pergunta por voz → Assistente responde usando RAG

**Workflow:**
1. **Trigger:** Comando de voz
2. **Node 1:** Speech-to-Text
3. **Node 2:** Consultar RAG
4. **Node 3:** Text-to-Speech
5. **Node 4:** Reproduzir áudio

**Ferramentas:**
- Google Cloud Speech-to-Text
- OpenAI TTS (text-to-speech)
- n8n para orquestração

---

### Exemplo 5: Dashboard de Métricas

**Cenário:**
Monitorar perguntas mais frequentes e performance

**Workflow:**
1. Toda consulta ao RAG é logada
2. Google Sheets recebe:
   - Timestamp
   - Pergunta
   - Resposta
   - Fontes usadas
   - Tempo de resposta
3. Google Data Studio cria dashboard
4. Visualiza:
   - Perguntas mais comuns
   - Documentos mais consultados
   - Performance ao longo do tempo

---

## 🔧 Troubleshooting {#troubleshooting}

### Erro: "Connection timeout"

**Causa:** Requisição levou mais de 30 segundos

**Solução:**
1. Aumentar timeout para 60 segundos
2. Verificar se Railway está com problema
3. Checar se knowledge base está muito grande

---

### Erro: "404 Not Found"

**Causa:** URL incorreta

**Verificar:**
- URL: `https://comfortable-tenderness-production.up.railway.app/query` ✅
- Não esquecer o `/query` no final
- Não usar `/ask` ou `/consultar`

---

### Erro: "400 Bad Request - Campo 'question' obrigatório"

**Causa:** JSON mal formatado

**Solução:**
Verificar se enviou:
```json
{
  "question": "sua pergunta aqui"
}
```

**NÃO enviar:**
```json
{
  "query": "...",      // ❌ Errado
  "pergunta": "...",   // ❌ Errado
  "text": "..."        // ❌ Errado
}
```

---

### Erro: "500 Internal Server Error"

**Causa:** Erro no servidor

**Verificar:**
1. Acessar logs da Railway
2. Ver se knowledge base está vazia
3. Checar se API keys (OpenAI, Cohere) estão válidas

**Como ver logs:**
```bash
railway logs --project comfortable-tenderness-production
```

---

### Resposta: "Knowledge base vazia"

**Causa:** Nenhum PDF processado

**Solução:**
1. Acessar: `https://comfortable-tenderness-production.up.railway.app/manage`
2. Fazer upload de PDFs
3. Aguardar processamento
4. Tentar novamente

---

### Resposta muito lenta (>30 segundos)

**Causas possíveis:**
1. Knowledge base muito grande
2. Query muito complexa
3. Muitas imagens sendo processadas

**Soluções:**
1. Aumentar timeout para 60s
2. Otimizar query (ser mais específico)
3. Verificar se Railway precisa de upgrade de plano

---

### Imagens não aparecem na resposta

**Verificar:**
1. Se a pergunta menciona "figura", "imagem", "fluxograma"
2. Se o PDF realmente tem imagens
3. Acessar `/debug-volume` para ver se imagens foram extraídas

**Teste:**
```bash
curl "https://comfortable-tenderness-production.up.railway.app/debug-volume"
```

Procurar por: `"images": X` (X > 0)

---

### Rate limit / Muitas requisições

**Sintoma:** Erro 429 ou respostas bloqueadas

**Solução:**
1. Implementar rate limiting no seu lado
2. Cachear respostas frequentes
3. Considerar adicionar API key para controle

---

## 📞 Suporte

### Testar Endpoint Manualmente:

**Via navegador:**
Não funciona (POST não é GET)

**Via Postman:**
1. Abra Postman
2. Método: POST
3. URL: `https://comfortable-tenderness-production.up.railway.app/query`
4. Headers: `Content-Type: application/json`
5. Body (raw JSON):
   ```json
   {
     "question": "Quais critérios de muito alto risco?"
   }
   ```
6. Send

**Via cURL:**
```bash
curl -X POST "https://comfortable-tenderness-production.up.railway.app/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quais critérios de muito alto risco cardiovascular?"}'
```

---

### Endpoints Adicionais Úteis:

**Health Check:**
```
GET https://comfortable-tenderness-production.up.railway.app/health
```

**Listar Documentos:**
```
GET https://comfortable-tenderness-production.up.railway.app/documents
```

**Debug Volume:**
```
GET https://comfortable-tenderness-production.up.railway.app/debug-volume
```

**Interface de Gerenciamento:**
```
https://comfortable-tenderness-production.up.railway.app/manage
```

---

## 🎓 Resumo Executivo

### Para Não-Programadores:

**O que você tem:**
- ✅ API RAG funcionando na Railway
- ✅ Endpoint `/query` pronto para receber perguntas
- ✅ Responde em JSON com answer + sources

**Como integrar:**
1. **n8n:** Arrasta nó HTTP Request, configura URL + POST + JSON
2. **Make.com:** Adiciona módulo HTTP, configura URL + POST + JSON
3. **Zapier:** Usa Webhooks by Zapier, configura URL + POST + Data

**Formato sempre o mesmo:**
```json
Enviar: {"question": "sua pergunta"}
Receber: {"response": "resposta", "sources": [...]}
```

**Próximos passos:**
1. Escolha plataforma (recomendo n8n se tiver servidor, Make.com se não)
2. Crie workflow seguindo passo a passo acima
3. Teste com pergunta simples
4. Conecte com saída desejada (WhatsApp/Email/etc)
5. Ative e monitore!

---

**Documentação criada em:** 2025-10-22
**Última atualização:** 2025-10-22
**Status:** ✅ Pronto para uso
