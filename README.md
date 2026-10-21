# Eleições 2026 — Previsão e apuração: 2º turno (Lula × Flávio) e arquivo do 1º turno

## Rodar o painel
```
streamlit run app.py
```
Páginas: **2º turno** (`segundo_turno/painel_2t.py`: previsão, apuração ao vivo, Maranhão por município, Tuntum por
seção, pesquisas e metodologia) e, como arquivo do 1º turno, **Cenário Nacional**, **Cenário Estadual MA** e
**Apuração ao vivo**. Senha opcional: variável `APP_PASSWORD` (sem ela, o painel é público).
O painel estratégico da Bruna Pessoa não faz parte deste app (fica no app próprio, bruna_api_webapp_v2_mapa).

## 2º turno (25/10/2026)
- **Dados oficiais do 1º turno** (TSE, conferidos: as partes somam exatamente os totais) em
  `segundo_turno/dados/tse_1t_2026/`: 27 UFs + exterior + Brasil, 217 municípios do MA e as 97 seções de Tuntum
  (lidas dos boletins de urna, agrupadas em 36 locais de votação).
- **Pesquisas e contexto** em `segundo_turno/dados/`: `pesquisas_2t_2026.csv` (registro no TSE, válidos),
  `pesquisas_2t_regioes.csv` (Datafolha por região), `transferencia_2t.csv` (para onde vão os eleitores de Cury, Renan,
  Caiado e Zema) e `contexto_2t.csv` (apoios, debates, agenda, índice digital — com fonte).
- **Modelo**: `python segundo_turno/modelo_2t.py` (gera `segundo_turno/resultados/`). Mesmo método do nacional:
  6 agregadores + erro das pesquisas com persistência incerta (2º turnos 2006–2022 e o erro de cada instituto no
  1º turno de 2026) + base estrutural (1º turno real + transferência medida). Geografia Brasil → UF → município → seção,
  calibrada em logit. Para incluir uma pesquisa nova: acrescente a linha no CSV e rode o modelo de novo.
- **Ao vivo** (`segundo_turno/motor_2t.py`), com fallback em camadas: códigos manuais (`segundo_turno/codigos_2t.json`)
  → config do TSE → códigos publicados (6258, pleito 3221); arquivo unificado → simplificado; Brasil → soma das UFs;
  boletins de urna por seção (cache em disco); TSE fora do ar → última leitura boa. Modo **Ensaio** na própria página.
  Antes do domingo, a aba Ao vivo tem um diagnóstico que testa cada camada a partir do servidor.
- **Testes**: `python -m unittest discover -s segundo_turno/testes -p "test_*.py"` e
  `python segundo_turno/testes/smoke_painel.py` (executa a página inteira sem navegador).
- Pontos dos locais de votação de Tuntum no mapa: opcional, `segundo_turno/dados/locais_tuntum.csv`
  (`local,nome,endereco,lat,lon`).

## Google Cloud (Cloud Run)
`Dockerfile` + `cloudbuild.yaml`: `gcloud builds submit --config cloudbuild.yaml --substitutions=_SERVICE=<serviço>,_REGION=<região>`.
O deploy liga afinidade de sessão (websocket do Streamlit), timeout de 1 h, 1 instância mínima e CPU sempre ligada, para
o domingo não ter "cold start". Variáveis: `APP_PASSWORD` (Secret Manager), `PUBLIC_URL` (miniatura do link),
`TSE_AMBIENTE` (`oficial` ou `simulado`), `APURACAO_CACHE_DIR`. O cache em `/tmp` é por instância e some ao reiniciar
(é só cache: o TSE continua sendo a fonte).

## Apuração ao vivo (domingo)
- Lê a apuração oficial do TSE (resultados.tse.jus.br) a cada 90 s: 27 estados (presidente) e 217 municípios (governador MA).
- **Assembleia MA**: acompanha em votos só Bruna Pessoa (15800), Abigail Cunha e Eric Costa (cargo 7, mesmos 217
  municípios). A Bruna é comparada com a projeção do modelo; Abigail e Eric com a votação de 2022 + 3% de eleitorado.
  Projeções por município em `apuracao/deputados_previsao.csv` (só os números, extraídos do modelo da Bruna; para
  atualizar, rode `python apuracao/atualizar_deputados.py` depois de recalcular o modelo em C:\modelo_bruna).
  Os nomes de urna procurados ficam em `apuracao/motor.py` (`NOMES_2026["deputado"]`). O ensaio dos deputados roda
  sem internet (votos reais de 2022 de Abigail e Eric; os da Bruna são sorteados em torno da projeção).
- Compara cada unidade apurada com a projeção do modelo e estima o resultado final (desvio aplicado aos votos que faltam).
- Descobre sozinha os códigos da eleição de 2026 na configuração pública do TSE. Se precisar fixar à mão, crie
  `apuracao/codigos_2026.json`: `{"ciclo": "ele2026", "presidente": {"1": "XXX", "2": "YYY"}, "governador": {"1": "ZZZ", "2": "WWW"}}` (o de deputado, se faltar, é o do governador no 1º turno).
- **Modo ensaio**: reproduz a apuração de 2022 para testar. Calibração: com 15% ou mais apurado, a faixa de 80% contém o
  resultado real em 82% a 91% das simulações.

## Atualizar os números
No computador, instale uma vez: `pip install -r requirements-modelos.txt` (o `requirements.txt` é só o do painel publicado).
Clique duas vezes em `atualizar_tudo.bat` (roda os 6 scripts dos dois cenários e pergunta se envia ao GitHub). Ou, à mão:
```
# Estadual (Maranhão)
python preparar_base.py && python modelos_pesquisas.py && python modelo_municipios_mc.py
# Nacional
cd nacional && python preparar_base_nacional.py && python modelos_pesquisas_nacional.py && python modelo_ufs_mc.py
```

## Mesma metodologia nos dois cenários
| Etapa | Estadual (MA) | Nacional |
|---|---|---|
| Pesquisas | `dados/pesquisas_verificadas.csv` | `nacional/dados/pesquisas_presidente.csv` |
| 6 agregadores (`agregadores.py`, código comum) | 1º e 2º turno | 1º e 2º turno |
| Histórico oficial (TSE) | governador 2018/2022, 217 municípios | presidente 2018/2022, 27 UFs (API TSE) |
| 5 modelos de ML de geografia | municípios | estados |
| Calibração regional | IPPI (mesorregiões), IPSensus (capital) | recortes regionais e pesquisas estaduais |
| Máquina política | 217 prefeitos | 27 governadores |
| Erro histórico das pesquisas | governador no Nordeste 2014–2022 | presidente 2006–2022 + 2º turno antecipado 2022 |
| Transferência para o 2º turno | medida em pesquisas com os dois turnos | medida em pesquisas com os dois turnos |
| Monte Carlo | 20 mil cenários + alerta (Bahia/Piauí) | 20 mil cenários + alerta (padrão 2022) |
| Mídia | 63 itens | 71 itens |

Regra do erro histórico: erro de uma eleição real sorteada × persistência incerta (0 a 100%) + ruído.
No nacional (1º turno), o 2º turno usa os erros das pesquisas finais de 2º turno de 2006–2022 (uma média por eleição);
o erro das simulações de 2º turno feitas antes do 1º turno de 2022 fica só no cenário de alerta. (Este README dizia
"só a era polarizada", o que não correspondia ao código.)
