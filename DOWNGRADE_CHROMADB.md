# ⚠️ DOWNGRADE ChromaDB 1.3→0.5: Procedimento Obrigatório

## Problema

ChromaDB 1.3.0 e 0.5.x usam **formatos incompatíveis**:
- **1.3.0**: HNSW em Rust (formato binário novo)
- **0.5.x**: HNSW em Python (formato antigo)

Se fizer redeploy sem limpar, o app **VAI FALHAR** ao tentar ler o índice 1.3.0 com código 0.5.x!

---

## Procedimento Correto (OBRIGATÓRIO)

### Passo 1: Fazer Redeploy no Railway

```bash
git push  # Railway detecta mudanças e faz redeploy automático
```

### Passo 2: Aguardar Deploy Completar (~2-3 min)

Verifique se está rodando:
```bash
curl https://seu-app.railway.app/health
```

Deve retornar:
```json
{"status": "ok", "ready": true}
```

### Passo 3: **RESETAR ChromaDB** (CRÍTICO!)

```bash
curl -X POST https://seu-app.railway.app/reset-chromadb \
  -H "Content-Type: application/json" \
  -d '{"confirm": "RESET"}'
```

**O que isso faz:**
- ❌ Deleta `chroma.sqlite3` (índice 1.3.0 incompatível)
- ❌ Deleta diretórios de HNSW UUID
- ❌ Limpa `docstore.pkl` (embeddings)
- ✅ **PRESERVA** `metadata.pkl` (lista de PDFs)
- ✅ Recria ChromaDB vazio (formato 0.5.x)

### Passo 4: Reprocessar PDF

Após reset, você terá que fazer upload do PDF novamente:

**Via UI:**
```
1. Acesse https://seu-app.railway.app
2. Faça upload do PDF
3. Aguarde processamento (30-60 segundos)
```

**Via API:**
```bash
curl -X POST https://seu-app.railway.app/upload \
  -F "file=@seu_pdf.pdf"
```

### Passo 5: Validar Query

Teste se está funcionando:
```bash
curl -X POST https://seu-app.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "diabetes"}'
```

**Resultado esperado:**
```json
{
  "answer": "...",
  "context": {
    "texts": [...],  // ✅ Deve ter textos (não vazio!)
    "images": [...]
  },
  "num_images": 2
}
```

---

## ❌ O que acontece se NÃO resetar?

### Erro esperado:
```
Error: Incompatible ChromaDB version
Unable to read index from disk
HNSW segment format mismatch
```

### Sintomas:
- ✅ App inicia normalmente
- ✅ `/health` retorna OK
- ❌ Queries falham com erro de formato
- ❌ `/admin` pode mostrar dados "fantasma"

---

## ✅ Checklist Completo

- [ ] 1. Git push feito (requirements.txt + consultar_com_rerank.py)
- [ ] 2. Railway redeploy completou
- [ ] 3. `/health` retorna OK
- [ ] 4. `/reset-chromadb` executado com sucesso
- [ ] 5. PDF reprocessado
- [ ] 6. Query testada e funciona (textos + imagens)
- [ ] 7. `/admin` mostra documento correto

---

## Perguntas Frequentes

### Q: Vou perder meus documentos?
**R:** Não! O `metadata.pkl` é preservado. Você só precisa reprocessar os PDFs (fazer upload novamente).

### Q: Preciso fazer upload de TODOS os PDFs de novo?
**R:** Sim, mas é rápido (30-60 seg por PDF). ChromaDB precisa reindexar com formato 0.5.x.

### Q: Posso pular o reset?
**R:** NÃO! App vai falhar com erro de formato incompatível.

### Q: E se eu tiver 100+ PDFs?
**R:** Considere:
1. Fazer script de upload em batch
2. Ou manter ChromaDB 1.3.0 + busca manual temporariamente
3. Ou migrar direto para FAISS (melhor opção longo prazo)

---

## Migração Futura: FAISS

Para escala (100+ PDFs), recomendamos migrar para FAISS em 1-2 meses:
- Performance 5-10x melhor
- Suporta milhões de docs
- Zero bugs de corrompimento
- GPU support opcional

Ver: `docs/FAISS_MIGRATION.md` (TODO)
