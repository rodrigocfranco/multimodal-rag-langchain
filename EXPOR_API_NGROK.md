# 🌐 Expor API para n8n Cloud com ngrok

## O Problema

- n8n Cloud não acessa `localhost:5000`
- Precisa de URL pública: `https://xyz.ngrok.io`

---

## ✅ SOLUÇÃO: Usar ngrok

### PASSO 1: Instalar ngrok

```bash
# macOS
brew install ngrok

# Ou baixar em: https://ngrok.com/download
```

### PASSO 2: Criar conta (Grátis)

1. Acesse: https://dashboard.ngrok.com/signup
2. Copie seu authtoken

### PASSO 3: Configurar authtoken

```bash
ngrok authtoken SEU_TOKEN_AQUI
```

### PASSO 4: Iniciar API (Terminal 1)

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate
python consultar_com_rerank.py --api
```

**Deixe rodando!**

### PASSO 5: Expor com ngrok (Terminal 2)

```bash
ngrok http 5000
```

**Você verá:**
```
Session Status                online
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:5000
```

**Copie a URL `https://abc123.ngrok-free.app`** ✅

---

## 🎯 Usar no n8n Cloud

### HTTP Request Node:

**Antes (não funciona):**
```
URL: http://localhost:5000/query
```

**Depois (funciona!):**
```
URL: https://abc123.ngrok-free.app/query
Method: POST
Body: {"question": "={{ $json.question }}"}
```

---

## 🧪 Testar

```bash
curl https://abc123.ngrok-free.app/health

curl -X POST https://abc123.ngrok-free.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "teste"}'
```

---

## ⚠️ Importante

1. **Terminal 1:** API rodando
2. **Terminal 2:** ngrok rodando
3. **Ambos precisam estar abertos!**

**URL ngrok muda a cada reinício** (plano grátis)

---

## 💰 Plano Grátis vs Pago

| Recurso | Grátis | Pago |
|---------|--------|------|
| URL muda | ✅ Sim | ❌ Não (fixo) |
| Limite req/min | 40 | 120+ |
| HTTPS | ✅ | ✅ |

Para uso contínuo, considere plano pago ou self-host.

---

## 🔒 Segurança

**ngrok grátis expõe sua API publicamente!**

Adicione autenticação:

```python
# No início do consultar_com_rerank.py
API_KEY = os.getenv("API_KEY", "sua-chave-secreta")

@app.route('/query', methods=['POST'])
def query():
    # Verificar API key
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    # ... resto do código
```

No n8n, adicione header:
```
X-API-Key: sua-chave-secreta
```

---

## 📊 Status da Configuração

✅ **Funcionando quando ver:**

**Terminal 1:**
```
🌐 API COM RERANKER rodando em http://localhost:5000
```

**Terminal 2:**
```
Forwarding     https://abc123.ngrok-free.app -> http://localhost:5000
```

**n8n:**
```
Status 200 OK
Response: {"answer": "...", "sources": [...]}
```

---

## 🎉 Pronto!

Sua API local agora está acessível pelo n8n Cloud!

