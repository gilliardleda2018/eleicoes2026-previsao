#!/usr/bin/env bash
# Cria o serviço de PRODUÇÃO com nome definitivo (o Cloud Run não renomeia serviços) e aposenta o "apuracao-teste".
# Rodar no Cloud Shell, em ~/apuracao-cloud:
#   bash segundo_turno/carga/criar_producao.sh
set -euo pipefail
REGIAO=${REGIAO:-southamerica-east1}
ANTIGO=${ANTIGO:-apuracao-teste}
NOVO=${NOVO:-eleicoes2026}

echo "== 1/4 liberando cota: o $ANTIGO fica com no máximo 1 instância (continua no ar para links antigos)"
gcloud run services update "$ANTIGO" --region "$REGIAO" --min-instances=0 --max-instances=1 >/dev/null
# a etiqueta "previa" (endereço previa---...) não é mais necessária
gcloud run services update-traffic "$ANTIGO" --region "$REGIAO" --remove-tags previa >/dev/null 2>&1 || true

echo "== 2/4 publicando o serviço de produção: $NOVO"
SERVICO="$NOVO" COPIAR_DE="$ANTIGO" bash "$(dirname "$0")/preparar_escala.sh"

URL=$(gcloud run services describe "$NOVO" --region "$REGIAO" --format='value(status.url)')
echo "== 3/4 endereço público da produção no próprio serviço (link de compartilhar e miniatura do WhatsApp)"
gcloud run services update "$NOVO" --region "$REGIAO" --update-env-vars "PUBLIC_URL=$URL" >/dev/null

echo "== 4/4 pronto"
echo "Produção:            $URL"
echo "Só o 2º turno:       $URL/segundo_turno?so2t=1"
echo "Ao vivo direto:      $URL/segundo_turno?so2t=1&modo=vivo"
echo "Aponte a sua página de redirecionamento para o link 'Só o 2º turno'."
