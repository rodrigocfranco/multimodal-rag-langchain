# 🧪 Guia de Testes Interativos - RAG Multimodal

## 3 Formas de Testar Seu Sistema

Criei 3 ferramentas para você testar e validar a extração do PDF:

---

## 🔍 Ferramenta 1: Inspetor de PDF (Mais Rápido)

**Propósito**: Ver O QUE foi extraído do PDF **sem processar** com IA

### Como Usar:

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

# Inspecionar o PDF
python inspecionar_pdf.py "Manejo da terapia antidiabética no DM2.pdf"
```

### O Que Mostra:
- ✅ Número de chunks, textos, tabelas e imagens extraídos
- ✅ Amostra dos primeiros 3 textos
- ✅ Primeira tabela encontrada
- ✅ Informações sobre imagens
- ✅ Metadados disponíveis

### Tempo: **2-5 minutos** ⏱️

### Exemplo de Saída:
```
📊 ESTATÍSTICAS DO DOCUMENTO
✅ Total de chunks extraídos: 45
📝 Chunks de texto: 38
📊 Tabelas: 3
🖼️  Imagens: 12

📝 AMOSTRA DE TEXTOS (primeiros 3)
┌─ Texto 1 ─────────────────────
│ Tipo: CompositeElement
│ Página: 1
│ Tamanho: 1250 caracteres
│
│ Conteúdo: 
│ Manejo da terapia antidiabética...
```

---

## 💬 Ferramenta 2: Chat no Terminal (Interativo)

**Propósito**: Fazer perguntas e receber respostas **no terminal**

### Como Usar:

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

# Iniciar chat
python chat_terminal.py "Manejo da terapia antidiabética no DM2.pdf"
```

### Funcionalidades:
- ✅ Chat interativo com perguntas ilimitadas
- ✅ Mostra fontes consultadas (textos + imagens)
- ✅ Comandos especiais: `info`, `exemplos`, `sair`
- ✅ Contador de perguntas

### Tempo: **5-10 minutos** (setup) + tempo de chat

### Exemplo de Uso:
```
💬 CHAT INTERATIVO - RAG MULTIMODAL
================================================================================

📄 Processando PDF: Manejo da terapia antidiabética no DM2.pdf
⏳ Aguarde... (isso pode levar 5-10 minutos)

[... processamento ...]

✅ SISTEMA PRONTO! Você pode fazer perguntas agora.
================================================================================

💡 Dicas:
  • Digite sua pergunta e pressione Enter
  • Digite 'sair' ou 'exit' para encerrar
  • Digite 'info' para ver estatísticas do documento
  • Digite 'exemplos' para ver perguntas sugeridas

────────────────────────────────────────────────────────────────────────────────

🤔 Sua pergunta: Qual é o tema principal deste documento?

⏳ Processando...

🤖 Resposta:
────────────────────────────────────────────────────────────────────────────────
O documento trata sobre o manejo da terapia antidiabética no diabetes mellitus 
tipo 2, abordando as diferentes classes de medicamentos, suas indicações e 
critérios de escolha conforme o perfil do paciente...
────────────────────────────────────────────────────────────────────────────────

📚 Fontes: 4 textos, 1 imagens

────────────────────────────────────────────────────────────────────────────────

🤔 Sua pergunta: info

📊 Estatísticas do documento:
  • Arquivo: Manejo da terapia antidiabética no DM2.pdf
  • Chunks de texto: 38
  • Tabelas: 3
  • Imagens: 12
  • Perguntas feitas: 1

────────────────────────────────────────────────────────────────────────────────

🤔 Sua pergunta: sair

👋 Encerrando chat. Até logo!
```

### Comandos Especiais:
- `info` → Ver estatísticas do documento
- `exemplos` → Ver sugestões de perguntas
- `sair` / `exit` / `q` → Sair do chat

---

## 🌐 Ferramenta 3: Interface Web com Streamlit (Mais Bonita)

**Propósito**: Interface gráfica **profissional** no navegador

### Instalação (primeira vez):

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

# Instalar Streamlit
pip install streamlit
```

### Como Usar:

```bash
# Iniciar servidor web
streamlit run app_streamlit.py
```

O navegador vai abrir automaticamente em `http://localhost:8501`

### Funcionalidades:
- ✅ Interface gráfica linda e profissional
- ✅ Seletor de PDFs (todos os PDFs em content/)
- ✅ Botão para processar PDF
- ✅ Chat com histórico de mensagens
- ✅ Mostra estatísticas do documento
- ✅ Fontes consultadas expandíveis
- ✅ Exemplos de perguntas na sidebar

### Tempo: **5-10 minutos** (setup) + tempo de chat

### Visual da Interface:

```
┌─────────────────────────────────────────────────────────────────┐
│ 📄 Chat com PDFs - RAG Multimodal                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ⚙️ Configurações        │  💬 Chat                             │
│                          │                                       │
│ Selecione um PDF:        │  📊 Informações do Documento         │
│ [v] Manejo da terapia... │  ┌────┬────┬────┬────┐              │
│                          │  │PDF │Tex │Tab │Img │              │
│ 🔄 Processar PDF         │  │38  │3   │12  │    │              │
│                          │  └────┴────┴────┴────┘              │
│ ─────────────────        │                                       │
│                          │  🤔 Usuário:                         │
│ 💡 Como usar             │  Qual é o tema principal?            │
│ 1. Selecione um PDF      │                                       │
│ 2. Clique em Processar   │  🤖 Assistente:                      │
│ 3. Aguarde               │  O documento trata sobre...          │
│ 4. Faça suas perguntas   │  📚 Fontes: 4 textos, 1 imagens     │
│                          │                                       │
│ 📊 Exemplos de Perguntas │  [Digite sua pergunta aqui...     ] │
│ • What is the main topic?│                                       │
│ • Summarize the document │                                       │
│ • What are key findings? │                                       │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## 📋 Comparação das Ferramentas

| Ferramenta | Velocidade | Interface | Melhor Para |
|------------|------------|-----------|-------------|
| **Inspetor PDF** | ⭐⭐⭐⭐⭐ | Terminal | Verificar extração rápida |
| **Chat Terminal** | ⭐⭐⭐⭐ | Terminal | Testes rápidos, debugging |
| **Streamlit Web** | ⭐⭐⭐ | Navegador | Apresentações, uso contínuo |

---

## 🎯 Fluxo de Trabalho Recomendado

### 1️⃣ Primeiro: Inspecionar o PDF
```bash
python inspecionar_pdf.py seu_arquivo.pdf
```
**Por quê?** Confirma que o PDF foi extraído corretamente antes de processar com IA.

### 2️⃣ Segundo: Testar no Terminal
```bash
python chat_terminal.py seu_arquivo.pdf
```
**Por quê?** Rápido para testar algumas perguntas e ver se as respostas fazem sentido.

### 3️⃣ Terceiro: Usar Interface Web
```bash
streamlit run app_streamlit.py
```
**Por quê?** Melhor experiência para uso prolongado e apresentações.

---

## 💡 Dicas de Testes

### Como Validar a Extração:

1. **Verificar Números**
   - Textos extraídos fazem sentido para o tamanho do PDF?
   - Tabelas foram detectadas?
   - Imagens foram encontradas?

2. **Perguntas de Validação**
   ```
   • What is the main topic? (deve identificar o tema)
   • Who are the authors? (se houver autores)
   • Summarize the introduction (teste de compreensão)
   • What are the key findings? (teste de análise)
   ```

3. **Verificar Fontes**
   - O sistema está consultando múltiplas fontes?
   - Textos e imagens estão sendo usados?

### Perguntas por Idioma:

**Português:**
```
• Qual é o tema principal deste documento?
• Resuma os pontos principais
• Quais são as conclusões?
• Explique a metodologia utilizada
```

**Inglês:**
```
• What is the main topic of this document?
• Summarize the key points
• What are the conclusions?
• Explain the methodology used
```

---

## 🐛 Solução de Problemas

### Problema: Inspetor demora muito
**Solução**: É normal! PDFs grandes (>50 páginas) podem demorar 5-10 minutos.

### Problema: Chat Terminal - Rate Limit Error
**Solução**: Aguarde 30 segundos entre perguntas ou aumente `time.sleep()` no código.

### Problema: Streamlit não abre
**Solução**: 
```bash
# Verificar se instalou
pip list | grep streamlit

# Reinstalar se necessário
pip install streamlit

# Testar manualmente
streamlit hello
```

### Problema: PDF não encontrado
**Solução**: 
```bash
# Verificar se o PDF está em content/
ls -lh content/

# Usar nome exato (com espaços entre aspas)
python chat_terminal.py "nome com espaços.pdf"
```

---

## 📊 Exemplo Completo de Teste

### Testar PDF sobre Diabetes:

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

# 1. Inspecionar primeiro (2-5 min)
python inspecionar_pdf.py "Manejo da terapia antidiabética no DM2.pdf"

# Saída esperada:
# ✅ 38 chunks de texto
# ✅ 3 tabelas
# ✅ 12 imagens

# 2. Iniciar chat (5-10 min setup)
python chat_terminal.py "Manejo da terapia antidiabética no DM2.pdf"

# Fazer perguntas:
🤔 Sua pergunta: Quais são as classes de antidiabéticos mencionados?
🤔 Sua pergunta: Qual é a recomendação para metformina?
🤔 Sua pergunta: info
🤔 Sua pergunta: sair

# 3. Interface web (opcional)
pip install streamlit  # se ainda não instalou
streamlit run app_streamlit.py

# Selecionar PDF na sidebar
# Clicar em "Processar PDF"
# Fazer perguntas no chat
```

---

## 🚀 Próximos Passos

Após validar que tudo funciona:

1. **Teste com seus PDFs**: Copie PDFs para `content/` e teste
2. **Ajuste parâmetros**: Veja `COMO_USAR_OUTROS_PDFS.md`
3. **Personalize perguntas**: Crie perguntas específicas para seu domínio
4. **Salve o vectorstore**: Adicione persistência para não reprocessar

---

## ❓ FAQ

**Q: Qual ferramenta usar para testes rápidos?**  
R: Use o **Inspetor PDF** primeiro, depois **Chat Terminal**.

**Q: Qual é a melhor para demonstrações?**  
R: **Streamlit** - interface profissional no navegador.

**Q: Posso usar em português?**  
R: Sim! Todas as ferramentas funcionam em qualquer idioma.

**Q: Quanto custa por pergunta?**  
R: ~$0.01 a $0.05 dependendo do tamanho do contexto.

**Q: Posso fazer perguntas ilimitadas?**  
R: Sim! Mas respeite os rate limits das APIs.

---

## 🎓 Recursos Adicionais

- **Documentação completa**: `README.md`
- **Processar múltiplos PDFs**: `COMO_USAR_OUTROS_PDFS.md`
- **Testes de instalação**: `python test_installation.py`

---

**Comece agora testando com o Inspetor de PDF! 🚀**

```bash
python inspecionar_pdf.py "Manejo da terapia antidiabética no DM2.pdf"
```

