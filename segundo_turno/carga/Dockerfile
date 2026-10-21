# Gerador de carga (Cloud Run Job): cada tarefa abre PESSOAS sessões na página do 2º turno.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# streamlit só para os protocolos (mensagens do websocket); mesma versão da produção
ARG STREAMLIT_VERSAO=1.62.0
RUN pip install --no-cache-dir "aiohttp>=3.9" "streamlit==${STREAMLIT_VERSAO}"
COPY carga_2t.py .
CMD ["python", "carga_2t.py"]
