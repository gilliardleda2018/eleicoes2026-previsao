# Revisão da projeção pública de Bruna Pessoa

Escopo: integridade estatística da projeção eleitoral e do motor de apuração. Recursos de segmentação, mobilização, agenda e recomendações de campanha não foram alterados nem executados.

## Origem e treino

O CSV importado do V13 contém 217 municípios únicos, sem campos vazios nas oito colunas. A soma de `votos_projetados` é 53.106. A origem documentada é o repositório `gilliardleda2018/bruna_api_webapp_v2_mapa`, arquivos `modelos_v13.py`, `preparar_base_v13.py` e resultados exportados.

O Gradient Boosting aprende um potencial histórico de Fernando Pessoa em 2018, usando também características de 2022. A validação aleatória em cinco partes é uma reconstrução retrospectiva, não uma previsão temporal de 2026. O resumo registra R² 0,241 na escala logarítmica e erro médio 1,48 ponto percentual na escala original; esses indicadores não medem o erro dos votos futuros de Bruna. Importâncias são calculadas no conjunto de treino.

`pct_potencial_ml` não entra na função `projetar` que gera os votos de Bruna. Por isso retreinar esse algoritmo não corrige a previsão do painel público. Não houve retreinamento nem mudança arbitrária dos totais.

O total inicial resulta de hipóteses: transferência 78%, recuperação 35%, realização das expectativas de campo 50%, crescimento uniforme 3%, sobreposição aproximada entre eleições e conversão especial em Tuntum. Sobreposição de porcentagens agregadas não demonstra que sejam os mesmos eleitores. Expectativas de campo não são pesquisas amostrais. As taxas não têm calibração temporal comprovada.

## Simulações e apuração

O V13 fornece uma distribuição de 20 mil simulações, com mediana 53.444 e P10/P90 de 41.238 a 68.559. A apuração usa outra distribuição: bootstrap municipal de 3 mil amostras e choque lognormal comum de intensidade inicial 0,20. Não importa a distribuição completa do V13.

Com nenhuma seção apurada, a execução reproduz mediana 52.511, P10 41.096, P90 68.589. A diferença frente ao total determinístico 53.106 é decorrente da amostra finita da simulação, não de votos novos. O intervalo parecido com o V13 não comprova calibração. Conforme a apuração avança, o motor usa os votos observados e corrige o restante pelo ritmo municipal, com regularização inicial de 3 mil votos.

Superar as referências de 24.800 e 38.329 votos não equivale a ser eleita. As chances exibidas são frequências condicionais do simulador, sem validação temporal de cobertura; vagas exigem também resultados e regras dos partidos. O ensaio da Bruna é sintético. Abigail e Eric usam votos históricos de 2022, mas testar contra a mesma base não é um backtest independente de uma projeção anterior.

## Correções e testes

Foram reproduzidos problemas: votos negativos, municípios duplicados e apuração acima de 100% eram aceitos. O motor agora rejeita essas entradas, valores não finitos, previsão vazia, municípios desconhecidos e parâmetros inválidos. O painel interrompe a projeção com mensagem clara em vez de mostrar números inválidos. Municípios ainda sem retorno do TSE preservam a projeção inicial.

Onze testes automatizados passaram com o CSV real e cenários artificiais: qualidade da base, saída inicial preservada, fechamento igual aos votos contados, reprodutibilidade parcial, projeção não inferior ao contado, municípios sem retorno e rejeição das entradas inválidas. São testes de integridade, não prova de acerto eleitoral.

Reprodução: `python -m unittest discover -s apuracao -p 'test_projecao_deputados.py' -v`.

## Pendências para validação preditiva

Seriam necessários históricos de previsões efetivamente produzidas antes de eleições, resultados posteriores comparáveis, datas das entradas e dados completos para reconstruir o pipeline sem informações futuras. O repositório depende de arquivos externos em `C:/modelo_bruna/dados_tse` e da planilha de campo para reconstrução integral. A projeção atual não deve ser apresentada como de alta confiabilidade comprovada. Os dados importados e as premissas foram preservados; não há fundamento validado para substituir 53.106 por outro total nesta revisão.
