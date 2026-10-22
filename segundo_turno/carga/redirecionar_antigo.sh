#!/usr/bin/env bash
# Troca o serviço antigo (apuracao-teste) por um redirecionador para a produção (eleicoes2026).
# Todo link antigo — inclusive os que já circularam no WhatsApp — passa a abrir a versão nova.
#   bash segundo_turno/carga/redirecionar_antigo.sh
set -euo pipefail
REGIAO=${REGIAO:-southamerica-east1}
ANTIGO=${ANTIGO:-apuracao-teste}
NOVO=${NOVO:-eleicoes2026}
DESTINO=$(gcloud run services describe "$NOVO" --region "$REGIAO" --format='value(status.url)')
echo "Redirecionando $ANTIGO → $DESTINO"
gcloud run deploy "$ANTIGO" --source "$(dirname "$0")/../redirecionador" --region "$REGIAO" --allow-unauthenticated \
  --set-env-vars "DESTINO=$DESTINO" --cpu 1 --memory 512Mi --cpu-throttling --execution-environment gen1 \
  --min-instances 0 --max-instances 2 --no-session-affinity
gcloud run services update-traffic "$ANTIGO" --region "$REGIAO" --to-latest
URL_ANTIGA=$(gcloud run services describe "$ANTIGO" --region "$REGIAO" --format='value(status.url)')
echo "Teste: curl -sI $URL_ANTIGA/segundo_turno?so2t=1 | grep -i location"
curl -sI "$URL_ANTIGA/segundo_turno?so2t=1" | grep -i "^location" || true
