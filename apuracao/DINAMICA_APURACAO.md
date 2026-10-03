# Dinâmica e histórico da apuração

A interface registra votos novos, marcos de percentual, mudanças de liderança entre candidatos acompanhados e revisões. Mostra diferença de votos, evolução das projeções, relógio da consulta, contagem aproximada de 90 segundos e modo telão. Não modifica o motor nem incorpora o PR #2.

Histórico oficial compartilhado no servidor em SQLite, com até 960 snapshots por disputa/turno/modo; gráficos usam os últimos 120, linha do tempo os últimos 30 eventos. Duplicatas por timestamp são ignoradas. Fecha e reabre o navegador sem perder o histórico existente no servidor. Ensaio permanece separado por sessão. Caminho configurável via APURACAO_HISTORICO_DB; padrão /tmp/eleicoes2026_historico.sqlite3. Render gratuito usa armazenamento efêmero: restart/deploy pode apagar o histórico. Sobrevivência a restart exige volume persistente ou armazenamento externo; não foi contratado ou ativado recurso pago.

Selos de eleito/segundo turno somente com situação textual do TSE; totalizado somente com flag oficial. Votos/projeções/100% não inferem esses selos. Ensaio rotulado explicitamente. Falha de SQLite não derruba placares e usa memória de sessão. Falha na fonte mostra último resumo disponível, com horário. Horário é da consulta do servidor, não da totalização do TSE.

Validação: compilação e seis testes automatizados em Streamlit 1.62.0: cache, deltas, revisões negativas, limites, interface/gráficos/telão, 0–100%, virada, recuperação sem sessão, concorrência e deduplicação, selos sem inferência e falha de conexão. Comando: python -m unittest apuracao.test_dinamica apuracao.test_historico_servidor -v. CSS de telão inclui limite de tamanho para telas estreitas; teste automatizado de interface não substitui inspeção visual em celular real.
