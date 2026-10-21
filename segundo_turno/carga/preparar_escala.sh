#!/usr/bin/env bash
# Prepara o serviço do painel para 1.000+ pessoas conectadas ao mesmo tempo (rodar no Cloud Shell, em ~/apuracao-cloud).
#   bash segundo_turno/carga/preparar_escala.sh            → configura (pode repetir; é idempotente)
#   MIN=6 bash segundo_turno/carga/preparar_escala.sh      → idem, com 6 instâncias sempre ligadas (domingo)
set -euo pipefail
PROJETO=$(gcloud config get-value project 2>/dev/null)
REGIAO=${REGIAO:-southamerica-east1}
SERVICO=${SERVICO:-apuracao-teste}
BUCKET=${BUCKET:-${PROJETO}-aovivo}
MIN=${MIN:-2}            # instâncias sempre ligadas (no domingo: 6)
# Cota atual do projeto em southamerica-east1: 20 vCPU e 40 GiB por região → 20 instâncias de 1 vCPU / 2 GiB.
# O Streamlit roda o Python num processo só (1 núcleo efetivo), então 1 vCPU por instância rende quase o mesmo que 2.
CPU=${CPU:-1}
MEM=${MEM:-2Gi}
MAX=${MAX:-20}           # teto de instâncias (20 × 60 = 1.200 pessoas); com mais cota: MAX=40
POR_INST=${POR_INST:-60} # pessoas por instância (o Streamlit roda o Python de todas no mesmo processo)

echo "== 1/4 bucket compartilhado entre as instâncias: gs://$BUCKET"
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 || \
  gcloud storage buckets create "gs://$BUCKET" --location="$REGIAO" --uniform-bucket-level-access
# leituras antigas não servem para nada: apaga depois de 3 dias
echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":3}}]}' > /tmp/ciclo_aovivo.json
gcloud storage buckets update "gs://$BUCKET" --lifecycle-file=/tmp/ciclo_aovivo.json >/dev/null

echo "== 2/4 permissão da conta do serviço no bucket"
SA=$(gcloud run services describe "$SERVICO" --region "$REGIAO" --format='value(spec.template.spec.serviceAccountName)')
if [ -z "$SA" ]; then
  NUM=$(gcloud projects describe "$PROJETO" --format='value(projectNumber)')
  SA="${NUM}-compute@developer.gserviceaccount.com"
fi
echo "   conta: $SA"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$SA" \
  --role=roles/storage.objectUser >/dev/null

echo "== 3/4 publicando com escala para muitas conexões"
COMUM=(--region "$REGIAO" --execution-environment gen2
  --session-affinity --timeout=3600 --concurrency="$POR_INST" --min-instances="$MIN" --max-instances="$MAX"
  --cpu="$CPU" --memory="$MEM" --no-cpu-throttling --cpu-boost
  --update-env-vars "TZ=America/Sao_Paulo,APURACAO_COMPARTILHADO=/mnt/aovivo/apuracao,PRESENCA_DIR=/mnt/aovivo,STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION=true,STREAMLIT_SERVER_WEBSOCKET_PING_INTERVAL=25,STREAMLIT_SERVER_DISCONNECTED_SESSION_TTL=60")
VOL="name=aovivo,type=cloud-storage,bucket=$BUCKET"
set +e
gcloud run deploy "$SERVICO" --source . "${COMUM[@]}" \
  --add-volume "$VOL,mount-options=metadata-cache-ttl-secs=0" --add-volume-mount volume=aovivo,mount-path=/mnt/aovivo \
  2>&1 | tee /tmp/deploy_aovivo.log
ST=${PIPESTATUS[0]}
set -e
if [ "$ST" != 0 ]; then
  if grep -q "Quota violated" /tmp/deploy_aovivo.log; then
    echo "PARE: cota de CPU/memória da região. Use um MAX menor (ex.: MAX=10) ou peça aumento da cota." >&2; exit 1
  fi
  echo "   (o gcloud recusou mount-options: tentando sem — o código tolera leituras com alguns segundos de atraso)"
  gcloud run deploy "$SERVICO" --source . "${COMUM[@]}" \
    --add-volume "$VOL" --add-volume-mount volume=aovivo,mount-path=/mnt/aovivo
fi
gcloud run services update-traffic "$SERVICO" --region "$REGIAO" --to-latest

echo "== 4/4 conferência"
gcloud run services describe "$SERVICO" --region "$REGIAO" --format=yaml | \
  grep -E "minScale|maxScale|containerConcurrency|cpu:|memory:|sessionAffinity|execution-environment|APURACAO_COMPARTILHADO" || true
echo "Capacidade: até $((MAX * POR_INST)) pessoas ao mesmo tempo · $MIN instância(s) sempre ligada(s)."
