# Guia Rápido - Deploy no Railway

Este guia mostra como fazer deploy do seu sistema RAG Multimodal no Railway em menos de 5 minutos.

## Pré-requisitos

Antes de começar, você precisa ter:

1. **Conta no GitHub** (gratuito): https://github.com
2. **Conta no Railway** (gratuito): https://railway.app
3. **3 API Keys** (2 gratuitas, 1 paga):
   - OpenAI: https://platform.openai.com/api-keys (pago, mas barato)
   - Groq: https://console.groq.com/keys (GRATUITO!)
   - Cohere: https://dashboard.cohere.com/api-keys (GRATUITO!)

## Passo a Passo

### 1. Fork do Repositório

1. Acesse: https://github.com/seu-usuario/multimodal-rag-langchain
2. Clique em **"Fork"** (canto superior direito)
3. Aguarde alguns segundos até criar o fork na sua conta

### 2. Criar Projeto no Railway

1. Acesse: https://railway.app
2. Faça login (pode usar GitHub)
3. Clique em **"New Project"**
4. Selecione **"Deploy from GitHub repo"**
5. Escolha o repositório que você fez fork: `seu-usuario/multimodal-rag-langchain`
6. Railway começará o build automaticamente

### 3. Configurar Variáveis de Ambiente

No Railway dashboard:

1. Clique na aba **"Variables"**
2. Clique em **"Add Variable"** e adicione:

```
OPENAI_API_KEY=sk-proj-sua_chave_aqui
GROQ_API_KEY=gsk_sua_chave_aqui
COHERE_API_KEY=sua_chave_aqui
```

3. Clique em **"Add"** para cada variável
4. Railway fará redeploy automático

### 4. Aguardar Deploy

- O build leva **5-8 minutos** na primeira vez
- Acompanhe os logs em **"Deployments"**
- Quando finalizar, verá status **"Success"**

### 5. Acessar sua API

1. Na aba **"Settings"**, veja o **"Public URL"**
2. Copie o URL (ex: `https://seu-app.railway.app`)
3. Teste o health check:

```bash
curl https://seu-app.railway.app/health
```

Resposta esperada:
```json
{"status": "ok", "reranker": "cohere"}
```

## Usar a API

### Interface Web

Acesse no navegador:

```
https://seu-app.railway.app/ui       # Upload de PDFs
https://seu-app.railway.app/chat     # Chat interativo
```

### Via cURL

#### Fazer Upload de PDF

```bash
curl -X POST https://seu-app.railway.app/upload \
  -F "file=@meu_arquivo.pdf"
```

#### Fazer Pergunta

```bash
curl -X POST https://seu-app.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Sua pergunta aqui"}'
```

### Via Python

```python
import requests

# Fazer pergunta
response = requests.post(
    "https://seu-app.railway.app/query",
    json={"question": "Qual o tratamento para diabetes?"}
)

print(response.json()["answer"])
print("Fontes:", response.json()["sources"])
```

### Integração n8n

1. Adicione node **HTTP Request**
2. Configure:
   - Method: `POST`
   - URL: `https://seu-app.railway.app/query`
   - Body Type: `JSON`
   - Body: `{"question": "{{ $json.pergunta }}"}`
3. Parse a resposta em `{{ $json.answer }}`

## Monitoramento

### Ver Logs

No Railway dashboard:
1. Clique em **"Deployments"**
2. Selecione o deployment ativo
3. Veja logs em tempo real

### Métricas

Em **"Metrics"**:
- CPU usage
- Memory usage
- Network traffic

### Health Check

O Railway monitora automaticamente via `/health`. Se a API cair, Railway reinicia automaticamente.

## Custos

### Railway (hospedagem)

- **Free Tier**: $5 crédito/mês (suficiente para testes)
- **Hobby**: $5/mês (uso moderado)
- **Pro**: $20/mês (uso intenso)

### APIs

- **OpenAI**: ~$0.06/PDF + ~$0.001/query
- **Groq**: GRATUITO (limite generoso)
- **Cohere**: GRATUITO (1000 reqs/mês)

**Custo total estimado para 100 PDFs + 1000 queries/mês**: ~$7/mês

## Troubleshooting

### Build falha

Verifique:
1. Dockerfile está presente no repositório
2. requirements.txt está correto
3. Logs de build no Railway

### API não responde

Verifique:
1. Deploy está **"Success"**
2. Variáveis de ambiente configuradas
3. Health check retorna 200
4. Logs para erros

### Erro "API Key not set"

Certifique-se que configurou as 3 variáveis:
- `OPENAI_API_KEY`
- `GROQ_API_KEY`
- `COHERE_API_KEY`

### Erro 503/504

Primeira chamada pode demorar (cold start). Aguarde 30s e tente novamente.

## Próximos Passos

1. **Faça upload de PDFs** via `/ui`
2. **Teste perguntas** via `/chat`
3. **Integre com n8n/Make** usando `/query`
4. **Configure domínio customizado** em Railway Settings

## Recursos Úteis

- **Railway Docs**: https://docs.railway.app
- **LangChain Docs**: https://python.langchain.com
- **OpenAI Pricing**: https://openai.com/pricing
- **Groq Console**: https://console.groq.com
- **Cohere Dashboard**: https://dashboard.cohere.com

## Suporte

Problemas? Abra uma issue:
https://github.com/seu-usuario/multimodal-rag-langchain/issues

---

**Deploy completo em 5 minutos! 🚀**
