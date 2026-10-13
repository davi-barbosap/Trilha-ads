# Playbooks de segmento

O site da Trilha atende quatro segmentos: **mercado imobiliário, hotelaria, gastronomia e mercado automotivo**. Hoje o sistema tem playbook só para o imobiliário. Os outros três usam o `padrao/`, que não conhece as etapas, os motivos de perda nem a receita de cada um.

Este documento registra o que cada segmento precisa para ganhar um playbook próprio. Nenhum dos três está pronto: os números de referência só entram depois de medidos nos clientes da carteira.

## Como um playbook funciona

O funil é o mesmo para todos os segmentos ([ADR-008](../docs/decisoes/008-funil-padrao.md)):

```
lead → em_atendimento → lead_qualificado → agendamento → comparecimento → proposta → venda   (+ perdido)
```

O `playbook.yaml` de um segmento muda só quatro coisas ([`trilha/core/playbook.py`](../trilha/core/playbook.py)):

| Chave | O que muda |
|---|---|
| `rotulos_etapas` | o nome exibido de cada etapa no raio-x e nos relatórios |
| `taxas_referencia` | a conversão esperada de uma etapa para a seguinte; sem ela, o raio-x compara com o histórico do próprio cliente |
| `motivos_perda` | a lista de motivos de perda do Kommo e a categoria de cada um (`lead`, `atendimento`, `comercial`, `externo`, `duplicado`) |
| `perguntas_aderencia` | o diagnóstico de aderência da oferta, respondido pelo assessor antes de anunciar |

O que o segmento não define vem do `padrao/`, chave a chave. O imobiliário também traz economia padrão, eixos de objeção, regras de preço, compliance, fontes de lead e calendário; o carregador lê só as quatro chaves acima, e o resto serve de referência ao assessor e às outras ferramentas.

A receita de cada venda vem do `perfil.yaml` do cliente (`economia.modelo_receita`): `venda_direta` (ticket), `comissao` (valor do bem × comissão × participação) ou `recorrencia` (mensalidade × meses de retenção).

## Hotelaria (hotéis e pousadas)

**O que o site promete:** reservas diretas, reativação de hóspedes e receita, aproveitando cada período do ano.

**Etapas propostas**

| Etapa do sistema | Nome no hotel |
|---|---|
| `lead` | Novo contato |
| `em_atendimento` | Em atendimento |
| `lead_qualificado` | Datas e hóspedes definidos |
| `agendamento` | Cotação enviada |
| `comparecimento` | Pré-reserva / sinal pendente |
| `proposta` | (não usar, ou "negociação" em grupos e eventos) |
| `venda` | Reserva confirmada (pagamento ou sinal) |

**Receita:** `venda_direta`, com o ticket = diárias × noites médias × hóspedes da reserva média. O valor que importa é o da reserva **direta**: comparar com o que o hotel pagaria de comissão à OTA (Booking, Expedia) na mesma reserva.

**Motivos de perda para validar**

| Motivo | Categoria |
|---|---|
| Sem disponibilidade nas datas | externo |
| Achou mais barato em OTA | comercial |
| Preço acima do orçamento | lead |
| Datas fora da temporada pedida | lead |
| Não respondeu à cotação | atendimento |
| Demora em enviar a cotação | atendimento |
| Desistiu da viagem | externo |

**O que falta no sistema**
- **Motor de reservas:** muitas reservas diretas são feitas no motor do site, sem passar pelo Kommo. Decidir se a venda vem do motor (integração nova) ou se toda reserva direta é registrada no Kommo.
- **Reativação de hóspedes:** hoje é só a tag `lead reativado`. Para medir "hóspede que voltou", o raio-x precisa de uma origem `base de hóspedes` e da data da última estadia.
- **Sazonalidade:** calendário de alta e baixa temporada no playbook, e metas por período, não por mês corrido.

**Perguntas de aderência para validar:** quanto da receita vem hoje de OTA; qual a ocupação na baixa temporada; existe tarifa melhor no canal direto; o hotel tem base de hóspedes com consentimento para contato.

## Mercado automotivo (concessionárias e revendas)

**O que o site promete:** leads qualificados, conversão comercial e giro de estoque.

**Etapas propostas**

| Etapa do sistema | Nome na revenda |
|---|---|
| `lead` | Novo lead |
| `em_atendimento` | Em atendimento |
| `lead_qualificado` | Interesse e forma de pagamento definidos |
| `agendamento` | Visita ou test drive agendado |
| `comparecimento` | Visita ou test drive realizado |
| `proposta` | Proposta / simulação enviada |
| `venda` | Venda faturada |

**Receita:** `venda_direta` com a **margem bruta do veículo** como ticket, não o preço do carro. Seminovo e zero quilômetro têm margens muito diferentes: separar por oferta.

**Motivos de perda para validar**

| Motivo | Categoria |
|---|---|
| Crédito ou financiamento reprovado | externo |
| Veículo já vendido | externo |
| Avaliação da troca abaixo do esperado | comercial |
| Comprou em outra loja | comercial |
| Procurava outro modelo | lead |
| Fora do perfil de crédito | lead |
| Não compareceu ao test drive | atendimento |
| Não respondeu às tentativas de contato | atendimento |

**O que falta no sistema**
- **Giro de estoque:** o site promete, mas o sistema não lê estoque. Seria preciso ligar cada anúncio ao veículo (código do veículo na UTM e na mensagem do WhatsApp) e ter a lista de estoque com data de entrada.
- **Troca:** a avaliação do usado do cliente pesa na venda e não tem campo próprio.
- **Vários vendedores por loja:** o raio-x por responsável já existe; confirmar se a loja usa o Kommo de verdade ou outro CRM do setor.

**Perguntas de aderência para validar:** qual o tempo médio de estoque; quanto das vendas é financiada; a loja aceita troca; como estão as vendas de balcão e indicação.

## Gastronomia (restaurantes e bares)

**O que o site promete:** aquisição de clientes, recorrência e faturamento.

Este é o segmento que menos cabe no funil atual. A maior parte da venda acontece no salão, sem lead no Kommo. O funil só vale para o que passa pelo WhatsApp ou pelo CRM: **reservas, eventos e grupos, encomendas e delivery próprio**.

**Etapas propostas (reservas e eventos)**

| Etapa do sistema | Nome no restaurante |
|---|---|
| `lead` | Novo contato |
| `em_atendimento` | Em atendimento |
| `lead_qualificado` | Data e número de pessoas definidos |
| `agendamento` | Reserva feita |
| `comparecimento` | Compareceu |
| `proposta` | Orçamento de evento enviado (só eventos) |
| `venda` | Evento fechado ou consumo registrado |

**Receita:** `venda_direta` com o ticket médio por mesa (ou por evento). Para clientes com programa de recorrência, `recorrencia` com o gasto mensal × meses ativos.

**Motivos de perda para validar**

| Motivo | Categoria |
|---|---|
| Sem mesa na data | externo |
| Não compareceu à reserva | atendimento |
| Orçamento de evento acima do previsto | comercial |
| Fora da área de entrega | lead |
| Não respondeu | atendimento |

**O que falta no sistema**
- **Venda no salão:** sem integração com o PDV, o sistema não sabe quem veio pelo anúncio. Decidir entre (a) medir só reservas e eventos, (b) usar um código de oferta resgatado no caixa, ou (c) integrar o PDV.
- **Recorrência:** precisa de uma base de clientes com consentimento e da data da última visita. Hoje não existe no sistema.
- **Volume pequeno por lead:** com ticket baixo, o freio de emergência e o CPL máximo ficam muito apertados. Revisar os padrões do freio para este segmento.

**Perguntas de aderência para validar:** quanto do faturamento vem de reservas, eventos e delivery próprio; o restaurante tem base de clientes; qual a ocupação nos dias fracos; existe PDV com cadastro de cliente.

## Ordem sugerida

1. **Automotivo:** é o que mais se parece com o funil atual (visita, proposta, venda). A carteira já tem clientes do segmento, e o histórico deles calibra as referências.
2. **Hotelaria:** pede a decisão sobre o motor de reservas antes do playbook.
3. **Gastronomia:** pede a decisão sobre o que medir (reservas e eventos, código no caixa ou PDV) antes de qualquer coisa.

## Como criar um playbook

1. Criar `playbooks/<segmento>/playbook.yaml` só com o que difere do `padrao/`.
2. Deixar `taxas_referencia` vazio até ter o histórico de pelo menos dois clientes do segmento; até lá, o raio-x compara cada cliente com ele mesmo.
3. Cadastrar a mesma lista de motivos de perda no Kommo do cliente, como motivos nativos e obrigatórios ([raio-x do funil](../docs/raio-x-do-funil.md)).
4. Apontar o cliente para o segmento em `perfil.yaml` (`cliente.segmento`) e rodar `python -m trilha validar`.
5. Acrescentar um teste em `tests/test_funil.py` com os rótulos e as categorias do novo segmento.
