# Editor da apuração

Resumo e seleção factual por regras, sem SageMaker/Personalize ou despesas novas. Compara duas consultas consecutivas; registra votos positivos, revisões negativas, percentual e liderança entre candidatos acompanhados. Destaca até cinco locais: viradas primeiro, depois soma das variações absolutas de votos dos candidatos acompanhados; nome desempata. Empates não são tratados como mudança de líder. Novos locais sem baseline aguardam outra consulta.

Deputados MA: municípios. Presidente: UFs. Governador MA: municípios. Senado/federal: resumo dos seis candidatos acompanhados; não há detalhe municipal nesse fluxo. Snapshot de unidades fica no histórico compartilhado oficial existente. Ensaio separado por sessão, explicitamente rotulado. Não explica causalidade de mudanças de projeção nem declara resultado oficial. Modelos, dados, pesos e motor preservados; PR #2 não incorporado.

Validação: nove testes passaram (editor, dinâmica e histórico), incluindo virada, revisão, prioridade, início/sem mudanças, escape HTML, interface, simulação 0–100%, armazenamento e concorrência. Comando: python -m unittest apuracao.test_editor_apuracao apuracao.test_dinamica apuracao.test_historico_servidor -q.
