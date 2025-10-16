# 📚 Sistema de Gerenciamento de Documentos - Proposta Técnica

## 🎯 OBJETIVOS

1. ✅ **PDF_ID único** para cada documento (hash SHA256 do arquivo)
2. ✅ **Metadata completa** em todos os chunks/embeddings
3. ✅ **Sistema de deleção** por PDF_ID (remove todos os chunks)
4. ✅ **UI de gerenciamento** com lista de documentos
5. ✅ **Versionamento** (reprocessar PDF mantém histórico)

---

## 📊 SITUAÇÃO ATUAL

### ✅ O QUE JÁ TEMOS:

```python
# Cada chunk TEM metadata:
doc = Document(
    page_content=summary,
    metadata={
        "doc_id": "uuid-do-chunk",        # ✅ UUID por chunk
        "source": "arquivo.pdf",          # ✅ Nome do arquivo
        "type": "text",                   # ✅ Tipo do elemento
        "index": 0                        # ✅ Ordem no documento
    }
)
```

### ❌ O QUE FALTA:

1. **PDF_ID** - ID único do ARQUIVO (não do chunk)
2. **Tracking completo** - Lista de todos PDFs com seus IDs
3. **Função de deleção** - Apagar todos chunks de um PDF
4. **UI de gerenciamento** - Ver e deletar documentos

---

## 🏗️ ARQUITETURA PROPOSTA

### 1. ESTRUTURA DE METADADOS

```python
# Por CHUNK (no vectorstore):
{
    "doc_id": "uuid-do-chunk",           # UUID individual do chunk
    "pdf_id": "sha256-do-arquivo",       # ✅ NOVO: ID do PDF
    "source": "artigo.pdf",              # Nome do arquivo
    "type": "text|table|image",          # Tipo do conteúdo
    "index": 0,                          # Posição no documento
    "page_number": 5,                    # ✅ NOVO: Número da página
    "uploaded_at": "2025-01-15 10:30",   # ✅ NOVO: Timestamp
    "file_size": 1024000,                # ✅ NOVO: Tamanho em bytes
    "hash": "sha256..."                  # ✅ NOVO: Hash do arquivo
}

# No metadata.pkl (tracking global):
{
    "documents": {
        "sha256-hash-123": {
            "pdf_id": "sha256-hash-123",
            "filename": "artigo.pdf",
            "original_filename": "Artigo de Revisão - NEJM.pdf",
            "file_size": 1024000,
            "hash": "sha256...",
            "uploaded_at": "2025-01-15 10:30:00",
            "processed_at": "2025-01-15 10:35:00",
            "stats": {
                "texts": 14,
                "tables": 3,
                "images": 3,
                "total_chunks": 20
            },
            "chunk_ids": ["uuid-1", "uuid-2", ...],  # Para deleção rápida
            "status": "processed|processing|error",
            "error": null,
            "version": 1  # Para versionamento
        }
    }
}
```

---

## 🔧 IMPLEMENTAÇÃO

### 1. GERAÇÃO DO PDF_ID

```python
import hashlib

def generate_pdf_id(file_path):
    """Gera hash SHA256 do arquivo"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Ler em chunks para arquivos grandes
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Uso:
pdf_id = generate_pdf_id(file_path)  # "a3f8b2c..."
```

**Vantagens**:
- ✅ Único e determinístico (mesmo arquivo = mesmo ID)
- ✅ Detecta duplicatas automaticamente
- ✅ Detecta modificações (PDF alterado = novo ID)

---

### 2. ADICIONAR METADATA COMPLETA

```python
# No adicionar_pdf.py:

# Gerar PDF_ID no início
pdf_id = generate_pdf_id(file_path)
file_size = os.path.getsize(file_path)
uploaded_at = time.strftime("%Y-%m-%d %H:%M:%S")

# Adicionar aos chunks
for i, summary in enumerate(text_summaries):
    chunk_id = str(uuid.uuid4())
    doc = Document(
        page_content=summary,
        metadata={
            "doc_id": chunk_id,
            "pdf_id": pdf_id,           # ✅ ID do PDF
            "source": pdf_filename,
            "type": "text",
            "index": i,
            "page_number": texts[i].metadata.page_number if hasattr(texts[i].metadata, 'page_number') else None,
            "uploaded_at": uploaded_at,
            "file_size": file_size,
            "hash": pdf_id
        }
    )
    retriever.vectorstore.add_documents([doc])
    retriever.docstore.mset([(chunk_id, texts[i])])
```

---

### 3. FUNÇÃO DE DELEÇÃO

```python
def delete_document(pdf_id):
    """
    Remove TODOS os chunks/embeddings de um documento

    Args:
        pdf_id: Hash SHA256 do documento

    Returns:
        dict: {"deleted_chunks": 20, "status": "success"}
    """
    import pickle
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    persist_directory = "./knowledge_base"

    # 1. Carregar vectorstore
    vectorstore = Chroma(
        collection_name="knowledge_base",
        embedding_function=OpenAIEmbeddings(),
        persist_directory=persist_directory
    )

    # 2. Buscar todos chunks do PDF
    # ChromaDB suporta filtro por metadata
    results = vectorstore.get(
        where={"pdf_id": pdf_id}
    )

    chunk_ids = results['ids']

    if not chunk_ids:
        return {"deleted_chunks": 0, "status": "not_found", "error": "PDF não encontrado"}

    # 3. Deletar do vectorstore
    vectorstore.delete(ids=chunk_ids)

    # 4. Deletar do docstore
    docstore_path = f"{persist_directory}/docstore.pkl"
    if os.path.exists(docstore_path):
        with open(docstore_path, 'rb') as f:
            docstore = pickle.load(f)

        for chunk_id in chunk_ids:
            docstore.pop(chunk_id, None)

        with open(docstore_path, 'wb') as f:
            pickle.dump(docstore, f)

    # 5. Atualizar metadata.pkl
    metadata_path = f"{persist_directory}/metadata.pkl"
    if os.path.exists(metadata_path):
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)

        if 'documents' in metadata and pdf_id in metadata['documents']:
            del metadata['documents'][pdf_id]

            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)

    return {
        "deleted_chunks": len(chunk_ids),
        "pdf_id": pdf_id,
        "status": "success"
    }
```

---

### 4. API ENDPOINTS

```python
# No consultar_com_rerank.py:

@app.route('/documents', methods=['GET'])
def list_documents():
    """Lista todos documentos processados"""
    metadata_path = f"{persist_directory}/metadata.pkl"

    if not os.path.exists(metadata_path):
        return jsonify({"documents": []})

    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    documents = []
    for pdf_id, doc_info in metadata.get('documents', {}).items():
        documents.append({
            "pdf_id": pdf_id,
            "filename": doc_info['filename'],
            "uploaded_at": doc_info['uploaded_at'],
            "stats": doc_info['stats'],
            "status": doc_info.get('status', 'processed')
        })

    # Ordenar por data (mais recente primeiro)
    documents.sort(key=lambda x: x['uploaded_at'], reverse=True)

    return jsonify({"documents": documents, "total": len(documents)})


@app.route('/documents/<pdf_id>', methods=['DELETE'])
def delete_document_endpoint(pdf_id):
    """Deleta um documento e todos seus chunks"""

    # Validar API key se configurada
    required_key = os.getenv('API_SECRET_KEY')
    provided = request.headers.get('X-API-Key')
    if required_key and provided != required_key:
        return jsonify({"error": "Unauthorized"}), 401

    result = delete_document(pdf_id)

    if result['status'] == 'success':
        return jsonify(result), 200
    elif result['status'] == 'not_found':
        return jsonify(result), 404
    else:
        return jsonify(result), 500


@app.route('/documents/<pdf_id>', methods=['GET'])
def get_document_details(pdf_id):
    """Retorna detalhes de um documento específico"""
    metadata_path = f"{persist_directory}/metadata.pkl"

    if not os.path.exists(metadata_path):
        return jsonify({"error": "Documento não encontrado"}), 404

    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    doc_info = metadata.get('documents', {}).get(pdf_id)

    if not doc_info:
        return jsonify({"error": "Documento não encontrado"}), 404

    return jsonify(doc_info), 200
```

---

### 5. UI DE GERENCIAMENTO

**Nova página: `/manage` ou `/documents`**

```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gerenciar Documentos - Knowledge Base</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 1200px;
      margin: 40px auto;
      padding: 0 20px;
      color: #333;
    }
    h2 { margin-bottom: 20px; }

    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .stat-card {
      background: #f8f9fa;
      padding: 20px;
      border-radius: 8px;
      border: 1px solid #dee2e6;
    }

    .stat-value {
      font-size: 32px;
      font-weight: bold;
      color: #0066cc;
    }

    .stat-label {
      font-size: 14px;
      color: #666;
      margin-top: 4px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      border-radius: 8px;
      overflow: hidden;
    }

    th {
      background: #f8f9fa;
      padding: 12px;
      text-align: left;
      font-weight: 600;
      border-bottom: 2px solid #dee2e6;
    }

    td {
      padding: 12px;
      border-bottom: 1px solid #f0f0f0;
    }

    .btn {
      padding: 6px 12px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.2s;
    }

    .btn-delete {
      background: #dc3545;
      color: white;
    }

    .btn-delete:hover {
      background: #c82333;
    }

    .btn-view {
      background: #0066cc;
      color: white;
      margin-right: 8px;
    }

    .btn-view:hover {
      background: #0052a3;
    }

    .status-badge {
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
    }

    .status-processed {
      background: #d4edda;
      color: #155724;
    }

    .status-processing {
      background: #fff3cd;
      color: #856404;
    }

    .status-error {
      background: #f8d7da;
      color: #721c24;
    }

    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: #666;
    }

    .loading {
      text-align: center;
      padding: 40px;
      color: #666;
    }
  </style>
</head>
<body>
  <h2>Gerenciar Documentos</h2>

  <div class="stats" id="stats">
    <div class="stat-card">
      <div class="stat-value" id="total-docs">-</div>
      <div class="stat-label">Documentos</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="total-chunks">-</div>
      <div class="stat-label">Total de Chunks</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="total-size">-</div>
      <div class="stat-label">Tamanho Total</div>
    </div>
  </div>

  <div id="loading" class="loading">Carregando documentos...</div>

  <div id="content" style="display: none;">
    <table id="documents-table">
      <thead>
        <tr>
          <th>Arquivo</th>
          <th>Enviado em</th>
          <th>Status</th>
          <th>Chunks</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody id="documents-list">
      </tbody>
    </table>

    <div id="empty-state" class="empty-state" style="display: none;">
      <p>Nenhum documento processado ainda.</p>
      <p><a href="/ui">Fazer upload de PDF</a></p>
    </div>
  </div>

  <script>
    async function loadDocuments() {
      try {
        const response = await fetch('/documents');
        const data = await response.json();

        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').style.display = 'block';

        if (data.documents.length === 0) {
          document.getElementById('empty-state').style.display = 'block';
          document.getElementById('documents-table').style.display = 'none';
          return;
        }

        // Atualizar estatísticas
        let totalChunks = 0;
        let totalSize = 0;

        data.documents.forEach(doc => {
          totalChunks += doc.stats.total_chunks || 0;
          totalSize += doc.file_size || 0;
        });

        document.getElementById('total-docs').textContent = data.total;
        document.getElementById('total-chunks').textContent = totalChunks.toLocaleString();
        document.getElementById('total-size').textContent = formatBytes(totalSize);

        // Renderizar tabela
        const tbody = document.getElementById('documents-list');
        tbody.innerHTML = '';

        data.documents.forEach(doc => {
          const row = document.createElement('tr');

          const statusClass = `status-${doc.status}`;
          const statusText = {
            'processed': 'Processado',
            'processing': 'Processando',
            'error': 'Erro'
          }[doc.status] || doc.status;

          row.innerHTML = `
            <td>
              <strong>${escapeHtml(doc.filename)}</strong><br>
              <small style="color: #666;">${doc.pdf_id.substring(0, 16)}...</small>
            </td>
            <td>${formatDate(doc.uploaded_at)}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>
              ${doc.stats.texts}T, ${doc.stats.tables}Tab, ${doc.stats.images}I
              <br><small>${doc.stats.total_chunks} total</small>
            </td>
            <td>
              <button class="btn btn-view" onclick="viewDocument('${doc.pdf_id}')">Detalhes</button>
              <button class="btn btn-delete" onclick="deleteDocument('${doc.pdf_id}', '${escapeHtml(doc.filename)}')">Deletar</button>
            </td>
          `;

          tbody.appendChild(row);
        });

      } catch (error) {
        console.error('Erro ao carregar documentos:', error);
        document.getElementById('loading').innerHTML = 'Erro ao carregar documentos.';
      }
    }

    async function deleteDocument(pdfId, filename) {
      if (!confirm(`Tem certeza que deseja deletar "${filename}"?\n\nTodos os chunks e embeddings serão removidos permanentemente.`)) {
        return;
      }

      try {
        const response = await fetch(`/documents/${pdfId}`, {
          method: 'DELETE',
          headers: {
            'X-API-Key': ''  // Adicione se necessário
          }
        });

        const result = await response.json();

        if (response.ok) {
          alert(`Documento deletado com sucesso!\n${result.deleted_chunks} chunks removidos.`);
          loadDocuments();  // Recarregar lista
        } else {
          alert(`Erro ao deletar: ${result.error}`);
        }
      } catch (error) {
        console.error('Erro ao deletar:', error);
        alert('Erro ao deletar documento.');
      }
    }

    function viewDocument(pdfId) {
      // Redirecionar para página de detalhes ou abrir modal
      window.location.href = `/documents/${pdfId}`;
    }

    function formatBytes(bytes) {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    function formatDate(dateStr) {
      const date = new Date(dateStr);
      return date.toLocaleString('pt-BR');
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Carregar ao iniciar
    loadDocuments();

    // Auto-refresh a cada 30 segundos
    setInterval(loadDocuments, 30000);
  </script>
</body>
</html>
```

---

## 🚀 MELHORIAS ADICIONAIS

### 1. DETECÇÃO DE DUPLICATAS

```python
# No upload:
pdf_id = generate_pdf_id(file_path)

# Verificar se já existe
metadata_path = f"{persist_directory}/metadata.pkl"
if os.path.exists(metadata_path):
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    if pdf_id in metadata.get('documents', {}):
        existing_doc = metadata['documents'][pdf_id]
        print(f"⚠️  PDF já existe!")
        print(f"   Adicionado em: {existing_doc['uploaded_at']}")

        # Opções:
        # 1. Reprocessar (versionar)
        # 2. Pular
        # 3. Perguntar ao usuário

        choice = input("Reprocessar? (s/N): ")
        if choice.lower() != 's':
            exit(0)
```

### 2. VERSIONAMENTO

```python
# Manter histórico de versões
{
    "documents": {
        "sha256-hash": {
            "current_version": 2,
            "versions": [
                {
                    "version": 1,
                    "uploaded_at": "2025-01-15 10:00",
                    "stats": {...}
                },
                {
                    "version": 2,
                    "uploaded_at": "2025-01-16 14:30",
                    "stats": {...}
                }
            ]
        }
    }
}
```

### 3. BUSCA POR DOCUMENTO

```python
@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    question = data.get('question')
    pdf_ids = data.get('pdf_ids', [])  # ✅ NOVO: Filtrar por PDFs

    # Se pdf_ids fornecido, buscar só nesses documentos
    if pdf_ids:
        filter_dict = {"pdf_id": {"$in": pdf_ids}}
        docs = retriever.invoke(question, filter=filter_dict)
    else:
        docs = retriever.invoke(question)

    # ...
```

### 4. TAGS E CATEGORIAS

```python
# Adicionar tags aos documentos
{
    "pdf_id": "sha256...",
    "filename": "artigo.pdf",
    "tags": ["medicina", "cardiologia", "revisão"],
    "category": "artigos-científicos",
    "language": "pt-BR"
}
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

- [ ] Adicionar função `generate_pdf_id()`
- [ ] Modificar `adicionar_pdf.py` para incluir `pdf_id` em todos chunks
- [ ] Criar função `delete_document(pdf_id)`
- [ ] Adicionar endpoints de API (`/documents`, `/documents/<id>`)
- [ ] Criar UI de gerenciamento (`/manage`)
- [ ] Adicionar detecção de duplicatas
- [ ] Implementar versionamento (opcional)
- [ ] Adicionar busca filtrada por documento (opcional)
- [ ] Testar deleção completa de documento
- [ ] Documentar na README

---

## 🎯 BENEFÍCIOS

1. ✅ **Rastreabilidade total** - Saber exatamente o que está no knowledge base
2. ✅ **Atualização fácil** - Deletar e reprocessar PDFs obsoletos
3. ✅ **Sem duplicatas** - Detecta PDFs já processados
4. ✅ **Gerenciamento visual** - UI amigável para ver e deletar documentos
5. ✅ **Performance** - Buscar só em documentos específicos
6. ✅ **Metadados ricos** - Estatísticas, timestamps, tamanhos
7. ✅ **Produção-ready** - Sistema robusto e escalável

---

## 🔄 FLUXO COMPLETO

```
1. UPLOAD
   ↓
2. Gerar PDF_ID (SHA256)
   ↓
3. Verificar duplicata
   ↓
4. Processar PDF
   ↓
5. Adicionar chunks com metadata completa (pdf_id, source, type, etc)
   ↓
6. Salvar tracking em metadata.pkl
   ↓
7. Mostrar na UI de gerenciamento

DELEÇÃO:
   ↓
1. Buscar chunks por pdf_id
   ↓
2. Deletar do vectorstore
   ↓
3. Deletar do docstore
   ↓
4. Atualizar metadata.pkl
   ↓
5. Confirmar na UI
```

---

**Pronto para implementar?** 🚀
