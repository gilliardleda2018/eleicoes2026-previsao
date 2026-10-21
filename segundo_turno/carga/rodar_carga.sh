#!/usr/bin/env bash
# Teste de carga com N pessoas simuladas (Cloud Run Job, várias tarefas em paralelo). Rodar em ~/apuracao-cloud.
#   PESSOAS=1200 bash segundo_turno/carga/rodar_carga.sh
set -euo pipefail
REGIAO=${REGIAO:-southamerica-east1}
SERVICO=${SERVICO:-apuracao-teste}
PESSOAS=${PESSOAS:-1200}
TAREFAS=${TAREFAS:-6}
RAMPA=${RAMPA:-300}      # segundos até todos entrarem (às 17h de domingo a chegada é parecida)
DURACAO=${DURACAO:-480}  # quanto tempo cada pessoa fica conectada
URL=${URL:-$(gcloud run services describe "$SERVICO" --region "$REGIAO" --format='value(status.url)')}
POR_TAREFA=$(( (PESSOAS + TAREFAS - 1) / TAREFAS ))
echo "Alvo: $URL · $PESSOAS pessoas em $TAREFAS tarefas ($POR_TAREFA cada) · rampa ${RAMPA}s · ${DURACAO}s conectadas"
gcloud run jobs deploy carga-2t --source segundo_turno/carga --region "$REGIAO" \
  --tasks "$TAREFAS" --parallelism "$TAREFAS" --max-retries 0 --task-timeout 1800 --cpu 2 --memory 2Gi \
  --set-env-vars "URL=$URL,PESSOAS=$POR_TAREFA,RAMPA=$RAMPA,DURACAO=$DURACAO"
gcloud run jobs execute carga-2t --region "$REGIAO" --wait || true
sleep 30
echo "== RESUMO de cada tarefa"
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="carga-2t" AND textPayload:"RESUMO"' \
  --freshness=1h --limit "$TAREFAS" --format='value(textPayload)'
echo "== Instâncias do painel durante o teste: Console → Cloud Run → $SERVICO → Métricas (instâncias, CPU, memória)"
