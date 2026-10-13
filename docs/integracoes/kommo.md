# Integração Kommo

> Código: `trilha/integracoes/kommo.py` · `trilha/conversao/pipeline.py` · `trilha/api.py` (rota `/conversao`) · Fluxo n8n: W01 ([n8n](n8n.md))
> Testes: `tests/test_kommo.py`, `tests/test_pipeline.py`, `tests/test_api.py`
> Núcleo: §7 (conversão real e qualidade de lead)

## 1. Antes de construir: o que já é nativo

Verificar na conta do cliente, porque o que for nativo não precisa de código:
- Integração do WhatsApp (API do WhatsApp Business) e gravação da origem da conversa — e, quando o atendimento inicial é pelo **BotConversa** (ferramenta paralela), se ele repassa o `ctwa_clid` e as UTMs ao lead no Kommo.
- Integração com formulários instantâneos do Meta (leads entram direto no funil).
- Formulários de site do Kommo (capturam UTMs).
- Integrações de eventos com o Meta disponíveis no marketplace do Kommo.

O Trilha cobre o que costuma faltar: **mapa etapa → evento padronizado por cliente, retorno para Meta e Google com deduplicação, registro no banco e alertas**. Fluxos de atendimento, nutrição e disparos no Kommo **não** são deste sistema ([ecossistema](../ecossistema.md)).

## 2. Fluxo

```
Kommo: lead criado ou mudou de etapa
  → webhook para o n8n: https://<dominio>/webhook/kommo/<cliente_id>?token=<segredo DESTE cliente>
  → W01 responde 200 ao Kommo na hora (o Kommo não espera processamento)
  → W01 chama a trilha-api: POST /conversao {cliente_id, webhook_token, corpo}
     trilha-api (dados pessoais ficam só aqui):
       → confere o segredo do cliente (KOMMO_WEBHOOK_TOKEN_<CLIENTE>)      senão: 403
       → confere a conta do corpo (account[subdomain]) com o perfil       senão: 403
       → parse_webhook()             qual lead olhar e qual etapa o webhook diz
       → KommoClient.dados_lead()    lê o lead e o contato principal (API v4, token KOMMO_TOKEN_<CLIENTE>)
       → confirma a etapa            só segue se o lead ESTÁ na etapa que o webhook diz
       → mapa do perfil.yaml         etapa → evento padrão
       → payloads com hash           Meta API de Conversões · Google Data Manager API
       → envia (só se TRILHA_SIMULAR=0) e devolve um resumo sem dado pessoal
  → W01 avisa no Slack se algum evento foi pulado
  → falha ou 403 → W10 (vigia de falhas)
```

**Por que um segredo por cliente:** o admin do Kommo de cada cliente enxerga a URL do webhook. Com um segredo único, um cliente poderia mandar conversões falsas para a conta de anúncios de outro. Com segredo próprio, conta conferida e etapa confirmada no Kommo, um webhook forjado não gera conversão.

**Repetições são seguras:** se o n8n repetir a chamada, Meta deduplica por `event_id` e Google por `transactionId` (ambos `kommo-<lead>-<evento>`).

## 3. Configuração por cliente (`perfil.yaml`)

```yaml
crm:
  tipo: kommo
  subdominio: "imobiliaria-exemplo"     # https://<subdominio>.kommo.com
  sla_primeiro_contato_min: 30          # prazo do time comercial do cliente para o primeiro contato
  mapa_eventos:                         # funil padrão da Trilha; IDs mudam em cada conta — copiar do Kommo
    - { pipeline_id: 1111, status_id: 2222, evento: lead }
    - { pipeline_id: 1111, status_id: 2223, evento: em_atendimento }
    - { pipeline_id: 1111, status_id: 3333, evento: lead_qualificado }
    - { pipeline_id: 1111, status_id: 4444, evento: agendamento }
    - { pipeline_id: 1111, status_id: 4445, evento: comparecimento }
    - { pipeline_id: 1111, status_id: 4446, evento: proposta }
    # 142 (venda ganha) → venda e 143 (perdida) → perdido já são padrão
  campos:                               # nome do campo personalizado no Kommo
    gclid: "gclid"
    gbraid: "gbraid"
    wbraid: "wbraid"
    fbclid: "fbclid"
    ctwa_clid: "ctwa_clid"
    meta_lead_id: "meta_lead_id"
    utm_source: "utm_source"
    utm_campaign: "utm_campaign"
    utm_content: "utm_content"          # recebe o nome do anúncio na taxonomia
    codigo_criativo: "codigo_criativo"  # código curto da mensagem do WhatsApp
    motivo_perda: "motivo_perda"        # só se a conta não usar os motivos de perda nativos
```

## 3.1 Vários funis

```yaml
crm:
  funis:
    - { pipeline_id: 1110, nome: SDR, papel: entrada, ganho_significa: comparecimento }
    - { pipeline_id: 1111, nome: Closer, papel: fechamento }        # 142 = venda
    - { pipeline_id: 1112, nome: Nutrição, papel: nutricao }        # 142 só com ganho_significa
    - { pipeline_id: 1113, nome: Base importada, papel: base }      # fora de leads e CPL
    - { pipeline_id: 1114, nome: Teste, papel: ignorar }
```

O "ganho" (142) só é venda no funil de fechamento. Em qualquer outro (entrada, nutrição) ele precisa de `ganho_significa`; sem isso, não gera evento. Funil não cadastrado em `funis` também não gera evento. Conta com um funil só pode deixar `funis` vazio (142 = venda, 143 = perdido).

## 3.2 Funil padrão no Kommo (todo cliente, qualquer segmento)

| Ordem | Etapa (nome pode seguir o segmento) | Evento |
|---|---|---|
| 1 | Novo lead | `lead` |
| 2 | Em atendimento (primeiro contato feito) | `em_atendimento` |
| 3 | Qualificado | `lead_qualificado` |
| 4 | Reunião / visita / consulta agendada | `agendamento` |
| 5 | Reunião / visita / consulta realizada | `comparecimento` |
| 6 | Proposta enviada | `proposta` |
| — | Venda ganha (142) | `venda` |
| — | Perdida (143) | `perdido` |
| — | Etapas de saída do cliente ("Descartado", "Frio") | `perdido`, com `motivo` |
| — | Reativado / Reativado (Disparo) | `reativado` |

```yaml
crm:
  mapa_eventos:
    - { pipeline_id: 1110, status_id: 5551, evento: perdido, motivo: Contato inválido }                       # Descartado
    - { pipeline_id: 1110, status_id: 5552, evento: perdido, motivo: Não respondeu às tentativas de contato }  # Frio
    - { pipeline_id: 1111, status_id: 5553, evento: reativado }                                              # Reativado (Disparo)
```

- **Motivos de perda:** usar os motivos nativos do Kommo, com a lista padrão do playbook do segmento (`motivos_perda`), **obrigatórios** ao mover para "perdida". A trilha-api lê o motivo do lead (`with=loss_reason`); o raio-x classifica a perda pela categoria do motivo (lead, atendimento, comercial, externo) e pelo momento (antes ou depois da qualificação). Motivo fora da lista aparece como "não classificado" no relatório.
- **Responsável:** todo lead com responsável (corretor/atendente). O raio-x sai também por responsável.
- **Contatos registrados:** mensagens e ligações feitas pelo Kommo, para medir a cadência (tentativas de contato por lead).
- **Histórico de etapas:** a coleta diária (W02) lê, pela API de eventos do Kommo, quando cada lead entrou em cada etapa e as tentativas de contato, e monta o histórico que o raio-x usa. Conferir na conta do cliente quais tipos de evento de contato estão disponíveis (há contas que não registram ligação nenhuma).
- **Primeiro contato humano:** o evento de saída mais antigo do lead (`outgoing_chat_message`, `entity_direct_message`, `outgoing_mail`) com `created_by` ≠ 0. `created_by` = 0 é bot ou automação e não conta. Vai para `LeadFunil.primeiro_contato_humano`.
- **Reuniões:** tarefas de reunião (tipo Meeting) dão a data marcada (`complete_till`), a pessoa (`entity_id`) e as remarcações (2 ou mais tarefas); tarefa concluída dá a data da reunião realizada. Sem tarefa, o campo `crm.campos.data_comparecimento` ou o histórico de etapas.
- **Origem no contato:** em algumas contas a integração ou o bot gravam origem, UTMs, score e respostas do bot no **contato**. A leitura procura primeiro no lead e, se vazio, no contato.
- **Tags lidas pelo raio-x** (`crm.tags`; comparação sem maiúsculas e sem acento, e "lead reativado \| follow-up" bate com "lead reativado"):

| Leitura | Tags padrão | Origem na operação |
|---|---|---|
| bot concluído | `bot-concluído`, `Interesse Confirmado` | salesbot de pré-atendimento; fluxos da equipe |
| bot incompleto | `bot-incompleto` | rotina de tags dos clientes |
| bot não iniciado | `bot-nao-iniciado` (sem acento), `lead frio` | salesbot de pré-atendimento; pré-atendimento escalonado |
| interagiu | `Interagiu` | rotina de tags (humano escreveu e o lead respondeu depois) |
| qualificado | `lead-qualificado` | time do cliente |
| reunião agendada | `reunião-agendada`, `reagendar-reunião`, `visita-agendada` | time do cliente |
| reunião realizada | `reunião-realizada`, `visita-realizada` | time do cliente (o card sai do 142 depois da reunião) |
| reativado | `lead reativado` (e variantes), `reativado` | fluxos de disparo e nutrição |
| contato inválido | `não-cadastrou` | pré-atendimento ("não me cadastrei", "engano") |

  As rotinas e fluxos que aplicam essas tags rodam fora deste sistema. "Interesse Confirmado" não é qualificação: o fluxo manda para "interesse" toda resposta que não for recusa.

## 3.3 Regras da coleta (W02)

Padrões dos coletores de mensuração da Trilha:
- **Vendas pela data de fechamento:** buscar também os leads do funil de fechamento com `closed_at` no período (não só os criados no período), e unir sem repetir.
- **Falhar alto:** qualquer resposta de erro (4xx ou 5xx) interrompe a coleta; no Meta, erro em qualquer janela mensal aborta tudo (nada de gasto parcial publicado). Nunca publicar "zero leads" por causa de token expirado; os últimos dados bons continuam valendo, com a data de coleta **de cada fonte** visível e aviso quando uma fonte ficar mais de 24 h atrás.
- **Trava antes de gravar:** cada fonte tem um mínimo de sanidade (ex.: Kommo com leads quando o período anterior teve, Meta com conjuntos, Google com campanhas). Abaixo disso, a coleta para e avisa em vez de gravar.
- **Card direto no fechamento:** o card do Closer de pessoa que nunca passou pela entrada nem pela nutrição entra como lead ([métricas](../metricas.md)).
- **Correções confirmadas:** `clientes/<id>/correcoes.yaml` (exclusões e datas de venda corrigidas, com motivo e quem confirmou) é aplicado antes do cálculo.
- **Paginação até o fim** (250 por página) e campos lidos por ID com fallback pelo nome (campo recriado muda de ID).
- **Base importada** entra só como contagem por etapa, não lead a lead.
- **Dados pessoais:** telefone e e-mail viram chave (hash) para deduplicar; nada sai em claro da trilha-api.

## 4. Campos personalizados padrão (criar em todo cliente)

| Campo | Tipo | Preenchido por |
|---|---|---|
| `gclid`, `gbraid`, `wbraid` | texto | campo oculto da landing / GTM |
| `fbclid` | texto | campo oculto da landing / GTM |
| `ctwa_clid` | texto | integração do WhatsApp (anúncio de clique para WhatsApp) |
| `meta_lead_id` | texto | integração de formulário instantâneo |
| `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` | texto | landing |
| `codigo_criativo` | texto | Salesbot lendo o código da mensagem pré-preenchida |
| `origem` | lista | padronizada: meta, google, portal_zap, portal_vivareal, portal_olx, indicacao, organico, lista |
| `motivo_perda` | lista | só se a conta não usar os motivos de perda nativos do Kommo |

O valor do negócio (campo "venda" do lead) deve ser o valor de venda — VGV no imobiliário. É ele que o raio-x soma como valor vendido.

## 5. Regras de envio

- **Deduplicação:** `event_id = kommo-<lead_id>-<evento>`; o mesmo lead voltando à mesma etapa não gera evento novo na plataforma.
- **Sem identificador, sem envio para aquela plataforma:** sem `gclid`/`gbraid`/`wbraid` e sem e-mail/telefone, não há envio ao Google; para o Meta, é preciso ao menos um entre `ctwa_clid`, `meta_lead_id`, `fbc` ou dado de contato em hash.
- **Eventos de uso interno** (`em_atendimento`, `proposta`, `perdido`, `reativado`) alimentam o raio-x e não vão às plataformas, salvo configuração explícita em `conversao.destinos`.
- **Ciclo longo:** o Google aceita conversões offline até 90 dias depois do clique. Lead criado há mais de 90 dias não é enviado ao Google; o motivo fica registrado como informativo e a venda conta no relatório pela atribuição do Kommo (UTMs do lead).
- **Limite de requisições da API do Kommo:** as leituras de lead passam por uma fila com backoff; a documentação oficial do Kommo define o limite vigente.
- **Falha nunca é silenciosa:** envio com erro vai para `fila_envios` com nova tentativa; três falhas seguidas viram alerta operacional.

## 6. O que sai dos dados do Kommo

| Dado | Onde aparece |
|---|---|
| Raio-x do funil: etapa por etapa, primeiro contato, cadência, perdas por categoria, maior vazamento | dossiê, relatório semanal, pacote da reunião, painel ([raio-x do funil](../raio-x-do-funil.md)) |
| Marketing entregou × comercial converteu | relatório semanal e pacote da reunião |
| Vendas e valor vendido por campanha e criativo (atribuição pelo Kommo) | relatório semanal, pacote da reunião, pacote de briefing |
| Motivos de perda por oferta | pacote de briefing |
| Divergência plataforma × Kommo | ponto de atenção no dossiê (urgência se > 50%) |

Reativação de leads frios, nutrição, salesbots e as rotinas que aplicam tags são fluxos de CRM — ferramentas paralelas. O sistema só lê o resultado (etapas e tags).

## 7. Testar localmente (sem n8n)

```bash
python -m trilha simular-webhook tests/fixtures/kommo_webhook.txt \
  --perfil tests/fixtures/clientes/_exemplo/perfil.yaml \
  --lead tests/fixtures/kommo_lead.json
```

Mostra os eventos identificados e os payloads exatos que iriam para o Meta e o Google, sem enviar nada.
