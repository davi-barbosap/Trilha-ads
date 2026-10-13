# Dicionário de métricas da Trilha

> Fonte: leitura completa dos repositórios de mensuração, atendimento e painéis da operação (out/2026).
> Implementação: `trilha/core/funil.py` (raio-x), `trilha/core/atribuicao.py` (canal), `trilha/core/saude.py` (contas), `trilha/core/periodo.py` (comparações), `trilha/core/correcoes.py` (correções confirmadas).

Todo número que o sistema mostra (dossiê, relatório, pacote da reunião, painel) segue estas definições. Painel de cliente que usa outra regra precisa ser alinhado a esta. Se um cliente exigir outra régua, ela vira um campo explícito do perfil, nunca uma divergência silenciosa.

## Entrada

| Métrica | Definição |
|---|---|
| **Lead** | Negócio criado no período nos funis de **entrada** (SDR) e de **nutrição**. Do funil de **fechamento** (Closer) só entra o card de quem **nunca apareceu** na entrada nem na nutrição: cadastro direto no Closer (indicação, plantão) conta como entrada pela data do card. A etapa de entrada não ordenada do Kommo ("Leads de entrada"/incoming) não conta até o lead ser aceito. Funis de **base** importada e de **teste** ficam fora de leads, CPL e taxa de qualificação. |
| **Pessoa** | Hash do telefone normalizado (com DDI); sem telefone, hash do e-mail. É a chave da deduplicação e do cruzamento entre funis. Se a chave sair da trilha-api, usa-se HMAC com segredo (hash puro de telefone é reversível por força bruta). |
| **Deduplicação de leads** | A mesma pessoa conta **uma vez por mês de entrada**. Quem entrou em julho e voltou em agosto é uma entrada de julho e uma de agosto. Quem tem card no SDR e na Nutrição conta uma vez, pelo SDR. |
| **Canal** | Campo "Origem" (do lead ou, vazio, do contato) normalizado: Meta+Ads/Facebook/Instagram → **Meta Ads**; google → **Google Ads**; indicação/recomendação → **Indicação**; `(referral)` (visita vinda de outro site, gravada pelas landing pages) → **Outro site**; vazio, "unknown" ou lixo → **Não rastreado**. Antes da regra geral valem os **apelidos do cliente** (`crm.origens`, ex.: `trilha-performance: Meta Ads`). Origem sem regra sai com o nome que o CRM registrou, nunca num balde "outros". |
| **Canal da venda** | O do card de fechamento; vazio, o do **primeiro card da pessoa** nos funis de entrada. |
| **UTMs** | `+` vira espaço; `{{…}}`, vazio e "—" são vazio; o criativo é o código antes de " \| " ("VD01 \| Ana" → "VD01"), que é o que casa com o nome do anúncio no Meta. Score e respostas do bot seguem a mesma regra da origem: lead primeiro, contato como reserva. |
| **Leads de mídia paga** | Leads com canal Meta Ads ou Google Ads. É o divisor dos custos. |

## Funil

| Métrica | Definição |
|---|---|
| **Lead qualificado** | Chegou à etapa de qualificado, a reunião agendada ou a reunião realizada, ou tem a tag de qualificado ou de reunião. Quem agendou passou pela qualificação, mesmo que o card tenha voltado de etapa. A tag "Interesse Confirmado" dos fluxos de pré-atendimento **não é qualificação**: o fluxo manda para "interesse" qualquer resposta que não seja recusa. |
| **Reunião agendada** | Contada **por pessoa** e pela **data marcada**, vinda das tarefas de reunião do Kommo (tipo Meeting, `complete_till`). Sem tarefa, a etapa ou a tag (`reunião-agendada`, `reagendar-reunião`). Quem remarca conta 1; remarcação = 2 ou mais tarefas de reunião ou a tag de reagendar, mostrada como número secundário. |
| **Reunião realizada / comparecimento** | Pela **data em que aconteceu** (tarefa de reunião concluída; ou o campo "Data da reunião realizada", `crm.campos.data_comparecimento`), por pessoa. Vale o 142 do funil de entrada (`crm.funis[].ganho_significa`), a etapa mapeada **ou** a tag `reunião-realizada`: o card costuma sair do 142 depois da reunião e só a tag preserva o evento. Card que chegou ao fechamento conta como realizada. Tarefa concluída sem avanço no funil é no-show: conta só como agendada. |
| **Oportunidade** | Lead que chegou a reunião realizada: o no-show já está descontado. |
| **Proposta** | Card do Closer nas etapas de proposta (enviada, follow-up, sinal verde, dados de venda solicitados). |
| **Venda** | O "ganho" (142) do funil de **fechamento**, com **data de fechamento** dentro do período (não a data de criação do lead). O 142 de qualquer outro funil (entrada, nutrição) só conta com `ganho_significa` explícito. |
| **Deduplicação de vendas** | Mesma pessoa, mesmo dia, mesmo valor e mesmo produto = o mesmo negócio cadastrado duas vezes. Duas unidades para a mesma pessoa no mesmo dia são duas vendas. |
| **Valor vendido / receita** | Soma do valor dos negócios ganhos no período (VGV no imobiliário). |
| **Ticket médio** | Valor vendido ÷ vendas **com valor**. Venda sem valor no Kommo não rebaixa o ticket; aparece em "vendas sem valor" e gera sinal. |
| **Ciclo de vendas** | Mediana (não média) de dias entre o **primeiro card da pessoa** nos funis de entrada e o fechamento. |
| **Conversão SDR** | Reuniões realizadas ÷ leads de entrada. |
| **Conversão Closer** | Vendas ÷ reuniões realizadas (aproximada em janela curta; converge em janela longa). |
| **Reativado** | Lead com a tag de reativação (`lead reativado` e variantes `lead reativado \| …`) ou numa etapa mapeada como `reativado` (ex.: "Reativado (Disparo)"). O raio-x mostra quantos voltaram, quantos chegaram a agendamento e quantos compraram. |
| **Etapa de saída** | Etapa que encerra o lead sem ser o 143 ("Descartado", "Frio") é mapeada como `perdido` com um motivo (`crm.mapa_eventos[].motivo`). Sem isso, o lead conta como ativo e vira "parado". A tag `não-cadastrou` é perda por contato inválido. |

## Custo e retorno

| Métrica | Fórmula | Leitura |
|---|---|---|
| **Investimento** | gasto de mídia paga, dia a dia: Meta por conjunto, Google por campanha (o Performance Max não tem grupo de anúncios) | — |
| **CPL** | investimento de captação ÷ leads de mídia paga | **diagnóstico**, nunca resultado; não divide pelo total de leads |
| **Investimento de captação** | investimento sem as campanhas sem objetivo de lead (topo de funil, alcance, visualização), identificadas pelo objetivo da campanha | o gasto de topo infla o CPL; CAC, retorno e custo por reunião continuam sobre o investimento total |
| **Meta · WhatsApp** | campanhas de clique para WhatsApp com CPL próprio, o gasto delas descontado do Meta formulário/LP | juntar os dois distorce o CPL dos dois lados |
| **CPL qualificado** | investimento ÷ qualificados de mídia paga | métrica principal de plataforma |
| **Custo por reunião** | investimento ÷ **todas** as reuniões realizadas | **piso** (inclui reuniões de lead orgânico); o de mídia paga aparece ao lado |
| **CPO por canal** | investimento do canal ÷ reuniões realizadas do canal | o número honesto para comparar canais |
| **CAC / custo por venda** | investimento ÷ vendas com canal Meta ou Google | **teto**: vendas sem rastreio ficam fora |
| **Retorno (ROAS)** | valor das vendas de mídia paga ÷ investimento | **piso**: receita sem rastreio fica fora |
| **CTR · CPM** | cliques no link ÷ impressões · investimento ÷ impressões × 1000 | diagnóstico |

Canais sem gasto medido (orgânico, indicação, não rastreado) ficam com custo **em branco**, não zero. "Sem atribuição" no relatório tem duas linhas: **não rastreado** (origem vazia ou lixo) e **canais sem gasto medido**.

## Time comercial do cliente

| Métrica | Definição |
|---|---|
| **Primeiro contato** | Da entrada do lead à **primeira mensagem de saída enviada por uma pessoa** (Kommo: `outgoing_chat_message`, `entity_direct_message` ou `outgoing_mail` com `created_by` ≠ 0; mensagem de bot e de automação não conta, e num dos clientes lidos são 2 de cada 3). Sem esse evento, a entrada em atendimento; sem ela, a qualificação. Tempo negativo ou de 30 dias ou mais é erro de registro e fica fora. |
| **Prazo de primeiro contato** | Medido em **minutos de expediente** (`crm.horario_comercial`: dias, início, fim e fuso): lead que chega às 23h e recebe a primeira mensagem às 8h05 esperou 5 minutos. O tempo corrido aparece ao lado. `crm.sla_primeiro_contato_min` vem do briefing (30 min → 30, 2 h → 120, 24 h+ → 1440). |
| **Chegada dos leads** | Mapa dia da semana × hora (horário do cliente), % fora do horário comercial, % à noite, % no fim de semana e o pico. É a base do plantão e do prazo de contato. |
| **Interagiu (resgate)** | Houve mensagem de chat enviada **por um humano** e o lead respondeu **depois** dela (`incoming_chat_message` posterior). Resposta espontânea ao bot não conta. Funis de entrada e nutrição. A regra nativa do Kommo ("mensagem recebida em qualquer canal") errava 298 de 535 casos no cliente em que foi medida e foi desligada lá. |
| **Pré-atendimento (bot)** | Tags exclusivas: `bot-concluído` (respondeu até a última pergunta) · `bot-incompleto` (respondeu ao menos uma) · `bot-nao-iniciado` (nunca respondeu; grafia real, sem acento). Com mais de uma tag vale concluído > incompleto > não iniciado. Nos fluxos de pré-atendimento da equipe, "Interesse Confirmado" equivale a concluído e "lead frio" a não iniciado. Lead sem nenhuma dessas tags fica fora da base do bot. O raio-x mostra também a qualificação de cada grupo. |
| **Leads parados** | Leads ativos (sem venda nem perda) sem movimentação há mais de `crm.dias_parado` dias (padrão 15), por responsável, com a **carteira parada** (% dos ativos da pessoa). Acima de `crm.dias_base_velha` (padrão 30) é **base velha**. Parado sem responsável aparece marcado, não some. No painel da carteira a leitura é sobre uma janela fixa de 45 dias de entrada, independente do período do relatório. |
| **Distribuição** | Leads da pessoa ÷ média do time (sem baldes e sem gestores). Desequilibrada a partir de 1,6× ou até 0,5× a média, quando a média é de 3 leads ou mais. |
| **Perfil por pessoa** | Nota de 0 a 100 relativa ao time no período (100 = o melhor do time, não uma meta). Dimensões e pesos: vendas 28 · conversão (vendas ÷ leads da safra) 20 · volume 16 · primeiro contato 16 · movimentação (saiu de novo lead) 10 · consistência (menos parados) 10. Empate = 50; sem dado = nota do pior. Só entra quem tem amostra: SDR com 20+ leads, closer com 5+ reuniões. |
| **Quem não é pessoa** | Baldes do sistema ("DESCARTE", "sem corretor") e os do cliente (`crm.baldes`, ex.: o usuário da imobiliária) ficam fora do time. Gestores (`crm.gestores`) aparecem, mas ficam fora da média e dos sinais por pessoa. |
| **Ritmo e prazo de tarefas** | Ritmo = mediana de dias entre criar e concluir; prazo = concluídas dentro do vencimento; atrasadas = pendentes com prazo vencido. O Kommo não expõe data de conclusão: usa-se a última alteração da tarefa. Os tipos de tarefa do cliente ("Dia 1", "Dia 3", "C - Dia 2 P.E"…) mostram a cadência quando a conta não registra ligações. |

## Qualidade do lead

| Métrica | Definição |
|---|---|
| **Lead score** | Classificação feita pelo bot ou pela régua do CRM do cliente. A escala é do cliente e varia (A–D na régua de um cliente e A–F no campo do Kommo do mesmo cliente; A–E com "Revisar" em outro). O sistema lê o score gravado, não recalcula. Quando o fechamento reavalia, vale o score final. O funil por score é em coorte e mostra **"sem score"** como grupo visível. |

## Períodos e comparações

- **Semanas do mês:** w1 = dias 1–7, w2 = 8–14, w3 = 15–21, w4 = 22 até o fim do mês.
- **Comparação:** com a janela imediatamente anterior, do mesmo número de dias (7 contra 7). No **mês corrente**, do dia 1 ao dia D contra o dia 1 ao dia D do mês anterior (D limitado ao fim daquele mês).
- **Variação:** taxa varia em **pontos percentuais**; volume, custo e valor variam em **%**. Diferença abaixo de 0,5% (ou 0,5 pp) é "estável"; anterior zerado é "sem base".
- **Eventos datados:** reunião pela data em que aconteceu, venda pela data de fechamento. O raio-x de safra (leads que entraram no período) e os indicadores do período (eventos que aconteceram no período) são leituras diferentes e aparecem identificadas.
- **Janela que começa antes da primeira mídia veiculada:** métricas financeiras com ressalva (CPL e CAC subestimados, retorno superestimado).
- **Períodos com apagão de rastreio** ficam fora do comparativo de CPL (mediriam o rastreio, não a mídia), mas os leads seguem contados.
- **Metas do cliente:** cada meta declara a base. "Agendamento 40%" de um dos clientes é agendados ÷ **leads**; o raio-x calcula cada passagem sobre a etapa anterior. Comparar sem dizer a base é erro.

## Correções confirmadas

Erro de cadastro que o time do cliente confirmou (negócio duplicado, venda fechada no Kommo com data errada) vai para `clientes/<id>/correcoes.yaml`, com motivo e quem confirmou, e é aplicado antes de qualquer cálculo. Nada de exceção escondida em código ou painel.

## Qualidade dos dados

Leads e vendas duplicados removidos · perdas marcadas como "Lead duplicado" (dado, não perda) · vendas sem valor · perdas sem motivo · motivos fora da lista (e quantos distintos: 8 ou mais = lista não padronizada) · leads não rastreados · leads sem responsável. Cada fonte (Kommo, Meta, Google) tem a data da sua última coleta visível; fonte mais de 24 h atrás gera aviso.

## Contas de anúncio

| Métrica | Definição |
|---|---|
| **Saldo** | Só em conta pré-paga (`is_prepay_account`), lido de `funding_source_details.display_string` ("R$ 1.234,56"). Conta pós-paga fica sem saldo; o campo `balance` do Meta é valor devido, não saldo. |
| **Dias de saldo** | saldo ÷ gasto médio diário dos últimos 7 dias. Menos de 5 dias = P1 (recarga esta semana); menos de 10 = P2 (avisar o cliente). |
| **Recarga sugerida** | gasto médio diário × 30. |
| **Status da conta** | qualquer status diferente de ativa = P1. Pagamento pendente, acerto pendente e período de carência pedem regularizar o pagamento; desativada, em análise de risco e encerrada pedem investigação. |
| **Anúncios** | anúncios reprovados ou com problema de entrega (`effective_status` DISAPPROVED / WITH_ISSUES) = P2. |
| **Alertas técnicos** | credencial recusada = **um** P1 para o responsável técnico (nunca um "conta não encontrada" por cliente); conta que sumiu do acesso e gasto ilegível = P2 para o técnico. Gasto ilegível não fica verde: fica "sem dado". |
