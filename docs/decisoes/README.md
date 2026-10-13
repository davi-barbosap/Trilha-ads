# Decisões de arquitetura

Cada decisão estrutural é um arquivo curto: contexto, decisão, consequências. Mudar uma decisão = editar o arquivo dela (o histórico fica no Git).

| ADR | Decisão | Status |
|---|---|---|
| [001](001-armazenamento.md) | Postgres para eventos, alterações e decisões; BigQuery para histórico de mídia | aceita |
| [002](002-n8n-orquestrador.md) | n8n autohospedado como orquestrador; trilha-api como núcleo testado | aceita |
| [003](003-painel.md) | Looker Studio sobre BigQuery; Metabase como alternativa | aceita |
| [004](004-dados-de-clientes.md) | Dados de clientes fora do repositório de código | aceita |
| [005](005-cadastro-pelo-trilha-briefing.md) | O cadastro do cliente vem do Trilha-briefing, por contrato de dados | aceita |
| [006](006-freio-de-emergencia.md) | Freio de emergência como única ação automática | aceita |
| [007](007-escopo-do-sistema.md) | Escopo: execução manual dos serviços de mídia; o resto é paralelo | aceita |
| [008](008-funil-padrao.md) | Funil padrão único para todos os segmentos; perda classificada por etapa e motivo; resultado é venda | aceita |
