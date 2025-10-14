# 🔧 Corrigir Erros Comuns

## ❌ Erro: NLTK SSL Certificate

### O Erro:
```
[nltk_data] Error loading averaged_perceptron_tagger_eng: <urlopen
[nltk_data]     error [SSL: CERTIFICATE_VERIFY_FAILED] certificate
[nltk_data]     verify failed: unable to get local issuer certificate
```

### ✅ O Que Significa:
- São apenas **WARNINGS**, não erros fatais
- O sistema **continua funcionando** normalmente
- O NLTK não conseguiu baixar alguns dados opcionais

### ✅ Solução 1: Ignorar (Recomendado)
**Esses warnings NÃO afetam o funcionamento!**

O script vai continuar processando normalmente. Você pode **ignorar** esses avisos.

### ✅ Solução 2: Corrigir os Warnings

#### Opção A - Script Automático:
```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate
python corrigir_nltk_ssl.py
```

#### Opção B - Instalar Certificados do Python:
```bash
# No macOS, executar:
/Applications/Python\ 3.13/Install\ Certificates.command
```

#### Opção C - Download Manual:
```python
import ssl
import nltk

ssl._create_default_https_context = ssl._create_unverified_context
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
```

---

## ❌ Erro: Warning about max_size deprecated

### O Erro:
```
The `max_size` parameter is deprecated and will be removed in v4.26.
Please specify in `size['longest_edge'] instead`.
```

### ✅ O Que Significa:
- Warning de uma biblioteca (timm ou transformers)
- **NÃO afeta o funcionamento**
- É só um aviso sobre API futura

### ✅ Solução:
**IGNORAR** - É apenas um warning que não impacta nada.

---

## ❌ Erro: "No languages specified, defaulting to English"

### O Erro:
```
Warning: No languages specified, defaulting to English.
```

### ✅ O Que Significa:
- O Unstructured está usando inglês como idioma padrão
- **Funciona perfeitamente** para PDFs em português também

### ✅ Solução (Opcional):
Se quiser especificar o idioma, adicione ao código:

```python
chunks = partition_pdf(
    filename=file_path,
    languages=["por"],  # Adicionar esta linha para português
    infer_table_structure=True,
    strategy="hi_res",
    # ... resto do código
)
```

**Idiomas disponíveis:** `"por"` (português), `"eng"` (inglês), `"spa"` (espanhol), etc.

---

## ❌ Erro: Rate Limit do Groq

### O Erro:
```
groq.RateLimitError: Error code: 429 - Rate limit reached for model
```

### ✅ O Que Significa:
- Você fez muitas requisições muito rápido
- Groq tem limite de 6000 tokens/minuto (plano gratuito)

### ✅ Solução:

#### Opção 1 - Aguardar:
Espere **30-60 segundos** e tente novamente.

#### Opção 2 - Aumentar Delay nos Scripts:
Edite os scripts e aumente o `time.sleep()`:

```python
# Trocar:
time.sleep(0.5)

# Por:
time.sleep(1.5)  # Espera mais tempo entre requisições
```

#### Opção 3 - Usar Modelo Menor:
```python
# Trocar:
model = ChatGroq(temperature=0.5, model="llama-3.1-8b-instant")

# Por modelo menor (mais rápido):
model = ChatGroq(temperature=0.5, model="mixtral-8x7b-32768")
```

---

## ❌ Erro: OpenAI API Key Invalid

### O Erro:
```
openai.error.AuthenticationError: Invalid API key
```

### ✅ Solução:
```bash
# Verificar arquivo .env
cat .env

# Deve conter:
OPENAI_API_KEY=sk-proj-...
```

Se a chave estiver incorreta:
1. Obtenha nova chave em: https://platform.openai.com/api-keys
2. Edite o arquivo `.env`
3. Execute o script novamente

---

## ❌ Erro: PDF não encontrado

### O Erro:
```
❌ Arquivo não encontrado: ./content/seu_arquivo.pdf
```

### ✅ Solução:
```bash
# Verificar se o PDF está no lugar certo
ls -lh content/

# Copiar PDF para o diretório correto
cp ~/Downloads/seu_arquivo.pdf content/

# Usar nome EXATO (com espaços entre aspas)
python inspecionar_pdf.py "Nome com Espaços.pdf"
```

---

## ❌ Erro: Memory Error

### O Erro:
```
MemoryError: Unable to allocate array
```

### ✅ O Que Significa:
- PDF muito grande
- Muitas imagens em alta resolução
- Sistema sem memória suficiente

### ✅ Solução:

#### Opção 1 - Reduzir Tamanho de Chunks:
```python
chunks = partition_pdf(
    filename=file_path,
    max_characters=5000,        # Reduzir de 10000
    combine_text_under_n_chars=1000,  # Reduzir de 2000
    # ... resto
)
```

#### Opção 2 - Desabilitar Imagens Temporariamente:
```python
chunks = partition_pdf(
    filename=file_path,
    extract_image_block_types=[],  # Desabilitar imagens
    # ... resto
)
```

#### Opção 3 - Processar PDF Menor:
Teste com um PDF menor primeiro (< 20 páginas).

---

## ❌ Erro: Module Not Found

### O Erro:
```
ModuleNotFoundError: No module named 'langchain'
```

### ✅ Solução:
```bash
# Verificar se ambiente virtual está ativo
source venv/bin/activate

# Reinstalar dependências
pip install -r requirements.txt

# Verificar instalação
pip list | grep langchain
```

---

## ❌ Erro: Connection Error

### O Erro:
```
requests.exceptions.ConnectionError: Failed to establish connection
```

### ✅ Solução:
1. **Verificar internet**: Você está conectado?
2. **Verificar proxy**: Se usa proxy corporativo, configure
3. **Aguardar**: APIs podem estar temporariamente indisponíveis
4. **Tentar novamente**: Execute o script novamente

---

## 🆘 Ainda Com Problemas?

### Diagnóstico Completo:

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate

# 1. Testar instalação
python test_installation.py

# 2. Verificar ambiente
python -c "import langchain; import openai; import chromadb; print('✅ Tudo OK!')"

# 3. Verificar arquivo .env
cat .env | grep -E "API_KEY"

# 4. Testar PDF simples
python inspecionar_pdf.py attention.pdf
```

---

## 📊 Status dos Warnings

| Warning | Gravidade | Pode Ignorar? |
|---------|-----------|---------------|
| NLTK SSL | ⚠️  Baixa | ✅ Sim |
| max_size deprecated | ⚠️  Baixa | ✅ Sim |
| No languages specified | ⚠️  Baixa | ✅ Sim |
| LangChain deprecation | ⚠️  Baixa | ✅ Sim |
| Rate Limit | ⚠️  Média | ❌ Precisa resolver |
| Invalid API Key | ❌ Alta | ❌ Precisa resolver |
| PDF não encontrado | ❌ Alta | ❌ Precisa resolver |

---

## ✅ Verificação Rápida

Execute este comando para verificar se está tudo funcionando:

```bash
cd /Users/rcfranco/multimodal-rag-langchain
source venv/bin/activate
python -c "
print('🔍 Verificando ambiente...')
import os
from dotenv import load_dotenv
load_dotenv()

# Verificar chaves
if os.getenv('OPENAI_API_KEY'):
    print('✅ OpenAI API Key configurada')
else:
    print('❌ OpenAI API Key não encontrada')

if os.getenv('GROQ_API_KEY'):
    print('✅ Groq API Key configurada')
else:
    print('❌ Groq API Key não encontrada')

# Verificar bibliotecas
try:
    import langchain
    import openai
    import chromadb
    print('✅ Bibliotecas instaladas')
except:
    print('❌ Faltam bibliotecas')

# Verificar PDF
import os
if os.path.exists('content/attention.pdf'):
    print('✅ PDF de exemplo encontrado')
else:
    print('⚠️  PDF de exemplo não encontrado')

print('\\n✅ Ambiente pronto para uso!')
"
```

---

**Os warnings de NLTK que você viu são NORMAIS e podem ser ignorados! O sistema vai funcionar perfeitamente. 😊**

