# Ensaio do contrato de inferência

Somente o modo Ensaio exibe o teste. O painel coleta dados; SageMaker não consulta TSE por conta própria. A futura integração enviará IDs, volume de mudanças e indicador de virada. A resposta deverá conter somente IDs e scores; textos e votos ficam locais.

Este teste não invoca AWS nem usa modelo treinado: o transporte é simulado e mantém a ordem das regras. Cenários Normal, Timeout e Resposta inválida verificam validação e retorno às regras. Não altera probabilidades, projeções ou votos. Modo oficial não importa nem exibe o simulador.

12 testes de interface/histórico/contrato passaram. Teste adicional confirmou ausência do simulador no modo oficial. Senado/deputado federal não enviam mudanças por município neste painel; o teste valida resposta vazia e o resumo global continua pelas regras.

Para dados oficiais em 04/10: coleta atual do painel continua disponível. Ranking real via AWS depende de endpoint, modelo validado, gateway com contador global e orçamento. Não está ativado e não há promessa de ativação automática amanhã.
