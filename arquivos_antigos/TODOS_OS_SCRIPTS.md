# 📚 Guia Completo de Todos os Scripts

## 🎯 Resumo: Qual Script Usar?

| Script | O Que Faz | Quando Usar | Tempo |
|--------|-----------|-------------|-------|
| **processar_e_salvar.py** | Processa PDF e salva vectorstore | UMA VEZ por PDF | 5-10 min |
| **consultar_vectorstore.py** | Chat rápido com vectorstore salvo | SEMPRE (uso diário) | 5 seg ⚡ |
| **listar_vectorstores.py** | Lista todos vectorstores processados | Ver o que tem salvo | 1 seg |
| **inspecionar_pdf.py** | Mostra o que foi extraído do PDF | Validar extração | 2-5 min |
| **chat_terminal.py** | Chat que reprocessa tudo | Testes rápidos | 5-10 min |
| **app_streamlit.py** | Interface web bonita | Apresentações | 5-10 min |
| **test_installation.py** | Testa se tudo está instalado | Verificar setup | 10 seg |

---

## 💾 Scripts de Vector Store Persistente (RECOMENDADOS)

### 1. `processar_e_salvar.py` ⭐
**Propósito:** Processar PDF UMA VEZ e salvar vectorstore

```bash
python processar_e_salvar.py "seu_arquivo.pdf"
```

**Quando usar:**
- ✅ Primeira vez processando um PDF
- ✅ Quer economizar tempo e dinheiro
- ✅ Vai fazer muitas consultas

**Tempo:** 5-10 minutos (UMA VEZ)

**Saída:**
```
💾 PROCESSAR PDF E SALVAR VECTORSTORE
📄 PDF: seu_arquivo.pdf
💾 Vectorstore: ./vectorstores/seu_arquivo

1️⃣  Extraindo dados...
2️⃣  Gerando resumos...
3️⃣  Salvando vectorstore...
✅ VECTORSTORE SALVO COM SUCESSO!

🚀 Próximo passo:
  python consultar_vectorstore.py seu_arquivo
```

---

### 2. `consultar_vectorstore.py` ⭐⭐⭐
**Propósito:** Chat RÁPIDO com vectorstore já salvo

```bash
python consultar_vectorstore.py nome_do_vectorstore
```

**Quando usar:**
- ✅ Depois de processar com `processar_e_salvar.py`
- ✅ Quer fazer perguntas rapidamente
- ✅ Uso diário/frequente

**Tempo:** 5-10 SEGUNDOS para iniciar ⚡

**Exemplo:**
```bash
$ python consultar_vectorstore.py Manejo_da_terapia_antidiabética_no_DM2

💬 CHAT RÁPIDO - CONSULTAR VECTORSTORE
📂 Carregando vectorstore: Manejo_da_terapia_antidiabética_no_DM2
⏳ Carregando (leva apenas alguns segundos)...
✓ Vectorstore carregado!

📊 INFORMAÇÕES DO DOCUMENTO
📄 Arquivo: Manejo da terapia antidiabética no DM2.pdf
📝 Textos: 38
📊 Tabelas: 3
🖼️  Imagens: 12

✅ SISTEMA PRONTO! Carregou em SEGUNDOS!

🤔 Sua pergunta: Quais são as classes de antidiabéticos?
⏳ Buscando resposta...
🤖 Resposta: [resposta instantânea]
```

**Comandos especiais:**
- `info` → Ver estatísticas
- `exemplos` → Ver perguntas sugeridas
- `sair` → Encerrar

---

### 3. `listar_vectorstores.py`
**Propósito:** Ver todos os vectorstores já processados

```bash
python listar_vectorstores.py
```

**Quando usar:**
- ✅ Esqueceu quais PDFs processou
- ✅ Ver estatísticas dos vectorstores
- ✅ Descobrir nome exato para consultar

**Saída:**
```
📂 VECTORSTORES DISPONÍVEIS

1. attention
   ────────────────────────────────────────────────────────────────────
   📄 Arquivo: attention.pdf
   📝 Textos: 12
   📊 Tabelas: 0
   🖼️  Imagens: 6
   ⏰ Processado: 2025-10-11 22:30:15
   💾 Tamanho: 15.32 MB
   
   🚀 Para consultar:
      python consultar_vectorstore.py attention

2. Manejo_da_terapia_antidiabética_no_DM2
   ────────────────────────────────────────────────────────────────────
   📄 Arquivo: Manejo da terapia antidiabética no DM2.pdf
   📝 Textos: 38
   📊 Tabelas: 3
   🖼️  Imagens: 12
   ⏰ Processado: 2025-10-11 23:15:42
   💾 Tamanho: 28.75 MB
   
   🚀 Para consultar:
      python consultar_vectorstore.py Manejo_da_terapia_antidiabética_no_DM2
```

---

## 🔍 Scripts de Teste e Validação

### 4. `inspecionar_pdf.py`
**Propósito:** Ver O QUE foi extraído do PDF (sem IA)

```bash
python inspecionar_pdf.py "seu_arquivo.pdf"
```

**Quando usar:**
- ✅ Primeira vez vendo um PDF
- ✅ Verificar se extração funcionou
- ✅ Antes de processar completamente

**Tempo:** 2-5 minutos

**Vantagens:**
- Rápido (não usa IA)
- Mostra amostra dos dados extraídos
- Bom para validação inicial

---

### 5. `chat_terminal.py`
**Propósito:** Chat que reprocessa tudo (não salva)

```bash
python chat_terminal.py "seu_arquivo.pdf"
```

**Quando usar:**
- ✅ Teste rápido de um PDF
- ✅ Não quer salvar vectorstore
- ✅ Uso único/pontual

**Tempo:** 5-10 minutos TODA VEZ

**Desvantagens:**
- ❌ Reprocessa toda vez
- ❌ Não salva vectorstore
- ❌ Mais lento para uso frequente

---

### 6. `app_streamlit.py`
**Propósito:** Interface web bonita (reprocessa tudo)

```bash
# Primeira vez: instalar Streamlit
pip install streamlit

# Executar
streamlit run app_streamlit.py
```

**Quando usar:**
- ✅ Apresentações
- ✅ Interface visual bonita
- ✅ Selecionar PDFs visualmente

**Tempo:** 5-10 minutos para processar

**Vantagens:**
- Interface gráfica profissional
- Seletor de PDFs
- Chat com histórico
- Bom para demos

**Desvantagens:**
- ❌ Reprocessa toda vez
- ❌ Não persiste vectorstore

---

### 7. `test_installation.py`
**Propósito:** Verificar se instalação está OK

```bash
python test_installation.py
```

**Quando usar:**
- ✅ Após instalar o projeto
- ✅ Problemas com dependências
- ✅ Verificar configuração

**Tempo:** 10 segundos

**O que testa:**
- Bibliotecas instaladas
- Chaves de API configuradas
- Arquivos do projeto
- Dependências do sistema

---

## 🗂️ Scripts Auxiliares

### 8. `multimodal_rag.py`
**Script original** - Reprocessa tudo e testa 3 perguntas

```bash
python multimodal_rag.py
```

**Quando usar:**
- ✅ Ver como o sistema funciona
- ✅ Teste inicial
- ✅ PDF hardcoded (attention.pdf)

---

### 9. `corrigir_nltk_ssl.py`
**Propósito:** Corrigir warnings de SSL do NLTK

```bash
python corrigir_nltk_ssl.py
```

**Quando usar:**
- ⚠️  Warnings de SSL incomodando
- ⚠️  Opcional - não afeta funcionamento

---

## 📊 Comparação: Qual Usar?

### Cenário 1: Uso Profissional Diário
```bash
# Dia 1: Processar (uma vez)
python processar_e_salvar.py "documento.pdf"

# Dia 1-365: Consultar (sempre)
python consultar_vectorstore.py documento
```
**⭐⭐⭐ RECOMENDADO**

---

### Cenário 2: Teste Rápido
```bash
# Ver se PDF está OK
python inspecionar_pdf.py "documento.pdf"

# Se estiver OK, processar e salvar
python processar_e_salvar.py "documento.pdf"
```

---

### Cenário 3: Demo/Apresentação
```bash
# Interface bonita para impressionar
streamlit run app_streamlit.py
```

---

### Cenário 4: Teste Pontual
```bash
# Teste único (não salva)
python chat_terminal.py "documento.pdf"
```

---

## 💡 Fluxo de Trabalho Recomendado

### Para Novo PDF:

```bash
# 1. Verificar extração (2-5 min)
python inspecionar_pdf.py "novo_documento.pdf"

# Saída mostra: ✅ 25 textos, 5 tabelas, 10 imagens

# 2. Processar e salvar (5-10 min)
python processar_e_salvar.py "novo_documento.pdf"

# 3. Consultar para sempre (5 seg)
python consultar_vectorstore.py novo_documento
```

### Para PDF Já Processado:

```bash
# Listar disponíveis
python listar_vectorstores.py

# Consultar diretamente
python consultar_vectorstore.py nome_do_documento
```

---

## 🎯 Decision Tree: Qual Script Usar?

```
Você tem um PDF novo?
│
├─ Sim
│  │
│  ├─ Quer apenas VER o que tem?
│  │  └─> python inspecionar_pdf.py "arquivo.pdf"
│  │
│  ├─ Quer fazer MUITAS consultas depois?
│  │  └─> python processar_e_salvar.py "arquivo.pdf"
│  │      (depois use consultar_vectorstore.py)
│  │
│  └─ Quer apenas TESTAR uma vez?
│     └─> python chat_terminal.py "arquivo.pdf"
│
└─ Não (já processado)
   │
   └─ Fazer consultas rápidas
      └─> python consultar_vectorstore.py nome
```

---

## 📁 Onde os Dados São Salvos?

```
multimodal-rag-langchain/
├── vectorstores/              ← Vectorstores persistentes
│   ├── pdf1/
│   ├── pdf2/
│   └── pdf3/
│
├── content/                   ← PDFs originais
│   ├── pdf1.pdf
│   ├── pdf2.pdf
│   └── pdf3.pdf
│
└── chroma_db/                 ← Usado por scripts antigos (opcional)
```

---

## 💰 Custo por Script

| Script | Custo por Execução | Obs |
|--------|-------------------|-----|
| **processar_e_salvar.py** | $0.10-0.50 | UMA VEZ |
| **consultar_vectorstore.py** | $0.01-0.05 | SEMPRE |
| **inspecionar_pdf.py** | Grátis | Sem IA |
| **chat_terminal.py** | $0.10-0.50 | TODA VEZ |
| **listar_vectorstores.py** | Grátis | Sem IA |

**Economia usando vectorstore persistente:**
- 10 consultas: $1.10 vs $5.00 (78% economia)
- 100 consultas: $5.50 vs $50.00 (89% economia)

---

## 🚀 Quick Start

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

# 1. Processar (uma vez)
python processar_e_salvar.py "Manejo da terapia antidiabética no DM2.pdf"

# 2. Consultar (sempre)
python consultar_vectorstore.py Manejo_da_terapia_antidiabética_no_DM2

# Fazer perguntas infinitas! 🎉
```

---

**Use `processar_e_salvar.py` + `consultar_vectorstore.py` para uso profissional! ⭐⭐⭐**

