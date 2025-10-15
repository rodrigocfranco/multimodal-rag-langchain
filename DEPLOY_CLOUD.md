# ☁️ Deploy do RAG Multimodal na Cloud

## 🎯 O Que Precisamos Hospedar

1. **API Flask** (consultar_com_rerank.py)
2. **ChromaDB** (vector store persistente)
3. **Arquivos** (PDFs processados)
4. **Python** + dependências

---

## 🏆 MELHORES OPÇÕES PARA DEPLOY

### ⭐ 1. RAILWAY (RECOMENDADO para começar)

**✅ Vantagens:**
- Deploy MUITO fácil (conecta GitHub)
- Suporta Python + ChromaDB
- Volume persistente (para vectorstore)
- $5/mês (plan Hobby)
- SSL/HTTPS automático
- Logs em tempo real

**❌ Desvantagens:**
- Recursos limitados no plano gratuito
- Cold starts (se ficar sem uso)

**💰 Custo:**
- Grátis: 500h + $5 crédito
- Hobby: $5/mês
- Pro: $20/mês

**📦 Como Deploy:**
```bash
# 1. Criar Procfile
echo "web: python consultar_com_rerank.py --api" > Procfile

# 2. Criar runtime.txt
echo "python-3.11" > runtime.txt

# 3. Push para GitHub
git push

# 4. Conectar no Railway
railway.app → New Project → Deploy from GitHub
```

---

### 🚀 2. RENDER (Alternativa Simples)

**✅ Vantagens:**
- Free tier generoso
- Deploy automático (GitHub)
- SSL grátis
- Volume persistente
- Sem cold starts (plano pago)

**❌ Desvantagens:**
- Free tier tem cold starts (30s)
- Menos recursos que Railway

**💰 Custo:**
- Free: Sim, mas com cold starts
- Starter: $7/mês
- Standard: $25/mês

**📦 Como Deploy:**
```yaml
# render.yaml
services:
  - type: web
    name: rag-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python consultar_com_rerank.py --api
    disk:
      name: vectorstore
      mountPath: /opt/render/project/src/knowledge_base
      sizeGB: 1
```

---

### 💪 3. GOOGLE CLOUD RUN (Escalável)

**✅ Vantagens:**
- Escala automaticamente (0 → N)
- Paga por uso (barato para pouco tráfego)
- Poderoso (até 8GB RAM)
- Container Docker (flexível)

**❌ Desvantagens:**
- Mais complexo (Docker)
- Stateless (precisa Cloud Storage)

**💰 Custo:**
- Free: 2M requisições/mês
- Depois: ~$0.10 por 1M requisições

**📦 Como Deploy:**
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "consultar_com_rerank.py", "--api"]
```

---

### 🐳 4. DIGITAL OCEAN APP PLATFORM

**✅ Vantagens:**
- Simples como Railway/Render
- Volume persistente (managed)
- Melhor custo/benefício
- Sem cold starts

**❌ Desvantagens:**
- Sem free tier
- Menos features que GCP/AWS

**💰 Custo:**
- Basic: $5/mês (512MB RAM)
- Professional: $12/mês (1GB RAM)

---

### ⚙️ 5. FLY.IO (Performático)

**✅ Vantagens:**
- Deploy rápido
- Volumes persistentes
- Edge computing (baixa latência)
- Free tier generoso

**❌ Desvantagens:**
- Requer Docker
- Configuração mais técnica

**💰 Custo:**
- Free: 3 VMs pequenas
- Depois: ~$1.94/mês por VM

---

## 📊 COMPARAÇÃO DETALHADA

| Plataforma | Facilidade | Custo/mês | Vector Store | Cold Start | SSL | Recomendado? |
|------------|-----------|-----------|--------------|------------|-----|--------------|
| **Railway** | ⭐⭐⭐⭐⭐ | $5-20 | ✅ Volume | ❌ Não | ✅ Auto | 🏆 **SIM** |
| **Render** | ⭐⭐⭐⭐⭐ | $7-25 | ✅ Volume | ⚠️ Free sim | ✅ Auto | ✅ Sim |
| **Cloud Run** | ⭐⭐⭐ | $0-10 | ⚠️ Storage | ❌ Não | ✅ Auto | ✅ Escala |
| **DigitalOcean** | ⭐⭐⭐⭐ | $5-12 | ✅ Volume | ❌ Não | ✅ Auto | ✅ Sim |
| **Fly.io** | ⭐⭐⭐ | $0-10 | ✅ Volume | ❌ Não | ✅ Auto | ✅ Técnico |

---

## 🎯 MINHA RECOMENDAÇÃO: RAILWAY

### Por quê Railway?

1. ✅ **Mais Fácil:** Deploy em 5 minutos
2. ✅ **Completo:** Suporta tudo que precisamos
3. ✅ **Barato:** $5/mês é suficiente
4. ✅ **Volume Persistente:** ChromaDB funciona perfeitamente
5. ✅ **Logs:** Debug fácil
6. ✅ **Variáveis de Ambiente:** API keys seguras

---

## 📋 DEPLOY NO RAILWAY (PASSO A PASSO)

### PASSO 1: Preparar Projeto

```bash
cd /Users/rcfranco/multimodal-rag-langchain

# Criar Procfile (Railway precisa disso)
echo "web: python consultar_com_rerank.py --api" > Procfile

# Criar runtime.txt (especificar Python)
echo "python-3.11" > runtime.txt

# Atualizar requirements.txt (garantir que está completo)
# Já está pronto!

# Criar .gitignore (se ainda não tem)
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
knowledge_base/
.env
.DS_Store
EOF
```

### PASSO 2: Subir para GitHub

```bash
# Inicializar Git (se ainda não fez)
git init
git add .
git commit -m "Deploy RAG to Railway"

# Criar repositório no GitHub
# Depois:
git remote add origin https://github.com/SEU-USER/multimodal-rag.git
git push -u origin main
```

### PASSO 3: Deploy no Railway

1. Acesse: https://railway.app
2. Clique em **"New Project"**
3. Selecione **"Deploy from GitHub repo"**
4. Escolha o repositório
5. Railway detecta Python automaticamente! ✅

### PASSO 4: Configurar Variáveis de Ambiente

No Railway Dashboard:
- **Variables** → Add Variable

```
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
COHERE_API_KEY=jnq...
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
PORT=5001
```

### PASSO 5: Adicionar Volume (Vector Store)

1. **Settings** → **Volumes**
2. Clique em **"+ New Volume"**
3. Configure:
   - **Mount Path:** `/app/knowledge_base`
   - **Size:** 1GB (expandir depois se precisar)

### PASSO 6: Deploy!

Railway faz deploy automaticamente! 🚀

Você receberá uma URL:
```
https://seu-projeto.railway.app
```

### PASSO 7: Testar

```bash
# Health check
curl https://seu-projeto.railway.app/health

# Fazer pergunta
curl -X POST https://seu-projeto.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "teste"}'
```

---

## 🔄 PROCESSAR PDFs NA CLOUD

### Opção 1: Processar Localmente, Fazer Upload

```bash
# 1. Processar PDFs localmente
python adicionar_pdf.py "arquivo.pdf"

# 2. Fazer backup do knowledge_base
tar -czf knowledge_base.tar.gz knowledge_base/

# 3. Upload via Railway CLI
railway volume mount knowledge_base
# Copiar arquivos para o volume
```

### Opção 2: API de Upload (Adicionar Endpoint)

```python
# adicionar ao consultar_com_rerank.py
@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    # Salvar e processar PDF
    # ... código de processamento
    
    return jsonify({"status": "processed"})
```

---

## 💰 CUSTOS ESTIMADOS

### Railway (Recomendado)

**Plano Hobby ($5/mês):**
- 512MB RAM (suficiente para API)
- 1GB Disco (vector store)
- Execução contínua

**Se crescer (Plano Pro $20/mês):**
- 8GB RAM
- 100GB Disco
- Priority support

### Custo APIs (adicional):

- **OpenAI:** ~$0.02 por query
- **Groq:** GRÁTIS (sumários)
- **Cohere:** ~$0.002 por query

**Total estimado para 100 queries/dia:**
- Railway: $5-20/mês
- APIs: ~$30/mês
- **Total: $35-50/mês**

---

## 🔒 SEGURANÇA

### 1. Adicionar Autenticação

```python
# No início da API
API_KEY = os.getenv("API_SECRET_KEY")

@app.before_request
def check_api_key():
    if request.endpoint != 'home':
        key = request.headers.get('X-API-Key')
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
```

### 2. Rate Limiting

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.headers.get('X-API-Key'))

@app.route('/query', methods=['POST'])
@limiter.limit("10 per minute")
def query():
    # ...
```

---

## 🎯 ARQUITETURA FINAL NA CLOUD

```
┌─────────────────────────────────────────────┐
│           RAILWAY / RENDER / FLY.IO         │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │   API Flask (consultar_com_rerank) │    │
│  │   - Porta 5001                     │    │
│  │   - Gunicorn (produção)            │    │
│  └──────────┬─────────────────────────┘    │
│             │                               │
│  ┌──────────▼─────────────┐                │
│  │   ChromaDB              │                │
│  │   (Vector Store)        │                │
│  │   Volume Persistente    │                │
│  └─────────────────────────┘                │
│                                             │
└─────────────────────────────────────────────┘
              │
              │ HTTPS
              │
┌─────────────▼─────────────┐
│         n8n Cloud          │
│    (seus workflows)        │
└────────────────────────────┘
```

---

## ✅ CHECKLIST DE DEPLOY

- [ ] Código no GitHub
- [ ] Procfile criado
- [ ] runtime.txt criado
- [ ] requirements.txt atualizado
- [ ] .gitignore configurado
- [ ] Conta Railway/Render criada
- [ ] Deploy feito
- [ ] Variáveis de ambiente configuradas
- [ ] Volume criado
- [ ] PDFs processados
- [ ] URL testada
- [ ] n8n configurado com nova URL

---

## 🆘 PROBLEMAS COMUNS

### 1. "Out of Memory"
**Solução:** Upgrade para mais RAM ($12-20/mês)

### 2. "Vector Store Vazio"
**Solução:** Reprocessar PDFs ou fazer backup/restore

### 3. "Timeout"
**Solução:** Desativar reranker ou upgrade plano

### 4. "Cold Start Lento"
**Solução:** Upgrade para plano pago (sem cold starts)

---

## 🎉 CONCLUSÃO

**Para você, recomendo: RAILWAY**

- ✅ Deploy em 10 minutos
- ✅ $5/mês (muito barato)
- ✅ Tudo funciona out-of-the-box
- ✅ Fácil de escalar depois

**Alternativa:** Render (se quiser free tier com cold starts)

---

**Quer que eu crie os arquivos de configuração para Railway?** 🚀

