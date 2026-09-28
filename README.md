# Eleições 2026 — Previsão: Cenário Nacional (Lula × Flávio) e Estadual MA (Braide × Orleans)

## Rodar o painel
```
streamlit run app.py
```
Duas páginas no topo: **Cenário Nacional** e **Cenário Estadual MA**. Senha opcional: variável `APP_PASSWORD`.

## Atualizar os números
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
No nacional, o 2º turno usa só os erros da era polarizada (2018, 2022 e as simulações de 2º turno feitas antes do 1º turno
de 2022), porque os grandes erros de 2006–2014 vieram de voto útil de 1º turno.
