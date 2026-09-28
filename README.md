# Governo do Maranhão 2026 — Braide × Orleans (modelo independente)

## Rodar
```
python preparar_base.py
python modelos_pesquisas.py
python modelo_municipios_mc.py
streamlit run painel_governo_ma.py
```

## Dados (pasta `dados/`)
- `pesquisas_verificadas.csv` — pesquisas conferidas em segunda fonte (e registro PesqEle); `pesquisas_governo_ma_2026.csv` — compilação pública.
- `pesquisas_recortes_regionais.csv` — recortes por mesorregião (IPPI) e por cidade (IPSensus).
- `erro_historico_pesquisas.csv` — pesquisas finais × urna, governador no Nordeste 2014–2022.
- `prefeitos_apoio_governo_2026.csv` — posição pública dos 217 prefeitos (18/09/2026).
- `midia_itens.csv`, `midia_argumentos.md` — mídia classificada, com links.
- `tse/` — votação por município (TSE), governador 2018 e 2022.

## Modelos
1. `modelos_pesquisas.py` — 6 agregadores (média ponderada, mediana robusta, regressão com efeito-instituto, Kalman,
   processo gaussiano, bayesiano hierárquico).
2. `modelo_municipios_mc.py` — 5 modelos de ML de geografia (2018→2022), calibração regional por pesquisas,
   efeito dos prefeitos, erro histórico das pesquisas e Monte Carlo (20 mil cenários) de 1º e 2º turno.

Senha opcional do painel: variável `APP_PASSWORD`.
