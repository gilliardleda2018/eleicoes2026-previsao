# O que mudou em Tuntum?

Cartão local nas páginas de presidente, governador MA e Assembleia MA. Compara candidatos acompanhados entre duas consultas: liderança local, deltas, revisões negativas, diferença em votos por par e percentual de seções do município. Não declara eleição nem altera projeções/modelos. Mesma identidade prata amarelada, relevo e detalhe azul.

Deputados vêm da linha Tuntum da tabela já calculada; governador vem da linha municipal TSE; presidente reutiliza a consulta municipal existente. Ensaio presidencial não tem recorte local e mostra indisponibilidade, sem copiar dados do estado. Ensaios têm histórico separado por disputa/turno/sessão; oficiais usam SQLite compartilhado, sujeito à perda no reinício/deploy no Render gratuito. Consulta repetida não vira novo evento.

Validação: 17 testes de mudanças locais, integração de ensaio, editor, dinâmica e histórico passaram; painel e módulo compilam. Não implica validação das probabilidades eleitorais.
