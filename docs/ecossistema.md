# Ecossistema — o que é deste sistema, o que é do assessor, o que é das outras ferramentas

> Decisão: [ADR-007](decisoes/007-escopo-do-sistema.md)
> Este documento delimita o escopo. Quando outro documento contradisser, vale este.
> O que já funciona e o que falta: [roadmap](roadmap.md).

## 1. Objetivo único deste sistema

**Executar o trabalho manual que sustenta os serviços de mídia paga do assessor**: coletar, conferir, calcular, devolver conversões às plataformas, montar os números e o material de apoio. Assim o assessor gasta o tempo dele pensando, decidindo e se relacionando com o cliente.

O sistema **não pensa a estratégia** e **não fala com o cliente**.

## 2. O ecossistema Trilha

| Etapa | Repositório | Papel |
|---|---|---|
| 1. Diagnóstico e planejamento | [Trilha-briefing](https://github.com/davi-barbosap/Trilha-briefing) | entende o cliente e decide a estratégia; é a fonte de tudo o que as outras ferramentas usam |
| 2. Copy | [Trilha-copy](https://github.com/davi-barbosap/Trilha-copy) | estrutura e revisa os textos dos anúncios, fiel ao briefing |
| 3. Página | [Trilha-LP](https://github.com/davi-barbosap/Trilha-LP) | landing page com o rastreamento que leva a origem do lead até o Kommo |
| 4. Execução e medição | **Trilha-ads (este)** | coleta, confere e calcula: raio-x do funil, conversão real, freio, material das reuniões |
| Dados dos clientes | Trilha-clientes (privado) | os arquivos reais de cada cliente; este sistema lê a pasta `ads/` |

O código da célula da grade (`PT01`, `GB01`…) amarra as etapas: nasce na grade do briefing, vai no anúncio como `utm_content` e na mensagem do WhatsApp da página, e chega ao lead no Kommo. O raio-x agrupa os resultados por esse código ([métricas](metricas.md)).

## 3. As três colunas

| Assessor (humano) | Este sistema (Trilha-ads) | Outras ferramentas |
|---|---|---|
| Estratégia, decisões de verba, estrutura, criativo e oferta | **Raio-x do funil:** etapa por etapa, primeiro contato e cadência do time comercial do cliente, perdas por categoria, maior vazamento, marketing entregou × comercial converteu | **Trilha-briefing:** diagnóstico, estratégia, grade e hipóteses |
| Diagnóstico de aderência da oferta (responde as perguntas) | **Conversão real:** Kommo → Meta (API de Conversões) e Google (Data Manager API) | **Trilha-copy:** estrutura e revisão dos anúncios |
| **Contatos proativos** com o cliente (≥ 3 por semana) | **Coleta e monitoramento:** Meta, Google e Kommo; pacing; urgências; freio de emergência | **Trilha-LP:** landing pages com rastreamento |
| **Respostas no grupo do cliente** (≤ 2 h) | **Dossiê da otimização semanal** e execução do que o assessor aprovar | **BotConversa:** atendimento e fluxos no WhatsApp |
| Sessão de otimização semanal (decide) | **Números do relatório semanal** ao cliente (leads · criativos · ações) | **GA4 / GTM:** rastreamento do site e eventos |
| Relatório semanal: escreve os insights e apresenta | **Pacote de dados do briefing** de criativo | **Disparos em massa** |
| Briefing de criativo: escreve a estratégia | **Pacote da reunião mensal** | **Fluxos de CRM** no Kommo (etapas, salesbots, tags) |
| Reunião mensal: conduz | **Painel da carteira** para a reunião de equipe | **Captura de tarefas no ClickUp no mesmo dia** (n8n) |
| Alinhamento com a equipe | | |

A coluna do meio é o escopo deste sistema, não o que já roda. Estão prontos no código o raio-x (inclusive por criativo), a conversão para o Meta e as regras do freio e da saúde das contas, mas nada está em operação: a coleta, os materiais e as entregas dependem dos fluxos do n8n, que ainda não existem ([roadmap](roadmap.md)).

## 4. O que este sistema precisa das outras ferramentas (contratos de interface)

Este sistema não constrói essas ferramentas, mas depende do que elas gravam. Sem isso, a conversão real e os relatórios ficam incompletos.

| Ferramenta | Precisa entregar | Por quê | Situação |
|---|---|---|---|
| **Trilha-briefing** | `marca.yaml`, `ofertas/*.yaml` e `perfil.parcial.yaml` que passam no `python -m trilha validar` ([ADR-005](decisoes/005-cadastro-pelo-trilha-briefing.md)) | contrato de dados do cadastro | entrega; teste de contrato no briefing |
| **Trilha-LP** | campos ocultos com `gclid`, `gbraid`, `wbraid`, `fbclid` e as 5 UTMs, gravados nos campos do lead no Kommo ([Kommo](integracoes/kommo.md) §4); payload com esquema fixo; telefone em E.164 sem duplicar o DDI; hora do clique; evento de lead só depois do recebimento confirmado, com `event_id` compartilhado com o servidor; botão de WhatsApp com o código do criativo na mensagem | sem o identificador de clique, a venda não volta para o Google e o Meta; sem código no WhatsApp, o lead do botão chega sem atribuição | entrega. Grava também `landing_page` e `event_id_lead`, que este sistema ainda não lê |
| **Trilha-copy** | anúncios aprovados com o código da célula como `utm_content` | atribuição por criativo (`por_criativo` no raio-x) | entrega |
| **BotConversa** | na conversa vinda de anúncio de clique para WhatsApp, repassar o `ctwa_clid` e as UTMs ao lead no Kommo; mover o lead nas etapas padronizadas | sem o `ctwa_clid`, a qualificação da conversa não volta para o Meta | depende da configuração de cada cliente |
| **GA4 / GTM** | tag do Google e pixel do Meta funcionando nas páginas; eventos de conversão do site; `event_id` compartilhado entre pixel e servidor | o freio usa "horas sem evento de conversão"; deduplicação no Meta | depende da configuração de cada cliente |
| **Fluxos de CRM (Kommo)** | funil com as etapas padrão; motivos de perda nativos com a lista padrão, obrigatórios; responsável em todo lead; contatos registrados no Kommo ([raio-x do funil](raio-x-do-funil.md), contrato) | sem isso não há raio-x: não dá para saber onde está o vazamento nem de quem é a perda | depende da configuração de cada cliente |
| **Captura de tarefas (n8n)** | tarefas no ClickUp com o cliente identificado (pasta do cliente) | o painel da carteira lê tarefas atrasadas por pessoa | a fazer |

Mudou uma etapa no Kommo, um campo oculto da página ou o fluxo do BotConversa? Avise quem cuida deste sistema: o mapa de eventos e o W01 precisam acompanhar.

### Outras ferramentas da operação

| Ferramenta | Relação com este sistema |
|---|---|
| Painéis de mensuração por cliente | camada de relatório publicada para o cliente; devem seguir o mesmo [dicionário de métricas](metricas.md) para os números baterem |
| Painel de saúde da carteira | mesma função do painel da carteira; as regras de saúde das contas foram trazidas para cá (`saude.py`) |
| Ranking do time comercial (painel de TV para o cliente) | usa as mesmas ideias de leads parados e perfil comparativo |
| Rotinas de tags no Kommo (estado do bot, `Interagiu`) | automação de CRM com simulação antes de gravar e log para desfazer; o raio-x lê as tags com os nomes reais ([Kommo](integracoes/kommo.md) §3.2) |
| Salesbots e fluxos do pré-atendimento | aplicam as tags e etapas que o raio-x lê (Interesse Confirmado, lead frio, não-cadastrou, reativado, bot-*) |
| Disparos em massa | fora do escopo |
| Landing pages feitas fora da Trilha-LP | algumas não gravam identificadores de clique nem UTMs em campo próprio, e versões antigas não enviam o lead a lugar nenhum. Sem isso a venda não volta às plataformas: o caminho é migrar para a Trilha-LP |

## 5. Time comercial do cliente ≠ assessor

O sistema **mede** o time comercial do cliente (corretores, atendentes) atendendo os leads: primeiro contato, cadência, conversão. Isso é o raio-x do funil. O sistema **não mede** o contato do assessor com o cliente (contatos proativos, respostas no grupo).

## 6. Fora do escopo, de propósito

- Construir landing pages, disparos em massa ou fluxos de CRM e atendimento.
- Medir ou cobrar tempo de resposta e contatos do assessor com o cliente.
- Escrever mensagens ao cliente, roteiros, peças criativas ou a estratégia de um briefing.
- Prospecção comercial da agência. (A calculadora de economia unitária pode ser usada nisso, mas como uso paralelo; aqui ela serve para as metas de cada cliente.)
