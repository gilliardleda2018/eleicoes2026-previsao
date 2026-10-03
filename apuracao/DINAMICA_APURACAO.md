# Dinâmica da apuração

A interface acompanha votos novos, percentual apurado, marcos de 25/50/75/100%, mudanças de liderança entre candidatos acompanhados e revisões da fonte. Inclui gráficos da diferença de votos e da estimativa final com as faixas existentes do modelo, relógio da consulta e contagem aproximada da próxima verificação. O modo telão amplia os placares.

Histórico em memória por sessão, disputa, turno e modo, limitado a 120 consultas e 30 eventos. Não reconstrói o passado anterior à abertura da sessão; recarregar reinicia o histórico. Consultas em cache não criam pontos duplicados. O horário mostrado é da consulta do servidor, não o horário de totalização do TSE. Contagem de 90 segundos é aproximada e não garante resposta da fonte. Falhas preservam e identificam o último resumo bem-sucedido desta sessão.

Não altera o motor, modelos, bases ou pesos; não incorpora o PR #2. Rankings acompanham os seis nomes exibidos no resumo dinâmico. Projeções ficam restritas às disputas com modelo já existente. Eventos de liderança não declaram eleição ou vitória oficial.

Validação: compilação dos dois arquivos e dois testes automatizados (registro/cache/revisões/limites e interface Streamlit com dois gráficos e modo telão). Comando: `python -m unittest apuracao.test_dinamica -v`.
