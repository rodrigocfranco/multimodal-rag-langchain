#!/bin/bash
# Script para resetar ChromaDB após downgrade 1.3→0.5
# Execute: railway run bash railway_reset_chromadb.sh

echo "🔄 Resetando ChromaDB incompatível (1.3→0.5 downgrade)"
echo "=================================================="

BASE_DIR="${PERSIST_DIR:-/app/base}"

echo "📁 Base directory: $BASE_DIR"

# 1. Deletar chroma.sqlite3 (formato 1.3.0 incompatível)
echo ""
echo "1️⃣ Deletando chroma.sqlite3..."
rm -f "$BASE_DIR/chroma.sqlite3"
rm -f "$BASE_DIR/chroma.sqlite3-wal"
rm -f "$BASE_DIR/chroma.sqlite3-shm"
echo "   ✅ chroma.sqlite3 deletado"

# 2. Deletar diretórios de índice HNSW (UUID format)
echo ""
echo "2️⃣ Deletando índices HNSW antigos..."
find "$BASE_DIR" -maxdepth 1 -type d -name "*-*-*-*-*" -exec rm -rf {} + 2>/dev/null || true
echo "   ✅ Índices HNSW deletados"

# 3. Deletar docstore.pkl (embeddings antigos)
echo ""
echo "3️⃣ Deletando docstore.pkl..."
rm -f "$BASE_DIR/docstore.pkl"
echo "   ✅ docstore.pkl deletado"

# 4. Preservar metadata.pkl (lista de documentos)
echo ""
echo "4️⃣ Verificando metadata.pkl..."
if [ -f "$BASE_DIR/metadata.pkl" ]; then
    echo "   ✅ metadata.pkl preservado ($(stat -f%z "$BASE_DIR/metadata.pkl" 2>/dev/null || stat -c%s "$BASE_DIR/metadata.pkl") bytes)"
else
    echo "   ℹ️  metadata.pkl não existe (ok, será criado no primeiro upload)"
fi

# 5. Listar o que sobrou
echo ""
echo "5️⃣ Conteúdo final de $BASE_DIR:"
ls -lah "$BASE_DIR" 2>/dev/null || echo "   (diretório vazio)"

echo ""
echo "=================================================="
echo "✅ Reset completo!"
echo ""
echo "Próximos passos:"
echo "1. Restart do app (railway restart)"
echo "2. Aguardar app iniciar"
echo "3. Fazer upload do PDF novamente"
echo "=================================================="
