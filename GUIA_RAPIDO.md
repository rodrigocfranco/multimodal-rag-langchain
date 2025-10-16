# Guia Rápido - Como Usar o Sistema

## 🚀 Início Rápido

### 1️⃣ Iniciar a API

```bash
# No terminal, execute:
python consultar_com_rerank.py --api
```

**Aguarde ver:**
```
============================================================
🌐 API COM RERANKER rodando em http://localhost:5001
============================================================

🔥 Reranker: Cohere (melhora precisão em 30-40%)

Endpoints:
  GET  /ui      → Upload UI
  GET  /chat    → Chat UI
  GET  /manage  → Gerenciamento
  POST /query   → Fazer pergunta (com rerank)

💡 Teste no navegador: http://localhost:5001/ui
============================================================
```

---

### 2️⃣ Fazer Upload de PDFs

**Opção A: Via Interface Web (Mais Fácil)**

1. Abra no navegador: **http://localhost:5001/ui**

2. Click em "Escolher arquivo"

3. Selecione seu PDF médico

4. Click em **"Enviar com Progresso (Tempo Real)"**

5. Aguarde 5-10 minutos vendo o progresso:
   ```
   Iniciando processamento...
   📄 Processando: Artigo de Revisão.pdf
   🔍 Gerando ID do documento...
      PDF_ID: a3f8b2c1...
      Tamanho: 5.2 MB
      Tipo detectado: review_article  ← NOVO!

   1️⃣  Extraído: 250 chunks
      ✓ 200 textos, 10 tabelas, 3 imagens

   2️⃣  Gerando resumos...
      Textos: 1/200...
      Textos: 50/200...
      Textos: 100/200...
      ✓ 200 textos
      ✓ 10 tabelas
      ✓ 3 imagens

   3️⃣  Adicionando ao knowledge base...
      ✓ Adicionado!

   ✅ PDF processado com sucesso!
   ```

6. Veja mensagem de sucesso

**Opção B: Via Terminal (Mais Detalhado)**

```bash
# Em outro terminal (deixe a API rodando)
python adicionar_pdf.py "/Users/rcfranco/Desktop/Documentos processados/Artigo de Revisão - NEJM.pdf"
```

---

### 3️⃣ Fazer Perguntas (Chat)

**Depois de processar PDFs:**

1. Abra no navegador: **http://localhost:5001/chat**

2. Digite sua pergunta:
   - "Quais os principais achados deste estudo?"
   - "Como foi feito o diagnóstico?"
   - "Quais são os efeitos colaterais?"
   - "Qual o tratamento recomendado?"

3. Veja a resposta com:
   - ✅ Resposta baseada nos PDFs
   - ✅ Fontes citadas
   - ✅ Reranking ativado (30-40% mais preciso)

**Interface do Chat:**
```
┌─────────────────────────────────────────────┐
│  Chat com a Base de Conhecimento           │
│                                             │
│  [Digite sua pergunta...]  [Enviar]        │
│                                             │
│  Q: Quais os principais achados?           │
│                                             │
│  A: Os principais achados incluem...       │
│     (baseado em context com reranking)     │
│                                             │
│     Fontes: artigo1.pdf, artigo2.pdf       │
└─────────────────────────────────────────────┘
```

---

### 4️⃣ Gerenciar Documentos

**Ver todos PDFs processados:**

1. Abra: **http://localhost:5001/manage**

2. Veja dashboard com:
   - Total de documentos
   - Total de chunks
   - Tamanho total
   - Estatísticas (textos, tabelas, imagens)

3. Para cada documento:
   - 👁️ Ver detalhes (tipo, seções, chunks)
   - 🗑️ Deletar (remove todos chunks)

**Interface de Gerenciamento:**
```
┌────────────────────────────────────────────────────┐
│  📚 Gerenciamento de Documentos                    │
│                                                    │
│  [Total: 5 docs] [Chunks: 1250] [Size: 25 MB]     │
│                                                    │
│  Documentos Processados:                [🔄 Atualizar]
│                                                    │
│  Nome                  | ID      | Tipo    | Ações │
│  ─────────────────────────────────────────────────│
│  Artigo Revisão NEJM  | a3f8... | review  | 👁️ 🗑️ │
│  Guideline HTN 2024   | b2c4... | guide   | 👁️ 🗑️ │
│  Case Report Rare     | c5d6... | case    | 👁️ 🗑️ │
└────────────────────────────────────────────────────┘
```

---

## 📁 Onde Estão Seus PDFs?

Você mencionou: `/Users/rcfranco/Desktop/Documentos processados/`

**PDFs disponíveis:**
- Artigo de Revisão - NEJM - Gamopatia Monoclonal de Significado Indeterminado.pdf
- Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf
- Artigo de Revisão - Nature Review Disease Primers - Nefrite Lúpica.pdf
- Artigo de Revisão - Nature Review Diseases - Cardiomiopatia Hipertrófica.pdf
- Manejo da terapia antidiabética no DM2.pdf

---

## 🧪 Testar o Sistema

### Processar 1 PDF (Teste)

```bash
# 1. Iniciar API (se não estiver rodando)
python consultar_com_rerank.py --api

# 2. Em outro terminal, processar PDF
python adicionar_pdf.py "/Users/rcfranco/Desktop/Documentos processados/Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf"

# 3. Aguardar processamento (5-10 min)

# 4. Testar no chat
# Abrir: http://localhost:5001/chat
# Perguntar: "Quais os principais achados sobre síndrome de lise tumoral?"
```

### Testar Performance

```bash
# Depois de processar 1+ PDFs
python test_performance.py

# Vai mostrar:
# - Latency média/min/max
# - Resultados rerankeados
# - Fontes utilizadas
# - Classificação de performance
# - Recomendações
```

---

## 🎯 Fluxo Completo Recomendado

### **DIA 1: Setup e Teste**

```bash
# Terminal 1: Iniciar API
python consultar_com_rerank.py --api

# Browser: Upload 1 PDF
# http://localhost:5001/ui
# → Upload: "Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf"
# → Aguardar processamento

# Browser: Testar Chat
# http://localhost:5001/chat
# → Perguntar sobre o PDF
# → Validar respostas

# Browser: Ver Gerenciamento
# http://localhost:5001/manage
# → Ver documento processado
# → Ver estatísticas
```

### **DIA 2: Processar Todos PDFs**

```bash
# Opção A: Um por um via UI
# http://localhost:5001/ui
# → Upload cada PDF
# → Aguardar processamento

# Opção B: Batch via terminal
python adicionar_pdf.py "/Users/rcfranco/Desktop/Documentos processados/Artigo de Revisão - NEJM - Gamopatia Monoclonal.pdf"
python adicionar_pdf.py "/Users/rcfranco/Desktop/Documentos processados/Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf"
# ... etc
```

### **DIA 3: Usar em Produção**

```bash
# Fazer perguntas médicas
# http://localhost:5001/chat

# Testar performance
python test_performance.py

# Ajustar queries conforme necessário
```

---

## ⚡ Comandos Úteis

### Iniciar Sistema
```bash
# API completa (upload + chat + gerenciamento)
python consultar_com_rerank.py --api

# Apenas terminal (sem API)
python consultar_com_rerank.py
```

### Processar PDFs
```bash
# Via terminal
python adicionar_pdf.py "/caminho/para/arquivo.pdf"

# Via UI
# http://localhost:5001/ui
```

### Testar
```bash
# Performance
python test_performance.py

# Metadata médico
python test_medical_metadata.py
```

### Gerenciar
```bash
# Ver documentos
# http://localhost:5001/manage

# Ou via Python
python document_manager.py
```

---

## 📊 Verificar Status

```bash
# Quantos documentos processados?
python -c "
import os, pickle
if os.path.exists('./knowledge_base/metadata.pkl'):
    with open('./knowledge_base/metadata.pkl', 'rb') as f:
        m = pickle.load(f)
    print(f'Documentos: {len(m.get(\"documents\", {}))}')
    total_chunks = sum(d.get('stats',{}).get('total_chunks',0) for d in m.get('documents',{}).values())
    print(f'Chunks: {total_chunks}')
else:
    print('Knowledge base vazio')
"
```

---

## 🆘 Troubleshooting

### Problema: API não inicia
```bash
# Verificar se porta 5001 está livre
lsof -i :5001

# Se estiver ocupada, matar processo
kill -9 <PID>

# Ou usar outra porta
PORT=8080 python consultar_com_rerank.py --api
```

### Problema: PDF não processa
```bash
# Verificar logs detalhados
python adicionar_pdf.py "arquivo.pdf" 2>&1 | tee log.txt

# Verificar tamanho do arquivo
ls -lh "arquivo.pdf"

# Verificar se é PDF válido
file "arquivo.pdf"
```

### Problema: Queries lentas
```bash
# Verificar performance
python test_performance.py

# Se latency > 3s, considerar:
# 1. Reduzir k (de 20 para 15)
# 2. Verificar número de chunks
# 3. Considerar migração (Fase 3)
```

---

## ✅ Checklist de Validação

### Antes de Usar
- [ ] API keys configuradas (.env)
- [ ] Dependências instaladas (requirements.txt)
- [ ] API iniciada (python consultar_com_rerank.py --api)

### Processar PDFs
- [ ] PDF médico selecionado
- [ ] Upload via UI ou terminal
- [ ] Processamento concluído (5-10 min)
- [ ] Verificado em /manage

### Testar Queries
- [ ] Aberto /chat
- [ ] Pergunta feita
- [ ] Resposta recebida
- [ ] Fontes verificadas

### Performance
- [ ] test_performance.py executado
- [ ] Latency < 3s
- [ ] Precisão validada

---

## 🎓 Próximos Passos

1. ✅ **Processar 1 PDF de teste** (Síndrome de Lise Tumoral)
2. ✅ **Validar no chat** (fazer 3-5 perguntas)
3. ✅ **Processar demais PDFs** (batch ou um por um)
4. ✅ **Testar performance** (python test_performance.py)
5. ✅ **Usar em produção** (queries reais)

---

**Pronto para começar!** 🚀

Qual você prefere fazer primeiro?
- A) Processar 1 PDF via UI (mais fácil)
- B) Processar 1 PDF via terminal (mais detalhado)
- C) Processar todos PDFs de uma vez
