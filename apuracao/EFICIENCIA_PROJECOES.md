# Avaliação das projeções durante a apuração

Expander nas disputas com projeções: presidente, governador e Assembleia. Senado/federal não têm modelos de projeção neste painel. Mostra variação absoluta da estimativa central entre consultas, largura da faixa e tempo local do cálculo (sem coleta/rede/AWS).

Erro e cobertura somente com referência final: ensaio em 100%, ou totalizado=True informado pelo TSE. Para deputados, referência em votos dos candidatos acompanhados; duelos, percentuais dos válidos no mesmo recorte de unidades do painel (exterior não incluído na projeção estadual). Não usa soma de votos dos dois candidatos como denominador.

Exclui consultas em 100% ou posteriores da avaliação de erro para não contar a previsão que já conhece o final. Erro médio absoluto por candidato, cobertura descritiva de suas faixas e erro da primeira projeção registrada. Consultas são correlacionadas: não é backtest independente nem calibração histórica. O ensaio pode reutilizar dados utilizados pelos modelos; não prova precisão para 2026. Não compara separadamente cada algoritmo do agregado nem valida probabilidades de vitória.

21 testes de eficiência, cartões Tuntum, ensaio de inferência, editor, dinâmica e histórico passaram; módulo/painel compilam. Retenção sujeita ao SQLite efêmero do Render. Custo/latência de inferência AWS indisponíveis; não inventa medições. Não altera previsões, pesos, algoritmos ou motor.
