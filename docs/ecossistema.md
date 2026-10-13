# Ecossistema — o que é deste sistema, o que é do assessor, o que corre em paralelo

> Decisão: [ADR-007](decisoes/007-escopo-do-sistema.md)
> Este documento delimita o escopo. Quando outro documento contradisser, vale este.

## 1. Objetivo único deste sistema

**Executar o trabalho manual que sustenta os serviços de mídia paga do assessor** — coletar, conferir, calcular, devolver conversões às plataformas, montar os números e o material de apoio — para que o assessor gaste o tempo dele pensando, decidindo e se relacionando com o cliente.

O sistema **não pensa a estratégia** e **não fala com o cliente**.

## 2. As três colunas

| Assessor (humano) | Este sistema (Trilha) | Ferramentas paralelas (fora deste repositório) |
|---|---|---|
| Estratégia, decisões de verba, estrutura, criativo e oferta | **Raio-x do funil:** etapa por etapa, primeiro contato e cadência do time comercial do cliente, perdas por categoria, maior vazamento, marketing entregou × comercial converteu |  |
| Diagnóstico de aderência da oferta (responde as perguntas) | **Conversão real:** Kommo → Meta (API de Conversões) e Google (Data Manager API) | **BotConversa:** atendimento e fluxos no WhatsApp |
| **Contatos proativos** com o cliente (≥ 3 por semana) | **Coleta e monitoramento:** Meta, Google e Kommo; pacing; urgências; freio de emergência | **GA4 / GTM:** rastreamento do site e eventos |
| **Respostas no grupo do cliente** (≤ 2 h) | **Dossiê da otimização semanal** e execução do que o assessor aprovar | **Landing pages** |
| Sessão de otimização semanal (decide) | **Números do relatório semanal** ao cliente (leads · criativos · ações) | **Disparos em massa** |
| Relatório semanal: escreve os insights e apresenta | **Pacote de dados do briefing** de criativo | **Fluxos de CRM** no Kommo (incl. `build_kommo_json.py` do briefing-trilha) |
| Briefing de criativo: escreve a estratégia | **Pacote da reunião mensal** | **Captura de tarefas no ClickUp no mesmo dia** (n8n) |
| Reunião mensal: conduz | **Painel da carteira** para a reunião de equipe | **Onboarding** (wizard do briefing-trilha) |
| Alinhamento com a equipe | | |

## 3. O que este sistema precisa das ferramentas paralelas (contratos de interface)

O Trilha não constrói essas ferramentas, mas depende do que elas gravam. Sem isso, a conversão real e os relatórios ficam incompletos.

| Ferramenta paralela | Precisa entregar ao Trilha | Por quê |
|---|---|---|
| **Landing pages** | campos ocultos com `gclid`, `gbraid`, `wbraid`, `fbclid` e as 5 UTMs, gravados nos campos personalizados do lead no Kommo ([Kommo](integracoes/kommo.md) §4), mesmo quando o envio passa por um webhook intermediário (Make); payload com esquema fixo (todas as chaves, vazias quando não houver); telefone em E.164 sem duplicar o DDI; hora do clique (`capturado_em`); evento de lead só depois do recebimento confirmado, com `event_id` compartilhado com o servidor; botão de WhatsApp com código de criativo na mensagem pré-preenchida | sem o identificador de clique, a venda não volta para o Google/Meta; sem código no WhatsApp, o lead do botão chega sem atribuição |
| **BotConversa** | quando atender a conversa vinda de anúncio de clique para WhatsApp, repassar o `ctwa_clid` e as UTMs ao lead no Kommo; mover o lead nas etapas padronizadas | sem o `ctwa_clid`, a qualificação da conversa não volta para o Meta |
| **GA4 / GTM** | tag do Google e pixel do Meta funcionando nas páginas; eventos de conversão do site; `event_id` compartilhado entre pixel e servidor quando houver API de Conversões no site | o freio de emergência usa "horas sem evento de conversão"; deduplicação no Meta |
| **Fluxos de CRM (Kommo)** | funil com as etapas padrão; motivos de perda nativos do Kommo com a lista padrão, obrigatórios; responsável em todo lead; contatos registrados no Kommo ([raio-x do funil](raio-x-do-funil.md), contrato) | sem isso não há raio-x: não dá para saber onde está o vazamento nem de quem é a perda |
| **Captura de tarefas (n8n)** | tarefas no ClickUp com o cliente identificado (pasta do cliente) | painel da carteira lê tarefas atrasadas por pessoa |
| **Onboarding (briefing-trilha)** | `perfil.yaml`, `marca.yaml`, `ofertas/*.yaml` que passam no `python -m trilha validar` | contrato de dados ([ADR-005](decisoes/005-dependencia-briefing-trilha.md)) |

Mudou uma etapa no Kommo, um campo oculto da página ou o fluxo do BotConversa? Avisar quem cuida do Trilha: o mapa de eventos e o W01 precisam acompanhar.

### Ferramentas paralelas que já existem

| Ferramenta (repositório) | Relação com este sistema |
|---|---|
| Painéis de mensuração e relatórios por cliente | camada de relatório publicada para o cliente; devem seguir o mesmo [dicionário de métricas](metricas.md) para os números baterem |
| Painel de saúde da carteira | mesma função do painel da carteira; as regras de saúde das contas foram trazidas para cá (`saude.py`) |
| Ranking de corretores | painel de TV para o cliente; usa as mesmas ideias de leads parados e perfil comparativo |
| Rotinas de tags no Kommo (estado do bot, `Interagiu`) | automação de CRM (GitHub Actions por cliente, com simulação antes de gravar e log para desfazer); o raio-x lê as tags com os nomes reais ([Kommo](integracoes/kommo.md) §3.2) |
| Salesbots e fluxos do pré-atendimento (`briefing-trilha` e fluxos por cliente) | aplicam as tags e etapas que o raio-x lê (Interesse Confirmado, lead frio, não-cadastrou, reativado, bot-*) |
| Disparos (Mailchimp) | disparo em massa; fora do escopo |
| Landing pages ([Trilha-LP](https://github.com/davi-barbosap/Trilha-LP) e páginas anteriores feitas por cliente) | a Trilha-LP cumpre o contrato inteiro ([contrato](https://github.com/davi-barbosap/Trilha-LP/blob/main/docs/contrato.md)). Das páginas anteriores, a melhor cumpre a captura (UTMs, `gclid`, `gbraid`, `wbraid`, `fbclid`, esquema fixo, `generate_lead` só após o webhook confirmar). A regra real é "o último clique com campanha na sessão vence, e a navegação orgânica depois não apaga", guardada em `sessionStorage` (não atravessa sessões). Faltam `event_id` compartilhado, código de criativo no WhatsApp e Consent Mode. Há páginas antigas que não gravam identificadores de clique nem UTMs em campo próprio, ou nem enviam o lead: devem ser trocadas por páginas da Trilha-LP antes de receber verba |
| Briefing (`briefing-trilha`) | onboarding da oferta e fluxos do Kommo ([ADR-005](decisoes/005-dependencia-briefing-trilha.md)) |

Origem detalhada de cada padrão: [origem dos padrões](origem-dos-padroes.md).

## 4. Time comercial do cliente ≠ assessor

O sistema **mede** o time comercial do cliente (corretores, atendentes) atendendo os leads: primeiro contato, cadência, conversão. Isso é o raio-x do funil. O sistema **não mede** o contato do assessor com o cliente (contatos proativos, respostas no grupo).

## 5. Fora do escopo, de propósito

- Construir landing pages, disparos em massa ou fluxos de CRM/atendimento.
- Medir ou cobrar tempo de resposta e contatos do assessor com o cliente.
- Escrever mensagens ao cliente, roteiros, peças criativas ou a estratégia de um briefing.
- Prospecção comercial da agência. (A calculadora de economia unitária pode ser usada nisso, mas como uso paralelo; aqui ela serve para as metas de cada cliente.)
