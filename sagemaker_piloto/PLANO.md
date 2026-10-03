# Piloto SageMaker: preparação, ainda não ativado

Autorização em 03/10/2026: conta 614471945241, orçamento máximo US$ 50,
sete dias começando em 03/10, encerramento em 10/10 no horário da ativação
(America/Fortaleza). Se não houver ativação em 03/10, não estender o período
sem alinhar com o usuário. Região proposta: us-east-1.

## Estado verificado

Atualização após reconexão em 03/10: as conexões personal (nova) e AWS Core
retornaram identidade root da conta 614471945241. ListEndpoints funcionou em
us-east-1 e retornou zero endpoints. A conexão Primary continua no auditor.
O bloqueio anterior foi superado na nova conexão; não indica que o piloto
esteja ativo.

Foi criada e relida a role dedicada:
arn:aws:iam::614471945241:role/eleicoes2026/AggilliEleicoes2026SageMakerExecution

Trust restrito ao serviço SageMaker, conta, região e recursos com nome
contendo eleicoes2026. Verificadas zero políticas inline e zero políticas
anexadas: ainda não há acesso a artefatos, imagens ou logs. Esta role não é
uma identidade de operador e não substitui a conexão root. Não foi criada
chave de acesso. Tags de data e orçamento são documentação, não desligamento
nem limite financeiro. Nenhum recurso dos outros projetos foi alterado.

GetProducts (AmazonSageMaker) confirmou tarifa de 2 GB em us-east-1:
US$ 0,0000400000 por segundo; SKU WRGJQXV26JHS9764, publicação 03/10/2026.
O custo dos demais componentes continua pendente.

### Registro da conexão anterior

A conexão Primary usa personal-assistant-dai-auditor. ListEndpoints e
SimulatePrincipalPolicy foram negados pela permissions boundary em 03/10.
Não houve criação de recursos, treino ou integração com o painel. Não alterar
as políticas DAI nem os recursos personal_assistant para liberar este projeto.
É necessária uma conexão/role dedicada ao projeto eleitoral com acesso
compatível, incluindo desligamento, e IAM PassRole restrito à execução.

## Objetivo e validação

Priorizar destaques factuais da apuração de presidente, governador, deputados
e senador. Não prever vencedor, alterar votos/probabilidades, recomendar
apostas ou inferir preferências políticas de pessoas. Textos ficam locais.
O endpoint só poderá retornar scores para IDs enviados.

O editor atual usa regras; não existe ainda um recomendador treinado e
validado. Faltam exemplos reais rotulados de relevância editorial. Antes do
treino: coletar mudanças públicas oficiais, anotar relevância, separar treino
e teste por tempo/eleição, comparar ranking com as regras atuais (NDCG@5,
precisão dos cinco destaques e latência). Dados de ensaio servem apenas para
testar o funcionamento. Não apresentar imitação das regras como melhora
comprovada de ML. Manter regras atuais durante coleta e teste em paralelo.

contrato.py não é um cliente AWS. Valida respostas, expiração e retorno às
regras; está isolado e não é importado pelo painel. Nenhuma dependência mudou.

## Custos e proteção a implementar antes da ativação

Preferir Serverless Inference sem provisioned concurrency, 2 GB e
MaxConcurrency=1. Sem notebook ligado, endpoint em instância permanente ou
treino recorrente. A página oficial apresenta US$ 0,00004/segundo para 2 GB:
https://aws.amazon.com/sagemaker/ai/pricing/

Cenário conservador de computação: 5.000 chamadas x 60 segundos x 0,00004 =
US$ 12; sobra uma reserva de US$ 38 dentro do teto autorizado. Isso não é
cotação total: treinamento, inicialização, armazenamento, logs, transferência
e outros serviços precisam ser precificados na região antes de criar recursos.
Não contar com créditos/free tier. A latência real precisa ser medida.

Não existe garantia de teto financeiro apenas com AWS Budgets, pois a
contabilização e alertas têm atraso. A autorização não permite ultrapassar
US$ 50: se o custo máximo do desenho não puder ser limitado, não ativar.

Pré-requisitos operacionais:
- Confirmar preço regional e cotas; registrar orçamento incluindo recursos auxiliares.
- Limitar invocações em um único gateway com contador global atômico persistente;
  cache por atualização oficial, limite absoluto de 5.000 e rate limit.
  Não usar contador de sessão Streamlit como teto global.
- Bloquear chamadas sem aprovação de modelo, prazo válido e reserva disponível.
- Congelar ativação e expiração em armazenamento persistente; não renová-las
  no reinício/deploy. Expiração também verificada em cada chamada.
- Criar e verificar desligamento programado independente do Render antes de
  criar endpoint. Remover endpoint no vencimento, parar jobs e conferir limpeza
  de model/config, objetos e logs dedicados. Só apagar recursos deste piloto.
- Alertas antecipados em US$ 10, 20 e 30; interromper operações ao atingir US$ 30
  contabilizados, mantendo reserva para atrasos. Alertas não substituem limites.
- Timeouts e resposta inválida mantêm ranking local. Não exigir AWS para abrir
  o painel. Guardar credenciais apenas em configuração segura do servidor.

## Testes da preparação

python -m unittest sagemaker_piloto.test_contrato -v

Quatro testes: início/fim exato dos sete dias, preservação do conteúdo,
fallback por prazo/limite e rejeição de IDs inválidos, duplicados, NaN ou texto
extra. Não comprovam qualidade de um modelo nem desligamento real na AWS.

## Próximas etapas ainda pendentes

A nova conexão superou o bloqueio de acesso. Preparar permissões mínimas dos
recursos dedicados, infraestrutura de limite/desligamento e dataset rotulado;
estimar custo total e testar em paralelo antes de ativar. Não há endpoint ou job para
desligar nesta preparação. O desligamento já foi agendado, conforme abaixo.

## Avanço de 03/10 após autorização para concluir

Criados grupo Scheduler eleicoes2026-piloto e role
arn:aws:iam::614471945241:role/eleicoes2026/AggilliEleicoes2026PilotShutdown.
Criado e relido o agendamento ENABLED:
arn:aws:scheduler:us-east-1:614471945241:schedule/eleicoes2026-piloto/eleicoes2026-desligar-20261010

Deadline fixo: 10/10/2026 às 11:31:34 America/Fortaleza. O período operacional
será menor que sete dias se a ativação ocorrer mais tarde. Target universal
sagemaker:deleteEndpoint, exclusivamente eleicoes2026-editor-piloto. Janela
flexível OFF; até três retries, idade máxima uma hora. A simulação IAM
confirmou allowed para este endpoint e implicitDeny para outro-projeto.
Isso verifica configuração e política, não uma execução real bem-sucedida.
Ainda faltam testar a entrega, monitorar falha de desligamento e limpar
artefatos/logs. Se o endpoint não for criado, a chamada encontrará recurso
inexistente; cancelar o agendamento se o piloto for abandonado.

Implementados dataset.py (SQLite somente leitura, mudanças por unidade,
revisões e viradas, rótulos inicialmente vazios) e treinar.py (Gradient
Boosting, corte temporal global sem dividir grupos, NDCG@5 contra regras).
Exige pelo menos 30 grupos, cinco datas e cinco grupos de teste comparáveis;
exporta artefato só com melhoria superior a 0,02. Estes números são gates
iniciais de engenharia, não garantia estatística. Revisão humana e teste em
paralelo continuam necessários. Dependências separadas espelham o ambiente
local; as dependências do Render não mudaram.

Sete testes de contrato/dataset passaram. Também confirmado: validar([])
recusa treino. Os únicos três snapshots locais têm tempos 1, 2 e 3, votos
A/B e nenhuma unidade: são fixtures de testes, não dados oficiais. Não foram
usados para treinar ou demonstrar qualidade. Chave *_False é filtro operacional,
não prova independente de origem; certificar fontes antes do treino.

Comandos:
python -m sagemaker_piloto.dataset BANCO_OFICIAL.sqlite3 rotulagem.jsonl
python -m sagemaker_piloto.treinar rotulagem_preenchida.jsonl artefato_novo
python -m unittest sagemaker_piloto.test_contrato sagemaker_piloto.test_dataset -v

Bloqueios restantes: dados reais de mudanças rotulados, teste de qualidade,
cliente/gateway com contador global persistente, orçamento total fechado,
alertas e ligação com Render. Não foi ativada inferência paga. Não houve
retreino de Bruna, alteração de motor ou modelos nacionais.
