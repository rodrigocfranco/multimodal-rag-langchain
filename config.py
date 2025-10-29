"""
Configuração centralizada do sistema
ÚNICA FONTE DA VERDADE para caminhos e configurações
"""
import os

# === DIRETÓRIOS ===
# Prioridade: PERSIST_DIR (env) > /app/base (Railway) > ./knowledge (local)
PERSIST_DIR = os.getenv("PERSIST_DIR")
if not PERSIST_DIR:
    # Railway default (novo volume)
    if os.path.exists("/app/base"):
        PERSIST_DIR = "/app/base"
    else:
        PERSIST_DIR = "./knowledge"

# SEMPRE usar caminho absoluto
PERSIST_DIR = os.path.abspath(PERSIST_DIR)

# Paths derivados
DOCSTORE_PATH = os.path.join(PERSIST_DIR, "docstore.pkl")
METADATA_PATH = os.path.join(PERSIST_DIR, "metadata.pkl")
CHROMA_PATH = os.path.join(PERSIST_DIR, "chroma.sqlite3")

# === CHROMA CONFIG ===
COLLECTION_NAME = "knowledge_base"

# === MODELS ===
EMBEDDING_MODEL = "text-embedding-3-large"
LLM_MODEL = "gpt-4o-mini"
RERANK_MODEL = "rerank-multilingual-v3.0"

# === DEBUG ===
def print_config():
    """Imprime configuração atual (útil para debug)"""
    print("=" * 70)
    print("CONFIGURAÇÃO DO SISTEMA")
    print("=" * 70)
    print(f"PERSIST_DIR: {PERSIST_DIR}")
    print(f"DOCSTORE_PATH: {DOCSTORE_PATH}")
    print(f"METADATA_PATH: {METADATA_PATH}")
    print(f"CHROMA_PATH: {CHROMA_PATH}")
    print(f"COLLECTION_NAME: {COLLECTION_NAME}")
    print(f"EMBEDDING_MODEL: {EMBEDDING_MODEL}")
    print("=" * 70)

if __name__ == "__main__":
    print_config()
