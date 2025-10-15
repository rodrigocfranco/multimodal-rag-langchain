FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências de sistema para Unstructured + OpenCV + Tesseract + Poppler + libmagic
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    tesseract-ocr \
    poppler-utils \
    poppler-data \
    libmagic1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o app
COPY . .

# Porta definida pelo Railway (POR PADRÃO ELE USA 8080, mas leremos PORT)
ENV PORT=8080

# Executa nossa API (modo hi_res por padrão)
CMD ["python", "consultar_com_rerank.py", "--api"]
