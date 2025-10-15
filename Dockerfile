FROM python:3.11-slim-bookworm

# Variáveis de ambiente para otimização
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Instalar dependências do sistema necessárias para Unstructured + OpenCV + Tesseract + Poppler
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    poppler-data \
    libmagic1 \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copiar código da aplicação
COPY *.py .
COPY content/ ./content/

# Criar diretório para knowledge base
RUN mkdir -p knowledge_base

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:${PORT}/health', timeout=5)" || exit 1

# Comando para iniciar a API
CMD ["python", "consultar_com_rerank.py", "--api"]
