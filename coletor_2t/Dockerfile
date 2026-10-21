FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TURNO=2
WORKDIR /app
RUN pip install --no-cache-dir "google-cloud-storage>=3,<4"
COPY coletor_tse.py executar_cloud.py ./
CMD ["python", "executar_cloud.py"]
