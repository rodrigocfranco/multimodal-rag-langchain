# 🚀 Guia de Início Rápido

## Passo a Passo para Usar o Projeto

### 1️⃣ Ativar o Ambiente Virtual

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate
```

Você verá `(venv)` no início do prompt, indicando que o ambiente está ativo.

### 2️⃣ Verificar Instalação

Verifique se tudo está instalado corretamente:

```bash
python -c "import langchain; import chromadb; import unstructured; print('✓ Tudo OK!')"
```

### 3️⃣ Executar o Sistema RAG

```bash
python multimodal_rag.py
```

**O que o script faz:**
1. Carrega o PDF `content/attention.pdf`
2. Extrai texto, tabelas e imagens
3. Gera resumos usando IA
4. Cria um banco de dados vetorial
5. Executa 3 perguntas de teste

**Tempo estimado:** 3-5 minutos (dependendo da conexão e do PDF)

### 4️⃣ Saída Esperada

Você verá algo assim:

```
✓ Ambiente configurado com sucesso!
================================================================================

1. EXTRAINDO DADOS DO PDF...
✓ 15 chunks extraídos do PDF
✓ Tipos de elementos encontrados: 2

2. SEPARANDO ELEMENTOS...
✓ 12 chunks de texto encontrados
✓ 2 tabelas encontradas
✓ 8 imagens encontradas

3. GERANDO RESUMOS...
  • Resumindo textos...
  ✓ 12 resumos de texto criados
  • Resumindo tabelas...
  ✓ 2 resumos de tabelas criados
  • Resumindo imagens...
  ✓ 8 resumos de imagens criados

4. CRIANDO VECTORSTORE...
  • Adicionando textos...
  ✓ 12 textos adicionados
  • Adicionando tabelas...
  ✓ 2 tabelas adicionadas
  • Adicionando imagens...
  ✓ 8 imagens adicionadas

5. CONFIGURANDO PIPELINE RAG...
✓ Pipeline RAG configurado!

================================================================================
6. TESTANDO O SISTEMA RAG
================================================================================

📝 Pergunta 1: What is the attention mechanism?
--------------------------------------------------------------------------------
Resposta: The attention mechanism is a component that allows...
```

## 🔧 Comandos Úteis

### Listar arquivos do projeto
```bash
ls -la
```

### Ver conteúdo do diretório content/
```bash
ls -lh content/
```

### Verificar versões instaladas
```bash
pip list | grep -E "langchain|chromadb|unstructured|openai"
```

### Desativar ambiente virtual
```bash
deactivate
```

### Reativar ambiente virtual
```bash
source venv/bin/activate
```

## 🐛 Problemas Comuns

### Erro: "ModuleNotFoundError"
**Solução:** Certifique-se de que o ambiente virtual está ativo:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Erro: "attention.pdf not found"
**Solução:** Baixe o PDF:
```bash
curl -L -o content/attention.pdf https://arxiv.org/pdf/1706.03762.pdf
```

### Erro: "OPENAI_API_KEY not configured"
**Solução:** Verifique o arquivo `.env`:
```bash
cat .env
# Certifique-se de que as chaves de API estão corretas
```

### Erro: "poppler not found" ou "tesseract not found"
**Solução:** Instale as dependências do sistema:
```bash
brew install poppler tesseract libmagic
```

## 📝 Personalizar Perguntas

Edite o final do arquivo `multimodal_rag.py` para fazer suas próprias perguntas:

```python
# Sua pergunta customizada
response = chain.invoke("Qual é a sua pergunta aqui?")
print("Resposta:", response)
```

## 🎯 Processar Seu Próprio PDF

1. Coloque seu PDF no diretório `content/`:
```bash
cp /caminho/para/seu/arquivo.pdf content/
```

2. Edite `multimodal_rag.py` e altere o nome do arquivo:
```python
file_path = output_path + 'seu_arquivo.pdf'  # Linha ~30
```

3. Execute o script:
```bash
python multimodal_rag.py
```

## 🌟 Próximos Passos

- ✅ Experimentar com diferentes PDFs
- ✅ Ajustar parâmetros de extração
- ✅ Testar diferentes modelos de IA
- ✅ Criar uma interface web com Streamlit
- ✅ Adicionar chat interativo

## 📚 Documentação Completa

Consulte o [README.md](README.md) para documentação completa.

---

**Dúvidas?** Consulte a seção de Solução de Problemas no README.md

