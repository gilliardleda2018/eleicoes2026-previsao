# Imagem do painel para o Google Cloud Run (também roda em qualquer host com Docker).
# Build e deploy: veja cloudbuild.yaml e a seção "Google Cloud" do README.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo \
    APURACAO_CACHE_DIR=/tmp/eleicoes2026_2t \
    APURACAO_HISTORICO_DB=/tmp/eleicoes2026_historico.sqlite3

WORKDIR /app
COPY requirements.txt .
RUN pip install --retries 10 --timeout 60 -r requirements.txt

COPY . .

# Cloud Run informa a porta em $PORT (8080 por padrão)
EXPOSE 8080
CMD streamlit run app.py \
    --server.port ${PORT:-8080} --server.address 0.0.0.0 \
    --server.headless true --browser.gatherUsageStats false \
    --server.enableCORS false --server.enableXsrfProtection true
