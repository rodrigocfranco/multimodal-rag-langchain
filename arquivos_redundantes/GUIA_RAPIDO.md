# 🚀 Guia Rápido - Sistema RAG Multimodal

## 3 Comandos Para Começar

```bash
# 1. Ativar ambiente
cd /Users/rcfranco/multimodal-rag-langchain && source venv/bin/activate

# 2. Processar PDF (UMA VEZ)
python processar_e_salvar.py "Manejo da terapia antidiabética no DM2.pdf"

# 3. Consultar (SEMPRE)
python consultar_vectorstore.py Manejo_da_terapia_antidiabética_no_DM2
```

---

## 📋 Scripts Essenciais

### 1️⃣ `processar_e_salvar.py`
**Processar PDF e salvar vectorstore**
```bash
python processar_e_salvar.py "arquivo.pdf"
```
- ⏱️ Tempo: 5-10 minutos
- 💾 Resultado: Vectorstore salvo em `vectorstores/`
- 🔁 Frequência: UMA VEZ por PDF

### 2️⃣ `consultar_vectorstore.py`
**Chat rápido com vectorstore**
```bash
python consultar_vectorstore.py nome_vectorstore
```
- ⏱️ Tempo: 5 segundos
- 💬 Resultado: Chat interativo
- 🔁 Frequência: QUANTAS VEZES QUISER

### 3️⃣ `listar_vectorstores.py`
**Ver PDFs processados**
```bash
python listar_vectorstores.py
```
- ⏱️ Tempo: 1 segundo
- 📊 Resultado: Lista com estatísticas

### 4️⃣ `diagnosticar_extracao.py`
**Validar extração do PDF**
```bash
python diagnosticar_extracao.py "arquivo.pdf"
```
- ⏱️ Tempo: 2-5 minutos
- 🔍 Resultado: Estatísticas detalhadas

---

## 💡 Comandos do Chat

Durante consulta com `consultar_vectorstore.py`:

- `info` → Ver estatísticas
- `exemplos` → Ver perguntas sugeridas  
- `sair` → Encerrar

---

## ✅ Verificação Rápida

```bash
# Testar se está tudo OK
python test_installation.py

# Ver vectorstores disponíveis
python listar_vectorstores.py
```

---

## 🐛 Problemas Comuns

**PDF não encontrado:**
```bash
ls -lh content/  # Ver PDFs disponíveis
```

**Vectorstore não encontrado:**
```bash
python listar_vectorstores.py  # Ver processados
```

**Rate limit:**
```bash
# Aguarde 30 segundos e tente novamente
```

---

## 📊 O Que Foi Corrigido

✅ **Tabelas**: Detecta tabelas embutidas em CompositeElements  
✅ **Imagens**: Valida tamanho antes de processar (sem erro 400)  
✅ **Performance**: Vector store persistente (5 seg vs 10 min)

---

## 📚 Documentação Completa

- `README.md` → Documentação completa
- `VECTOR_STORE_PERSISTENTE.md` → Detalhes do vector store
- `arquivos_antigos/` → Scripts alternativos (referência)

---

**🎉 Sistema pronto para uso profissional!**

