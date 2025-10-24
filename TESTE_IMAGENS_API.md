# 🧪 GUIA DE TESTE: Imagens na API

## ✅ Implementação Concluída!

As seguintes mudanças foram implementadas em `consultar_com_rerank.py`:

1. ✅ `parse_docs()` - Retorna imagens como `{base64, metadata}`
2. ✅ `build_prompt()` - Extrai base64 do dict
3. ✅ Endpoint `/query` - Adiciona campos `images`, `has_images`, `num_images`

---

## 🎯 Como Testar no /chat (Railway)

### Passo 1: Aguardar Deploy

1. Acessar: https://railway.app/project/comfortable-tenderness-production
2. Aguardar build completar (~2-3 min)
3. Status deve ficar: ✅ **Deployed**

### Passo 2: Testar no /chat

**URL:** https://comfortable-tenderness-production.up.railway.app/chat

#### Queries de Teste (com imagens):

**Teste 1 - Figura específica:**
```
Explique a figura 1 do documento de hiperglicemia no paciente internado não crítico
```

**Resultado esperado:**
- ✅ Resposta descreve a figura
- ✅ Fonte: "Manejo de hiperglicemia hospitalar..."
- ✅ Console do navegador (F12): JSON tem campo `images`

**Teste 2 - Fluxograma:**
```
Descreva o fluxograma 1 de hiperglicemia hospitalar
```

**Teste 3 - Múltiplas imagens:**
```
Quais figuras há no documento de diabetes e risco cardiovascular?
```

**Teste 4 - Sem imagens (controle):**
```
Quais critérios de muito alto risco cardiovascular?
```

**Resultado esperado:**
- ✅ Resposta normal
- ✅ `has_images: false`
- ✅ `images: []`

---

## 🔍 Verificar Resposta JSON (Console do Navegador)

### Como ver o JSON completo:

1. Abrir `/chat`
2. Apertar **F12** (Developer Tools)
3. Ir na aba **Network**
4. Fazer pergunta sobre imagem
5. Clicar na requisição `query` (última da lista)
6. Ir na aba **Response**

### O que verificar:

```json
{
  "answer": "FIGURA 1 é um fluxograma...",
  "sources": ["Manejo de hiperglicemia hospitalar..."],
  "chunks_used": 8,
  "reranked": true,
  "total_docs_indexed": 5,
  "cache_hit": true,
  "has_images": true,  // ✅ DEVE SER TRUE
  "images": [          // ✅ DEVE TER ARRAY
    {
      "base64": "/9j/4AAQSkZJRgABAQEAYABgAAD...",  // ✅ String longa
      "metadata": {
        "source": "Manejo de hiperglicemia hospitalar no doente não crítico.pdf",
        "type": "image",
        "index": 0,
        "summary": "FLUXOGRAMA 1: Monitorização da glicemia..."  // ✅ Descrição
      }
    }
  ],
  "num_images": 1  // ✅ Quantidade
}
```

---

## 🧪 Teste via cURL (Avançado)

### Teste básico (ver JSON):

```bash
curl -X POST "https://comfortable-tenderness-production.up.railway.app/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Explique a figura 1 do documento de hiperglicemia"}' \
  | python3 -m json.tool > response.json

# Ver resultado
cat response.json
```

### Ver quantas imagens vieram:

```bash
cat response.json | jq '.num_images'
cat response.json | jq '.has_images'
```

### Ver metadata da primeira imagem:

```bash
cat response.json | jq '.images[0].metadata'
```

### Extrair primeira imagem (salvar como JPEG):

```bash
cat response.json | jq -r '.images[0].base64' | base64 -d > image1.jpg

# Abrir
open image1.jpg  # macOS
# ou
xdg-open image1.jpg  # Linux
```

---

## ✅ Checklist de Validação

### Teste 1: Query com imagem
- [ ] Campo `has_images` é `true`
- [ ] Campo `num_images` é >= 1
- [ ] Array `images` não está vazio
- [ ] Cada imagem tem `base64` (string longa)
- [ ] Cada imagem tem `metadata.source` (nome do PDF)
- [ ] Cada imagem tem `metadata.summary` (descrição)
- [ ] Resposta menciona a figura/imagem

### Teste 2: Query sem imagem
- [ ] Campo `has_images` é `false`
- [ ] Campo `num_images` é `0`
- [ ] Array `images` está vazio `[]`
- [ ] Resposta funciona normalmente

### Teste 3: Validar base64
- [ ] Consegue extrair base64 do JSON
- [ ] Consegue decodificar (`base64 -d`)
- [ ] Imagem abre corretamente (é JPEG válido)
- [ ] Imagem mostra fluxograma/diagrama/figura correto

### Teste 4: Tamanho do JSON
- [ ] JSON com 1 imagem: ~200-500 KB
- [ ] JSON com 2 imagens: ~400 KB - 1 MB
- [ ] JSON com 3 imagens: ~600 KB - 1.5 MB
- [ ] Não ultrapassa 5 MB (se ultrapassar, algo errado!)

---

## 🐛 Troubleshooting

### Erro: "images is not defined"

**Causa:** Deploy não completou ou código antigo ainda em cache

**Solução:**
1. Aguardar mais 1-2 min
2. Force refresh (Ctrl+Shift+R ou Cmd+Shift+R)
3. Limpar cache do navegador

---

### Campo "images" está vazio mesmo com query sobre imagem

**Possíveis causas:**

1. **Cohere Rerank descartou as imagens**
   - Verificar logs: `🖼️ Query sobre imagens detectada`
   - Se NÃO aparecer, problema na detecção de pattern

2. **Imagens não foram extraídas do PDF**
   - Verificar: `/debug-volume`
   - Procurar: `"images": X` onde X > 0

3. **Query não menciona figura/imagem/fluxograma**
   - Usar keywords: "figura", "fluxograma", "diagrama", "imagem"

**Debug:**
```bash
# Ver se há imagens no vectorstore
curl "https://comfortable-tenderness-production.up.railway.app/debug-volume" | jq '.chroma_count'
```

---

### Base64 não decodifica (erro ao salvar JPEG)

**Causa:** Base64 corrompido ou incompleto

**Solução:**
```bash
# Verificar tamanho
cat response.json | jq '.images[0].base64' | wc -c

# Deve ser > 10000 chars (~50KB+ de imagem)
# Se for muito pequeno (<1000), algo errado
```

---

### JSON muito grande (>10 MB)

**Causa:** Muitas imagens ou imagens muito grandes

**Verificar:**
```bash
ls -lh response.json
cat response.json | jq '.num_images'
```

**Solução:**
- Normal: 1-3 imagens (~600 KB - 1.5 MB)
- Se >5 imagens, verificar código (deveria limitar a 3)
- Se cada imagem >2 MB, verificar filtro MIN_IMAGE_SIZE_KB

---

## 📊 Métricas Esperadas

| Métrica | Valor Esperado |
|---------|----------------|
| **Tempo de resposta** | 3-6s (com imagens) |
| **Tamanho JSON (1 img)** | 200-500 KB |
| **Tamanho JSON (3 imgs)** | 600 KB - 1.5 MB |
| **Imagens retornadas** | 1-3 (max) |
| **Taxa de sucesso** | >90% para queries com keywords |

---

## 🎉 Próximos Passos (Depois de Validar)

1. ✅ **Validar tudo funcionando no /chat**
2. 📝 **Documentar formato para n8n**
3. 🔄 **Criar workflow n8n teste**
4. 🎨 **Integrar imagens no HTML da questão**
5. 🚀 **Usar em produção!**

---

## 📞 Comandos Úteis

### Ver logs Railway:
```bash
railway logs --project comfortable-tenderness-production
```

### Testar endpoint health:
```bash
curl "https://comfortable-tenderness-production.up.railway.app/health"
```

### Ver documentos indexados:
```bash
curl "https://comfortable-tenderness-production.up.railway.app/documents" | jq
```

### Limpar cache (se necessário):
```bash
curl -X POST "https://comfortable-tenderness-production.up.railway.app/clear-cache"
```

---

**Criado em:** 2025-10-22
**Status:** ✅ Pronto para teste
**Próximo passo:** Validar no /chat após deploy completar
