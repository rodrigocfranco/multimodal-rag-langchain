# 🎯 Qual Sistema Usar? Guia Definitivo

## 📊 Você Agora Tem 3 Sistemas Diferentes

Após todo o desenvolvimento, temos **3 abordagens** diferentes. Veja qual usar:

---

## 1️⃣ **Sistema Separado (1 PDF = 1 Vectorstore)**

### Scripts:
- `processar_e_salvar.py`
- `consultar_vectorstore.py`

### Como Funciona:
```
PDF 1 → vectorstore_pdf1/
PDF 2 → vectorstore_pdf2/
PDF 3 → vectorstore_pdf3/

Consulta: Precisa escolher qual PDF consultar
```

### Quando Usar:
- ✅ PDFs **muito diferentes** (medicina vs programação vs finanças)
- ✅ Quer **isolar** conhecimentos
- ✅ **Controle granular** sobre cada documento
- ✅ Testar um PDF específico

### Exemplo:
```bash
# Processar
python processar_e_salvar.py "diabetes.pdf"
python processar_e_salvar.py "programacao.pdf"

# Consultar diabetes
python consultar_vectorstore.py diabetes

🤔 Pergunta sobre diabetes
```

---

## 2️⃣ **Knowledge Base Unificado (Todos os PDFs juntos)** ⭐

### Scripts:
- `adicionar_pdf_ao_vectorstore.py`
- `consultar_knowledge_base.py`

### Como Funciona:
```
PDF 1 ─┐
PDF 2 ─┤─→ unified_knowledge_base/
PDF 3 ─┘

Consulta: Busca AUTOMÁTICA em todos os PDFs
```

### Quando Usar:
- ✅ PDFs **relacionados** ao mesmo tópico
- ✅ **Base de conhecimento** (empresa/pesquisa)
- ✅ Quer **busca global** automática
- ✅ **Comparar** informações entre documentos
- ✅ **Não sabe** onde está a informação
- ⭐ **RECOMENDADO para maioria dos casos**

### Exemplo:
```bash
# Adicionar PDFs
python adicionar_pdf_ao_vectorstore.py "artigo1.pdf"
python adicionar_pdf_ao_vectorstore.py "artigo2.pdf"
python adicionar_pdf_ao_vectorstore.py "artigo3.pdf"

# Consultar (busca em TODOS)
python consultar_knowledge_base.py

🤔 [Qualquer pergunta]
🤖 [Busca automaticamente]
📄 [Mostra de qual PDF veio]
```

---

## 3️⃣ **Sistema com Metadados Avançados**

### Scripts:
- `processar_com_metadata_avancado.py`
- `consultar_com_filtros.py`

### Como Funciona:
```
PDF → vectorstore com metadados ricos (12+ campos)

Consulta: Pode filtrar por tipo, página, etc
```

### Quando Usar:
- ✅ PDFs **grandes** (>50 páginas)
- ✅ Precisa de **filtros** (só tabelas, só página X)
- ✅ **Análises avançadas**
- ✅ **Debugging** (ver exatamente de onde veio)
- ✅ Uso **profissional/acadêmico**

### Exemplo:
```bash
# Processar com metadados
python processar_com_metadata_avancado.py "tese.pdf"

# Consultar com filtros
python consultar_com_filtros.py tese_metadata

🤔 filtrar:tabela
Digite pergunta: Quais são os resultados?

🤔 filtrar:pagina:50
Digite pergunta: O que tem nesta página?
```

---

## 📊 Comparação Completa

| Aspecto | Separado | Unificado | Metadados Avançados |
|---------|----------|-----------|---------------------|
| **PDFs por vectorstore** | 1 | Múltiplos | 1 |
| **Busca** | Manual | Automática | Automática + Filtros |
| **Cross-document** | ❌ | ✅ | ❌ |
| **Rastreabilidade** | Média | Alta | Muito Alta |
| **Filtros** | ❌ | ❌ | ✅ |
| **Metadados** | Básicos | Médios | Avançados (12+) |
| **Escalabilidade** | Baixa | Alta | Média |
| **Complexidade** | Baixa | Baixa | Média |

---

## 🎯 Decision Tree: Qual Usar?

```
Você tem múltiplos PDFs relacionados ao mesmo tópico?
│
├─ SIM
│  │
│  ├─ Quer busca global automática?
│  │  ├─ SIM → KNOWLEDGE BASE UNIFICADO ⭐
│  │  └─ NÃO → Sistema Separado
│  │
│  └─ Precisa de filtros avançados?
│     └─ SIM → Metadados Avançados (mas separado)
│
└─ NÃO (PDFs muito diferentes)
   │
   └─ Precisa de filtros?
      ├─ SIM → Metadados Avançados
      └─ NÃO → Sistema Separado
```

---

## 💡 Recomendações por Caso de Uso

### **Base de Conhecimento Médica**
```
✅ USAR: Knowledge Base Unificado

Exemplo:
- artigo_diabetes.pdf
- artigo_hipertensao.pdf
- artigo_obesidade.pdf

Vantagem: Fazer perguntas gerais e o sistema encontra
```

### **Tese/Dissertação Grande**
```
✅ USAR: Metadados Avançados

Exemplo:
- tese_completa.pdf (200 páginas)

Vantagem: Filtrar por capítulo/página
```

### **Documentos Corporativos**
```
✅ USAR: Knowledge Base Unificado

Exemplo:
- manual_procedimentos.pdf
- politicas_rh.pdf
- codigo_conduta.pdf

Vantagem: Busca global em toda documentação
```

### **Pesquisa/Review de Literatura**
```
✅ USAR: Knowledge Base Unificado

Exemplo:
- paper1.pdf
- paper2.pdf
- paper3.pdf

Vantagem: Comparar abordagens entre papers
```

### **Teste/Aprendizado**
```
✅ USAR: Sistema Separado

Exemplo:
- teste1.pdf

Vantagem: Simples e direto
```

---

## 🚀 Quick Start para Cada Sistema

### **Opção 1: Separado**
```bash
python processar_e_salvar.py "pdf.pdf"
python consultar_vectorstore.py pdf
```

### **Opção 2: Unificado** ⭐
```bash
python adicionar_pdf_ao_vectorstore.py "pdf1.pdf"
python adicionar_pdf_ao_vectorstore.py "pdf2.pdf"
python consultar_knowledge_base.py
```

### **Opção 3: Metadados**
```bash
python processar_com_metadata_avancado.py "pdf.pdf"
python consultar_com_filtros.py pdf_metadata
```

---

## 📚 Scripts por Sistema

### **Sistema Separado:**
- `processar_e_salvar.py`
- `consultar_vectorstore.py`
- `listar_vectorstores.py`

### **Knowledge Base Unificado:**
- `adicionar_pdf_ao_vectorstore.py`
- `consultar_knowledge_base.py`

### **Metadados Avançados:**
- `processar_com_metadata_avancado.py`
- `consultar_com_filtros.py`

### **Utilitários (todos):**
- `diagnosticar_extracao.py`
- `comparar_estrategias.py`
- `test_installation.py`

### **API REST:**
- `api_rest.py` (funciona com qualquer sistema)

---

## ✅ Recomendação Final

**Para a maioria dos casos: Use Knowledge Base Unificado! ⭐**

Porque:
- ✅ Mais intuitivo (não precisa escolher PDF)
- ✅ Busca global automática
- ✅ Cross-document queries
- ✅ Escalável
- ✅ Rastreabilidade mantida

**Só use os outros sistemas se tiver necessidade específica!**

---

**Documentação completa:** `KNOWLEDGE_BASE_UNIFICADO.md`

