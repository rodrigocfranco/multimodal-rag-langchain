# Migração de Volume no Railway - ChromaDB 0.5.x → 1.0.x

## ⚠️ Por que preciso deletar o volume?

O formato interno do banco de dados ChromaDB mudou entre versões:
- **0.5.x**: Formato antigo (JSON sem campo `_type`)
- **1.0.x**: Formato novo (JSON com campo `_type`)

Se você já tinha um deploy com ChromaDB 0.5.x, o banco de dados no volume está no formato antigo e é **incompatível** com 1.0.x.

## 🔍 Como Saber se Preciso Deletar?

### Sintoma 1: Healthcheck Falha
```
Attempt #1 failed with service unavailable
Attempt #2 failed with service unavailable
...
KeyError: '_type'
```

### Sintoma 2: Deploy Anterior Funcionava
Se você tinha um deploy funcionando antes desta atualização, precisa migrar.

### Sintoma 3: Deploy Novo
Se este é seu **primeiro deploy**, NÃO precisa fazer nada! O volume será criado automaticamente com o formato correto.

## 📋 Procedimento de Migração

### Passo 1: Verificar Logs do Deploy Atual

```
Railway Dashboard → Deployments → View Logs

Procure por:
- "KeyError: '_type'" ← Precisa migrar
- "Mounting volume on: /var/lib/..." ← Volume está sendo usado
```

### Passo 2: Deletar Volume

```
1. Railway Dashboard → Seu Serviço
2. Click em "Settings" (engrenagem)
3. Scroll até "Volumes"
4. Você verá:

   📁 knowledge
   Mount path: /app/knowledge
   [⋮] Menu → Delete

5. Click em "Delete"
6. Confirme: "Yes, delete this volume"
```

**⚠️ IMPORTANTE:** Isso **não deleta a configuração** do volume, só os dados!

### Passo 3: Forçar Novo Deploy

```
1. Settings → Deployments
2. Click no último deploy
3. Click em "Redeploy" (ícone de reload)
```

**O que acontece:**
```
✅ Railway detecta que o volume foi deletado
✅ Cria automaticamente novo volume vazio
✅ Monta em /app/knowledge (conforme railway.json)
✅ Python inicia
✅ ChromaDB 1.0.21 cria estrutura nova
✅ Healthcheck passa! 🎉
✅ Deploy marcado como Success
```

### Passo 4: Reprocessar PDFs

Seus PDFs foram deletados junto com o volume. Você precisa fazer upload novamente:

```bash
# Opção 1: Via API
curl -X POST https://seu-app.railway.app/upload \
  -F "pdf=@documento.pdf"

# Opção 2: Via Interface Web
Acesse: https://seu-app.railway.app/ui
```

## 🚫 O Que NÃO Fazer

❌ **NÃO tente criar volume manualmente**
   → Railway cria automaticamente

❌ **NÃO reverta para ChromaDB 0.5.x**
   → Versão antiga, sem suporte, problemas de segurança

❌ **NÃO ignore o erro**
   → Aplicação nunca vai funcionar com banco corrompido

## ✅ Alternativa: Manter Versão Antiga (NÃO Recomendado)

Se você **realmente** não quer perder os dados e pode esperar:

```python
# requirements.txt - REVERTER PARA VERSÃO ANTIGA
chromadb==0.5.23
langchain-chroma==0.1.4
```

**Desvantagens:**
- ❌ Versão desatualizada
- ❌ Sem bugfixes/security patches
- ❌ Vai ter que migrar eventualmente
- ❌ Não recebe melhorias

## 🔄 Verificação Pós-Migração

Após o deploy completar:

### 1. Verificar Healthcheck
```
Deployment Logs:
✅ Starting Healthcheck
✅ Path: /health
✅ Attempt #1 succeeded with status 200
✅ Healthcheck passed!
```

### 2. Testar Endpoint
```bash
curl https://seu-app.railway.app/health

# Resposta esperada:
{
  "status": "ok",
  "reranker": "cohere",
  "persist_dir": "/app/knowledge",
  "ready": true
}
```

### 3. Verificar Volume Vazio
```bash
curl https://seu-app.railway.app/documents

# Resposta esperada:
{
  "documents": []  # Vazio, como esperado
}
```

## 📊 Comparação de Opções

| Opção | Tempo | Dados Preservados | Recomendado |
|-------|-------|-------------------|-------------|
| **Deletar volume** | 5 min | ❌ Não | ✅ Sim |
| **Reverter versão** | 2 min | ✅ Sim | ❌ Não |
| **Exportar + Migrar** | 1-2 horas | ✅ Sim | ⚠️ Se crítico |

## 🆘 Problemas Comuns

### "Não vejo opção de deletar volume"

**Solução:** Click no menu de 3 pontos (⋮) ao lado do volume

### "Volume não foi recriado"

**Solução:**
1. Verifique railway.json tem volumeMounts
2. Force redeploy novamente
3. Check logs: "Mounting volume on..."

### "Healthcheck ainda falha após deletar"

**Solução:**
1. Verifique se usou a versão correta (chromadb>=1.0.21)
2. Check logs para outros erros
3. Verifique variáveis de ambiente (OPENAI_API_KEY, etc)

## 📞 Suporte

Se tiver problemas:
1. Verifique logs completos no Railway
2. Procure por erros diferentes de KeyError '_type'
3. Abra issue no GitHub com logs completos

---

**Última atualização:** 2025-10-29
**ChromaDB:** 0.5.23 → 1.0.21
**LangChain-Chroma:** 0.1.4 → 1.0.0
