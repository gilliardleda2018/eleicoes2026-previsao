# Correções e retreinamento nacional — 2 de outubro de 2026

Base do repositório: `facc9a474deeda4504a928cbba0f082f43015a1b`. Corte de campo: 2026-10-02. Alterações limitadas à pasta `nacional/`. Não houve mudança de dependências, autenticação, apuração ao vivo, modelo MA ou configuração de deploy.

## Dados e execução real

A base de 27 UFs foi reconstruída a partir dos JSONs TSE de 2022 já versionados e do CSV 2018; as validações de conclusão da apuração, conservação de votos e unicidade passaram. O conteúdo numérico da base permaneceu igual. As entradas originais foram preservadas.

Das 281 linhas de pesquisas, foram usadas 50 de primeiro turno e 51 de segundo turno. Somente `status=confirmada` foi aceito. Cinco linhas confirmadas de primeiro turno foram excluídas por total incompatível; lista e fontes em `resultados/pesquisas_excluidas.csv`. Status confirmado é uma classificação da base, não uma nova auditoria independente das fontes.

A base registra que `indecisos` inclui brancos/nulos quando `brancos_nulos` está vazio. O denominador do primeiro turno passou a ser 100 menos essas respostas. Exigimos conservação do total dentro de dois pontos por arredondamento. Ausências dos demais candidatos continuam ausentes; valores censurados como `<1` recebem ponto médio do intervalo, hipótese explícita usada para conferência do total. Não foram inventadas pesquisas, resultados ou datas de publicação.

Foram ajustados os seis agregadores reais existentes no projeto e os cinco modelos geográficos em 27 UFs. A validação espacial deixou cada região fora do treinamento. Modelos com erro superior à persistência de 2018 recebem peso zero na geografia:

| Modelo | MAE espacial (pontos) | Peso |
|---|---:|---:|
| Regressão linear | 3,57 | 48,5% |
| Ridge | 3,01 | 51,5% |
| Random Forest | 10,38 | 0% |
| Gradient Boosting | 8,02 | 0% |
| KNN | 9,51 | 0% |
| Referência: persistência de 2018 | 4,59 | referência |

A média ponderada dos erros individuais é 3,28 pontos. Isso não é uma avaliação temporal independente do ensemble: os pesos foram escolhidos na mesma validação espacial. Cinco modelos continuam sendo treinados; apenas dois contribuíram nesta execução.

## Saída do modelo revisado

20.000 simulações nacionais, 5.000 estaduais, 44 pares para transferência implícita. Probabilidades condicionadas à hipótese de vitória de Lula ou Flávio:

- Lula presidente: 37,9%.
- Flávio presidente: 62,1%.
- Segundo turno: 99,7%.
- Segundo turno, Lula: mediana de 49,4% dos válidos, P10 46,9%, P90 51,9%.

Esses números descrevem as premissas do modelo. Não são votos apurados, garantia de acerto, recomendação de voto ou consenso de IAs.

## Correções

- Corte temporal no histórico (zero a dez dias antes), nas pesquisas nacionais e nos recortes; suporte a data de divulgação quando disponível.
- Validação de percentuais, amostras, denominadores e contagem TSE.
- Pareamento um-para-um de pesquisas para transferência; distribuição empírica substitui Beta por momentos.
- Falta de pares: fallback explícito para pesquisas diretas; ausência de ambas as fontes interrompe a geração.
- Vitória no primeiro turno exige mais de 50%; NaN, infinito e empates exatos não geram probabilidades inválidas silenciosamente.
- Primeiro turno converte o erro histórico da base dos dois candidatos para todos os votos válidos antes de aplicar o deslocamento.
- Segundo turno principal usa erros históricos do próprio turno; o erro antecipado de 2022 fica no alerta. Esta troca de premissa exige avaliação temporal mais extensa.
- Calibração estadual exige convergência. Apoio de governadores e recortes redistribuem votos e não mudam a probabilidade nacional.
- JSON estrito com escrita atômica por arquivo; o conjunto completo de saídas ainda não é uma transação única.
- Painel informa limites, favorito dinâmico, P10/P90 e transferência implícita. Testes usam execução real das seções e dos sliders.

## Testes

- Compilação de todos os arquivos nacionais e `git diff --check`: passaram.
- 14 testes automatizados: passaram, incluindo as dez seções do painel e alterações dos dois sliders de cenários.
- Integração sintética: passou, inclusive conservação, fallback, reprodutibilidade e efeitos estaduais.
- Reexecução real dos agregadores e do Monte Carlo: saídas reprodutíveis. Reexecução final do Monte Carlo: mesmos hashes.
- Os requisitos fixados no repositório foram instalados para os testes; não foram editados. Ambiente e hashes registrados em `resultados/manifesto_validacao.json`.
- Processo gaussiano emitiu aviso de limite inferior do comprimento de escala, sem falha. Não houve busca de novos hiperparâmetros para melhorar artificialmente os testes.
- Testes Streamlit verificam execução e elementos; não equivalem a revisão visual manual de todos os gráficos em navegador.

## Backtest temporal parcial

`backtest_historico_real.py` testa 2014, 2018 e 2022 usando correções aprendidas exclusivamente em eleições anteriores. Usa a média das pesquisas finais, uma por instituto; não reproduz os seis agregadores nem o horizonte anterior ao primeiro turno de 2026. As datas disponíveis são de campo, não de publicação.

| Variante | Brier (menor é melhor) | MAE de votação | Cobertura da faixa de 80% |
|---|---:|---:|---:|
| Sem correção | 0,00938 | 0,912 ponto | 66,7% |
| Correção histórica | 0,01664 | 0,952 ponto | 66,7% |

A correção histórica não melhorou estas métricas. São só três eleições: não comprovam calibração ou alta confiabilidade. O backtest completo do pipeline de 2026, com históricos de simulações antecipadas de vários ciclos e datas de divulgação, continua pendente.

## Reproduzir

```bash
pip install -r requirements-modelos.txt
MODELO_DATA_CORTE=2026-10-02 python nacional/preparar_base_nacional.py
MODELO_DATA_CORTE=2026-10-02 python nacional/modelos_pesquisas_nacional.py
MODELO_DATA_CORTE=2026-10-02 python nacional/modelo_ufs_mc.py
python nacional/backtest_historico_real.py
python -m unittest discover -s nacional -p 'test_*.py' -v
python nacional/test_integracao_sintetica.py
```

Limites remanescentes: exterior excluído, pesos eleitorais de 2022, crescimento uniforme de 3%, duas candidaturas com vitória modelada, mistura 50/50 e persistência uniforme de erros não calibradas temporalmente. Publicação automática do Render usa `main`; esta revisão foi preparada em branch separada para não alterar produção durante os testes.
