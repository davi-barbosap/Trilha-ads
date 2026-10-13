# Raio-x do funil

> Código: `trilha/core/funil.py`, `trilha/core/playbook.py` · CLI: `python -m trilha raio-x` · API: `POST /funil/raio-x`
> Decisão: [ADR-008](decisoes/008-funil-padrao.md) · Definições: [dicionário de métricas](metricas.md)

## Por que existe

A maioria das operações olha para as duas pontas: quantos leads entraram e quantas vendas saíram. O que acontece no meio é tratado no achismo, e é esse achismo que leva a decisões caras:
- aumentar a verba quando o vazamento está no atendimento;
- cobrar o marketing por venda quando ele já entregou volume, qualidade e visita;
- trocar agência, CRM, script ou campanha sem saber onde está o gargalo.

O raio-x mostra o meio do funil etapa por etapa e aponta **onde está o maior vazamento e quanto ele custa**. A leitura e a decisão são do assessor.

## Funil padrão (todos os segmentos)

O funil é o mesmo para qualquer segmento. O playbook muda só o nome exibido de cada etapa e as referências de conversão.

| Etapa (código) | Padrão | Imobiliário | Quem move o lead até aqui |
|---|---|---|---|
| `lead` | Novo lead | Novo lead | marketing |
| `em_atendimento` | Em atendimento | Em atendimento | atendimento (primeiro contato) |
| `lead_qualificado` | Qualificado | Qualificado | qualificação (qualidade do lead + critério do atendimento) |
| `agendamento` | Reunião agendada | Visita agendada | comercial |
| `comparecimento` | Reunião realizada | Visita realizada | comercial |
| `proposta` | Proposta enviada | Proposta enviada | comercial |
| `venda` | Venda | Venda | comercial |
| `perdido` | — | — | etapa 143 do Kommo; classificado abaixo |

Outros segmentos usam os mesmos códigos com seus nomes: em educação, "aula experimental agendada/realizada"; em saúde, "consulta agendada/realizada"; em serviços, "orçamento enviado". Segmento sem playbook próprio usa `playbooks/padrao/`.

Etapas puladas contam como passadas: um lead que foi de "qualificado" direto para "venda" conta em todas as etapas entre as duas.

### Vários funis no Kommo

Operações reais usam mais de um funil: **SDR** (entrada), **Closer** (fechamento), **Nutrição**, **base importada** e **teste**. Cada um é cadastrado em `crm.funis` com seu papel. O "ganho" (142) muda de sentido: no Closer é venda; no SDR costuma ser reunião realizada (`ganho_significa: comparecimento`); na Nutrição só conta com `ganho_significa` explícito. Base e teste não geram evento nem entram em leads e CPL. Funil não cadastrado não gera evento.

Etapas que encerram o lead sem ser o 143 ("Descartado", "Frio") são mapeadas como `perdido` com um motivo; sem isso, o lead fica contado como ativo e vira "parado".

## O que o raio-x mostra

| Bloco | Conteúdo |
|---|---|
| **Etapa por etapa** | quantos chegaram a cada etapa, conversão da etapa anterior, referência do segmento e tempo mediano entre etapas; etapa confirmada só por tag (ex.: `reunião-realizada`) conta sem inventar data |
| **Primeiro contato** | tempo mediano até a primeira mensagem **de uma pessoa** (o bot não conta), em minutos de expediente e corridos; % dentro do prazo (`crm.sla_primeiro_contato_min`, em expediente); tempo de quem chegou dentro e fora do horário; leads que nunca foram contatados |
| **Chegada dos leads** | mapa dia da semana × hora, % fora do horário comercial, à noite e no fim de semana, pico |
| **Cadência** | tentativas de contato dos leads perdidos antes de qualificar × dos qualificados |
| **Perdas** | por etapa e por categoria (lead, atendimento, comercial, externo, sem motivo); qualificados perdidos por motivo de lead = **critério de qualificação a revisar**; "lead duplicado" sai das perdas e vai para qualidade dos dados |
| **Maior vazamento** | a passagem abaixo da referência que mais custa vendas, com o valor em R$ |
| **Marketing entregou × comercial converteu** | leads, qualificados e agendamentos com custo de cada um × prazo de primeiro contato, comparecimento, propostas, vendas, conversões SDR e Closer, ciclo de vendas, perdas de atendimento e comerciais |
| **Resultado** | vendas, valor vendido (VGV no imobiliário), ticket (só vendas com valor), retorno sobre o investimento, custo por reunião (piso, todas as reuniões) e o de mídia paga, custo por venda; o CPL aparece só como diagnóstico, sobre o investimento de captação |
| **Por responsável** | o mesmo raio-x por SDR/corretor do time do cliente: primeiro contato, perdas sem motivo, parados e carteira parada, distribuição de leads contra a média do time e o **perfil** (0–100, relativo ao melhor do time, só com amostra de 20+ leads); baldes do sistema e do cliente ficam fora; gestores aparecem fora da média |
| **Por closer** | comparecimentos → propostas → vendas, quando o fechamento é de outra pessoa (amostra mínima: 5 reuniões) |
| **Por canal, campanha e score** | leads, qualificados, comparecimentos, vendas e valor, atribuídos pelo Kommo; canal "Não rastreado" à parte; funil por lead score com o grupo "sem score" |
| **Pré-atendimento** | % concluído, incompleto e não iniciado no bot, a qualificação de cada grupo, % dos não qualificados que interagiram com um humano |
| **Reativação** | leads reativados, quantos chegaram a agendamento, vendas e valor |
| **Leads parados** | leads ativos sem movimentação há mais de `crm.dias_parado` dias (padrão 15), por responsável, com os sem responsável marcados; base velha acima de `crm.dias_base_velha` |
| **Qualidade dos dados** | leads e vendas duplicados removidos, perdas marcadas como duplicado, vendas sem valor, perdas sem motivo, motivos fora da lista (e quantos distintos), leads não rastreados, leads sem responsável |
| **Sinais** | regras fixas que registram o fato e o número, sem prescrever: perdas de atendimento acima de 30% antes da qualificação → resgatar a base antes de aumentar volume e revisar o primeiro contato; mais de 20% das perdas sem motivo; 8+ motivos distintos fora da lista; mais de 20% sem canal; mais de 20% sem responsável; vendas sem valor; qualificados perdidos por motivo de lead; leads parados; 10+ em base velha; 40%+ dos ativos parados numa etapa; 40%+ dos leads fora do horário; pessoa com 10+ leads e nenhum qualificado; pessoa com qualificação abaixo da metade da média; distribuição desequilibrada |

## Perdas: de quem é

Toda perda no Kommo exige um motivo da lista padrão. Cada motivo tem uma categoria no playbook:

| Categoria | Significa | Exemplos |
|---|---|---|
| `lead` | qualidade do lead que o marketing trouxe | contato inválido, fora do perfil financeiro, procurava outro produto |
| `atendimento` | velocidade, cadência e condução do time do cliente | não respondeu às tentativas, demora no primeiro contato, não compareceu e não foi reagendado |
| `comercial` | proposta, negociação e fechamento | escolheu um concorrente, preço não atendeu, desistiu após a proposta |
| `externo` | fora do controle de marketing e comercial | financiamento negado, adiou a decisão |

O **momento** da perda vem da etapa em que o lead estava: antes ou depois da qualificação. O mesmo motivo muda de leitura conforme o momento. Um lead "fora do perfil financeiro" perdido antes de qualificar é qualidade do lead; depois de qualificado, é falha no critério de qualificação.

## Maior vazamento: como é calculado

Para cada passagem abaixo da referência, com pelo menos 20 leads na etapa anterior:

```
vendas a mais = leads na etapa anterior × (referência − conversão observada) × conversão do resto do funil
valor a mais  = vendas a mais × valor médio das vendas do período
```

A referência vem do playbook do segmento. Segmento sem referência compara com o histórico do próprio cliente (parâmetro `referencia`).

## Resultado é venda

- **Resultado:** vendas, valor vendido, retorno sobre o investimento, custo por comparecimento, custo por venda.
- **Custos sobre mídia paga:** investimento ÷ o que veio de Meta e Google. Como parte das vendas entra sem rastreio, o custo por venda é um **teto** e o retorno é um **piso**.
- **Deduplicação:** a mesma pessoa conta uma vez por mês de entrada; mesma pessoa, mesmo dia, mesmo valor e mesmo produto é a mesma venda.
- **Diagnóstico:** CPL, CTR, CPM. CPL baixo com lead que não fecha é prejuízo disfarçado de eficiência.
- No imobiliário, o valor vendido é o **VGV** (valor do negócio no Kommo). A comissão continua sendo a base das metas (`modelo_receita`) e do valor enviado às plataformas.

## Atribuição pelo Kommo

Em ciclos longos a venda acontece muito depois do clique, fora da janela de atribuição das plataformas. A janela do Google para conversões offline é de até 90 dias; acima disso, o sistema não envia e registra o motivo. O raio-x atribui vendas à campanha e ao criativo gravados no próprio lead (UTMs no Kommo), então **nenhuma venda se perde no relatório**, esteja ou não na janela da plataforma. O criativo é o código da célula da grade no `utm_content` (`por_criativo`: leads, qualificados, vendas e, com o gasto de cada código, os custos). O gasto por código chega pela coleta diária (W02); antes dela, pode ser informado à mão (`--gasto-por-codigo`).

## Time comercial do cliente ≠ assessor

O raio-x mede o time comercial **do cliente** (corretores, atendentes, SDRs) atendendo os leads. O contato do **assessor** com o cliente continua fora do sistema ([ecossistema](ecossistema.md)).

## Onde aparece

| Material | Uso do raio-x |
|---|---|
| Dossiê de otimização | maior vazamento e passagens abaixo da referência, antes de qualquer ponto de atenção de mídia |
| Relatório semanal | "marketing entregou × comercial converteu", perdas por categoria, primeiro contato por responsável |
| Pacote da reunião | raio-x do mês completo, por campanha e por responsável |
| Painel da carteira | maior vazamento de cada cliente |

## Padrão no Kommo (contrato)

O raio-x só é tão bom quanto o Kommo que o alimenta. Em todo cliente:
1. Funil com as etapas padrão (os nomes podem seguir o segmento), mapeadas em `crm.mapa_eventos`, incluindo as etapas de saída que não são o 143.
2. Motivos de perda **nativos do Kommo** com a lista padrão do playbook, obrigatórios ao mover para "perdido".
3. Responsável preenchido em todo lead; o usuário da empresa cadastrado em `crm.baldes`.
4. Mensagens e ligações registradas no Kommo, para o primeiro contato humano e a cadência serem medidos.
5. UTMs gravadas no lead na entrada.
6. Tags do pré-atendimento, de reunião e de reativação com os nomes de `crm.tags` (o padrão já reconhece os nomes reais da operação).

Detalhes em [Kommo](integracoes/kommo.md). Correções confirmadas com o cliente ficam em `clientes/<id>/correcoes.yaml`.

## Uso

```bash
python -m trilha raio-x tests/fixtures/funil_leads.json --perfil clientes/_exemplo/perfil.yaml --investimento 7550
```

O exemplo usa os números de um cliente do imobiliário da operação, sem identificação: R$ 7.550 investidos, 425 leads, 4 vendas, R$ 7.084.000 em VGV. As etapas do meio são ilustrativas.
