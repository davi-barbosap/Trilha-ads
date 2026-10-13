# n8n — orquestração da operação

> Decisão: [ADR-002](../decisoes/002-n8n-orquestrador.md) · Quem faz o quê: [modelo operacional](../modelo-operacional.md) · Escopo: [ecossistema](../ecossistema.md)
> Infra: [`infra/`](../../infra/) · Fluxos-modelo escritos à mão: [`n8n/modelos/`](../../n8n/modelos/) · Fluxos em produção (exportação diária): `n8n/fluxos/` · Núcleo chamado pelos fluxos: `trilha/api.py`
> Versão-alvo: **n8n 2.x** autohospedado.

## 1. Arquitetura

```
                 ┌──────────────────────────── n8n 2.x (modo fila: principal + worker) ─────────────────────────┐
Kommo webhook ──►│ W01 Conversão real ───────────► POST /conversao ──┐                                            │
Agendador ──────►│ W02 Coleta   W03 Urgências+freio ─► /freio/avaliar ├──► trilha-api (rede interna, sem porta      │
                 │ W04 Pacing   W05 Leitura diária                    │     pública): perfil, metas, hash, payloads, │
ClickUp gatilho ►│ W06 Execução do aprovado ──────► /calcular ───────┘     regras do freio, segredo por cliente      │
                 │ W07 Relatório semanal (números)   W08 Pacote de briefing                                          │
                 │ W10 Vigia de falhas   W11 Pacote da reunião   W12 Dossiê de otimização   W14 Painel da carteira   │
                 └───────────────┬────────────────────────────────────────────────────────────────────────────────┘
                                 ▼
          ClickUp (dossiês, relatórios, pacotes) · Slack (urgências, freio, falhas) · Postgres · BigQuery → Looker Studio
```

Regra de divisão (ADR-002): erro que custa dinheiro ou expõe dado pessoal → trilha-api, com teste. Erro que só atrasa uma entrega → pode ficar no n8n.

**Na mesma instância, mas fora deste sistema** ([ecossistema](../ecossistema.md)): a automação paralela de captura de tarefas no ClickUp no mesmo dia pode rodar no mesmo n8n, como projeto separado, sem depender da trilha-api.

## 2. Mapa de fluxos

Cada fluxo é **um só para toda a carteira**: pede a lista de clientes à trilha-api (`GET /clientes`) e percorre cada um. Nunca copiar fluxo por cliente.

| Fluxo | Serve a | Disparo | Faz | Status |
|---|---|---|---|---|
| **W01** Conversão real | base de tudo | webhook do Kommo `…/webhook/kommo/<cliente_id>?token=<segredo do cliente>` | responde 200 ao Kommo na hora; chama `/conversao`, que confere o segredo do cliente, a conta Kommo e a etapa real do lead; avisa no Slack se algo foi pulado | ✅ modelo (`n8n/modelos/w01-conversao-real.json`) |
| **W02** Coleta | dossiê, relatório, pacotes | diário 05:00 | Meta Insights (por conjunto e anúncio, diário, `time_increment=1`, em janelas mensais por causa do erro de paginação #2642; status dos anúncios; objetivo da campanha para separar captação, topo de funil e clique para WhatsApp) + Google (GAQL por campanha e dia, `cost_micros` ÷ 1e6; o Performance Max não tem grupo de anúncios) + Kommo por cliente (leads, histórico de etapas, primeiro contato humano, tarefas de reunião, tags) → BigQuery; leads do período e vendas fechadas no período em todos os funis cadastrados; correções confirmadas do cliente aplicadas; falha alto em qualquer erro de qualquer fonte, trava de sanidade antes de gravar, data de coleta por fonte, nunca publica "zero" ([Kommo](kommo.md) §3.3) | ⬜ |
| **W03** Urgências + freio | freio de emergência | a cada 2 h, 07–23 h, todos os dias | métricas do dia → `/freio/avaliar` → pausa (modo A) ou só avisa (modo B) → Slack com desfazer; também: gasto zerado, entrega parada, reprovação, conta desativada e saldo pré-pago para menos de 5 dias (`/contas/saude`) | ⬜ (regra pronta na API) |
| **W04** Pacing | dossiê | diário 06:00 | projeção do gasto do mês × verba contratada | ⬜ |
| **W05** Leitura diária | assessor | dias úteis 07:30 | a carteira em 5 linhas por cliente no Slack, escrita a partir dos números já calculados | ⬜ |
| **W06** Execução do aprovado | otimização semanal | gatilho do ClickUp (status → "Aprovado") | confere se a conta ainda está no estado "antes", executa a mudança simples aprovada, registra, comenta o resultado | ⬜ |
| **W07** Relatório semanal | relatório ao cliente | véspera de `operacao.dia_relatorio`, 16:00 | números e gráficos em três blocos (leads · criativos · ações) → tarefa no ClickUp. **Não envia nada ao cliente.** | ⬜ |
| **W08** Pacote de briefing | briefing de criativo | com o dossiê e sob demanda (status no ClickUp) | o que converte e o que cansou, objeções e motivos de perda, modelo de briefing pré-preenchido | ⬜ |
| **W10** Vigia de falhas | todos | fluxo de erro global | toda falha vira aviso no Slack com etapa, erro e link da execução | ✅ modelo (`n8n/modelos/w10-vigia-de-falhas.json`) |
| **W11** Pacote da reunião | reunião mensal | 2 dias úteis antes da reunião | resultado × meta vigente, testes, decisões e efeito, números para a proposta → documento no ClickUp/Drive | ⬜ |
| **W12** Dossiê de otimização | otimização semanal | véspera de `operacao.dia_otimizacao`, 16:00 | placar, mudanças, decisões anteriores e efeito, pontos de atenção com simulação, testes, freio, funil do cliente → tarefa no ClickUp | ⬜ |
| **W14** Painel da carteira | alinhamento com a equipe | véspera da reunião de equipe | semáforo por cliente, saúde das contas (dias de saldo, recarga sugerida, anúncios com problema), leads parados numa janela fixa de 45 dias, freio da semana, tarefas atrasadas e criativos pendentes (ClickUp), tokens perto de vencer; confere o **conteúdo** de cada material e coleta, não só se o fluxo terminou (coleta com zero leads quando o período anterior teve, plataforma sem dado, material com mais de 7 dias); alertas técnicos para o responsável técnico, agrupados | ⬜ |

Números W09 e W13 ficaram livres: pertenciam ao onboarding e à ata→tarefas, que hoje são ferramentas paralelas.

**Prioridade de construção:** ver [roadmap](../roadmap.md).

## 3. Volume e custo (8 clientes, ~300 leads/mês cada)

| Fluxo | Execuções/mês |
|---|---|
| W01 (uma por evento do Kommo) | 7.000–10.000 |
| W06 (o gatilho do ClickUp dispara em toda atualização de tarefa) | 1.000–3.000 |
| W10 | ~750 |
| W03 | ~270 |
| Demais (W02, W04, W05, W07, W08, W11, W12, W14) | < 300 |
| **Total** | **~9–14 mil** |

Com fluxos copiados por cliente, o total passaria de 12 mil só nos fluxos agendados — mais um motivo para o desenho em laço.

| Item | Mensal estimado |
|---|---|
| Servidor (4 vCPU / 8 GB) com n8n, worker, Redis, Postgres, Caddy | R$ 100–300 |
| BigQuery + Looker Studio | R$ 0–50 |
| API do Claude (W05, W07, W08, W11, W12: ~300 chamadas de ~6 mil tokens, só para organizar texto a partir de números prontos) | dezenas de dólares — conferir tabela vigente |
| Backups externos e monitoramento | R$ 0–50 |
| **Total** | **~R$ 300–800** |

## 4. Os dez requisitos de operação profissional

1. **Fluxos com parâmetros, nunca copiados por cliente.**
2. **Credenciais organizadas:** Meta — um usuário do sistema por Business Manager, token sem expiração, permissão de escrita só se o freio estiver no modo A; Google — uma credencial na MCC para a Google Ads API (coleta e alterações) e OAuth com escopo da Data Manager API (conversões offline), **app OAuth publicado em produção** (em modo "teste" o token de atualização expira em 7 dias); Kommo — **um par por cliente** em `infra/kommo.env`: token da API e segredo do webhook, nunca reutilizados entre clientes (o admin do Kommo de cada cliente enxerga a URL do webhook). Validade registrada e avisada no W14.
3. **Fluxo de erro global:** todo fluxo aponta para o W10 em *Settings → Error workflow*.
4. **Vigia externo:** um serviço fora do servidor (ex.: monitor de "batimento") recebe um ping ao fim do W02 e do W03; sem ping no horário, avisa. O n8n não consegue avisar que ele mesmo caiu.
5. **LGPD no histórico de execuções:** `EXECUTIONS_DATA_SAVE_ON_SUCCESS=none`, limpeza após 7 dias, e dados pessoais tratados só na trilha-api (o W01 nunca vê telefone ou e-mail).
6. **Versionamento:** `infra/backup.sh` exporta todos os fluxos para `n8n/fluxos/` e faz commit todo dia (o Git nativo do n8n é recurso pago).
7. **Ambiente de teste:** segunda instância (ou outra porta) ligada a uma conta de teste do Kommo e ao `META_TEST_EVENT_CODE`; `TRILHA_SIMULAR=1` até o primeiro evento aparecer certo no Gerenciador de Eventos.
8. **Modo fila com Redis** para absorver rajadas de webhooks (importações de leads no Kommo).
9. **Webhooks protegidos:** segredo próprio de cada cliente na URL do Kommo, conferido na trilha-api junto com a conta Kommo do corpo; a etapa é confirmada lendo o lead no Kommo (webhook forjado não vira conversão); assinatura do ClickUp conferida no W06; HTTPS pelo Caddy; trilha-api sem porta pública.
10. **Runbook:** a §6 deste documento, mantida junto com cada fluxo novo.

## 5. Segurança: variáveis de ambiente e credenciais

No n8n 2.x, `N8N_BLOCK_ENV_ACCESS_IN_NODE` vem como `true` (nós não leem variáveis de ambiente). O `infra/docker-compose.yml` libera `$env` apenas para configuração de baixo risco: `TRILHA_API_URL` (endereço interno) e `SLACK_WEBHOOK_URL`. O token da trilha-api fica numa **credencial "Header Auth"** do n8n (`Authorization: Bearer …`), criptografada com a `N8N_ENCRYPTION_KEY`. Com o acesso liberado, qualquer pessoa que edite fluxos pode ler essas duas variáveis: manter a edição restrita à equipe técnica.

## 6. Runbook

| Sintoma | Onde olhar | Ação |
|---|---|---|
| Aviso do W10 no Slack | link da execução no aviso | ler a etapa e o erro; 401/403 = credencial; 429 = limite da API (o fluxo tenta de novo); 5xx = indisponibilidade da plataforma |
| W01 avisa "lead sem identificador" com frequência | campos `gclid`/`fbclid`/`ctwa_clid` no Kommo do cliente | acionar quem cuida das landing pages, do GTM e do BotConversa: o contrato de interface não está sendo cumprido ([ecossistema](../ecossistema.md) §5) |
| W01 avisa "etapa não confirmada no Kommo" | etapa atual do lead no Kommo | normal se o lead mudou de etapa em segundos; frequente = alguém está movendo leads em massa ou o webhook está forjado (W10 mostra 403 em tentativas recusadas) |
| `/conversao` responde 403 | aviso do W10 | segredo errado na URL do Kommo daquele cliente, ou chamada vinda de outra conta Kommo |
| W01 avisa "perfil sem …" | `perfil.yaml` do cliente em `trilha-clientes` | completar o bloco e rodar `python -m trilha validar` |
| Evento desconhecido do Kommo (etapa nova) | `crm.mapa_eventos` | o cliente criou/renomeou etapa: atualizar o mapa |
| Sem leitura diária (W05) às 08h | vigia externo / `docker compose ps` | reiniciar o serviço; se o banco caiu, restaurar do backup |
| Freio pausou campanha | aviso no Slack | decidir na hora (desfazer) ou na sessão semanal; nunca deixar sem decisão até a sessão |
| Token do Kommo expirando (W14) | painel da carteira | gerar novo token na conta do cliente e atualizar `infra/kommo.env`; reiniciar a trilha-api |
| Restaurar do zero | `infra/backup/` + `N8N_ENCRYPTION_KEY` guardada fora do servidor | subir o compose, restaurar o `pg_dump`, conferir credenciais |

## 7. Importar os fluxos-modelo

1. Criar a credencial **Header Auth** "trilha-api" (`Authorization` = `Bearer <TRILHA_API_TOKEN>`).
2. Importar `n8n/modelos/w10-vigia-de-falhas.json` primeiro; anotar o ID gerado.
3. Importar `n8n/modelos/w01-conversao-real.json`; no nó "trilha-api /conversao", selecionar a credencial; em *Settings → Error workflow*, apontar para o W10 (o arquivo traz o marcador `DEFINIR_ID_DO_W10_APOS_IMPORTAR`).
4. Para cada cliente: gerar um segredo longo e aleatório, gravar como `KOMMO_WEBHOOK_TOKEN_<CLIENTE>` em `infra/kommo.env` e cadastrar no Kommo dele o webhook `https://<dominio>/webhook/kommo/<cliente_id>?token=<segredo>` para lead criado e mudança de etapa.
5. Testar com `TRILHA_SIMULAR=1`: mover um lead de teste e conferir a execução e a resposta da trilha-api.

Depois do primeiro backup, os fluxos em produção aparecem em `n8n/fluxos/` (nomeados pelo nome do fluxo); `n8n/modelos/` continua sendo o ponto de partida para instalações novas. Os modelos seguem o formato de exportação do n8n, mas **ainda não foram importados numa instância real**: conferir tipo e versão de cada nó ao importar.
