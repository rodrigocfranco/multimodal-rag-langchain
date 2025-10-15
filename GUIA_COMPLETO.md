# Guia Completo - Sistema RAG Funcionando

## Passo 1: Obter URL do Railway

1. Acesse seu projeto no Railway: https://railway.app
2. Clique no seu projeto `multimodal-rag-langchain`
3. Na aba **Settings**, procure por **"Domains"** ou **"Public URL"**
4. Copie a URL (será algo como: `https://seu-app.up.railway.app`)

**Vamos chamar essa URL de `[SUA_URL_RAILWAY]` nos exemplos abaixo.**

---

## Passo 2: Testar se a API está Funcionando

### 2.1 Health Check

Abra o navegador ou terminal:

```bash
curl https://[SUA_URL_RAILWAY]/health
```

**Resposta esperada:**
```json
{
  "status": "ok",
  "reranker": "cohere"
}
```

### 2.2 Página inicial (Documentação)

```bash
curl https://[SUA_URL_RAILWAY]/
```

Ou abra no navegador: `https://[SUA_URL_RAILWAY]/`

---

## Passo 3: Popular a Vector Store com PDFs

### Opção A: Via Interface Web (Recomendado)

1. **Acesse a UI de Upload:**
   ```
   https://[SUA_URL_RAILWAY]/ui
   ```

2. **Faça upload de um PDF:**
   - Clique em "Choose File"
   - Selecione um PDF (exemplo: artigo médico, manual, etc)
   - Clique em "📡 Enviar com acompanhamento (tempo real)"
   - Aguarde 5-10 minutos (você verá o progresso em tempo real)

3. **Aguarde o processamento:**
   - O sistema vai extrair textos, tabelas e imagens
   - Gerar resumos com IA (Llama 3.1)
   - Armazenar no ChromaDB com embeddings OpenAI

### Opção B: Via API (cURL)

```bash
curl -X POST https://[SUA_URL_RAILWAY]/upload \
  -F "file=@/caminho/para/seu/arquivo.pdf"
```

### Opção C: Via Python

```python
import requests

url = "https://[SUA_URL_RAILWAY]/upload"
files = {"file": open("seu_arquivo.pdf", "rb")}

response = requests.post(url, files=files)
print(response.json())
```

**Importante:** O primeiro upload demora mais (5-10 min) porque processa tudo.

---

## Passo 4: Testar o RAG (Fazer Queries)

### Opção A: Via Interface Web de Chat

1. **Acesse:**
   ```
   https://[SUA_URL_RAILWAY]/chat
   ```

2. **Digite uma pergunta relacionada ao PDF que você enviou:**
   - Exemplo: "Quais são os principais tratamentos mencionados?"
   - Exemplo: "Resuma o conteúdo do documento"
   - Exemplo: "O que diz sobre hipertensão?"

3. **Veja a resposta com:**
   - ✅ Resposta gerada pelo GPT-4o-mini
   - ✅ Fontes (nomes dos PDFs usados)
   - ✅ Reranking automático (melhora precisão em 30-40%)

### Opção B: Via API (cURL)

```bash
curl -X POST https://[SUA_URL_RAILWAY]/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o tratamento para diabetes tipo 2?"
  }'
```

**Resposta esperada:**
```json
{
  "answer": "O tratamento para diabetes tipo 2 inclui...",
  "sources": ["Manejo da terapia antidiabética no DM2.pdf"],
  "reranked": true
}
```

### Opção C: Via Python

```python
import requests

url = "https://[SUA_URL_RAILWAY]/query"
payload = {
    "question": "Qual o tratamento para diabetes?"
}

response = requests.post(url, json=payload)
result = response.json()

print("Resposta:", result["answer"])
print("Fontes:", result["sources"])
```

---

## Passo 5: Integrar com n8n

### 5.1 Criar Workflow no n8n

1. **Abra seu n8n**
2. **Crie novo workflow**
3. **Adicione os seguintes nodes:**

#### Node 1: Webhook (Trigger)
- **Tipo:** Webhook
- **Method:** POST
- **Path:** `/rag-query`
- **Response Mode:** Last Node

#### Node 2: HTTP Request (Query RAG)
- **Tipo:** HTTP Request
- **Method:** POST
- **URL:** `https://[SUA_URL_RAILWAY]/query`
- **Headers:**
  ```
  Content-Type: application/json
  ```
- **Body:**
  ```json
  {
    "question": "{{ $json.body.question }}"
  }
  ```
- **Response Format:** JSON

#### Node 3: Code/Function (Processar Resposta)
```javascript
const response = $input.item.json;

return {
  json: {
    answer: response.answer,
    sources: response.sources,
    reranked: response.reranked,
    timestamp: new Date().toISOString()
  }
};
```

### 5.2 Testar o Webhook n8n

Depois de ativar o workflow, teste:

```bash
curl -X POST https://[SEU_N8N_URL]/webhook/rag-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o tratamento para hipertensão?"
  }'
```

---

## Passo 6: Workflows n8n Avançados

### Workflow 1: Chat com Histórico

```
1. Webhook (recebe pergunta)
2. HTTP Request → Railway RAG (query)
3. Google Sheets (salvar histórico)
4. Respond to Webhook (retornar resposta)
```

### Workflow 2: Upload Automático de PDFs

```
1. Google Drive Trigger (novo PDF na pasta)
2. HTTP Request → Railway Upload (enviar PDF)
3. Wait (aguardar processamento - 10 min)
4. Slack (notificar conclusão)
```

### Workflow 3: Assistente via Telegram

```
1. Telegram Trigger (recebe mensagem)
2. HTTP Request → Railway Query
3. Telegram (enviar resposta)
```

### Workflow 4: RAG + WhatsApp Business

```
1. WhatsApp Business Trigger
2. HTTP Request → Railway Query
3. WhatsApp Business (responder)
```

---

## Passo 7: Monitoramento e Manutenção

### Ver Logs no Railway

1. Acesse Railway dashboard
2. Clique em **"Deployments"**
3. Selecione deployment ativo
4. Veja logs em tempo real

### Métricas Importantes

- **CPU/Memory:** Railway → Metrics
- **Response Time:** Monitore queries
- **Success Rate:** /health endpoint

### Adicionar Mais PDFs

Simplesmente repita o Passo 3! Cada PDF adicionado:
- ✅ É processado automaticamente
- ✅ É adicionado à mesma vector store
- ✅ Fica disponível para queries imediatamente após processamento

---

## Exemplos de Uso Real

### Caso 1: Base de Conhecimento Médico

```bash
# Upload de artigos
curl -X POST https://[SUA_URL]/upload -F "file=@artigo_diabetes.pdf"
curl -X POST https://[SUA_URL]/upload -F "file=@artigo_hipertensao.pdf"
curl -X POST https://[SUA_URL]/upload -F "file=@artigo_cardiologia.pdf"

# Query inteligente
curl -X POST https://[SUA_URL]/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual a relação entre diabetes e hipertensão?"}'

# Resposta usa TODOS os PDFs relevantes!
```

### Caso 2: Documentação Técnica

```bash
# Upload de manuais
curl -X POST https://[SUA_URL]/upload -F "file=@manual_api.pdf"
curl -X POST https://[SUA_URL]/upload -F "file=@guia_instalacao.pdf"

# Query
curl -X POST https://[SUA_URL]/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Como faço a instalação?"}'
```

---

## Troubleshooting

### Erro: "service unavailable"
- Aguarde 30s (cold start)
- Verifique variáveis de ambiente no Railway

### Erro: "API key not set"
- Configure OPENAI_API_KEY, GROQ_API_KEY, COHERE_API_KEY no Railway

### Upload demora muito
- Normal: 5-10 min por PDF
- Use `/upload-stream` para ver progresso

### Query retorna vazio
- Certifique-se que o PDF foi processado completamente
- Tente reformular a pergunta

---

## Checklist Final

- [ ] API Railway respondendo em `/health`
- [ ] UI acessível em `/ui` e `/chat`
- [ ] Pelo menos 1 PDF processado na vector store
- [ ] Query via `/chat` funcionando
- [ ] Query via API (cURL/Python) funcionando
- [ ] Webhook n8n configurado
- [ ] Workflow n8n testado e funcionando

**Quando todos estiverem ✅, seu sistema RAG está 100% operacional!**

---

## Próximos Passos Avançados

1. **Adicionar autenticação** (API_SECRET_KEY)
2. **Implementar cache de queries** (Redis)
3. **Criar dashboard de analytics** (queries mais comuns)
4. **Adicionar mais formatos** (DOCX, PPTX)
5. **Implementar rate limiting**
6. **Configurar domínio customizado** no Railway

---

## Suporte

- **GitHub Issues:** https://github.com/rodrigocfranco/multimodal-rag-langchain/issues
- **Railway Docs:** https://docs.railway.app
- **n8n Docs:** https://docs.n8n.io

**Boa sorte com seu sistema RAG! 🚀**
