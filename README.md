# Trilha-ads

Execução e medição dos serviços de mídia paga da Trilha (Meta Ads e Google Ads). O sistema faz o trabalho manual e demorado do assessor: coletar, conferir, calcular, devolver a venda às plataformas e montar o material das reuniões. Assim o assessor gasta o tempo pensando, decidindo e cuidando do cliente.

O sistema **não decide estratégia nem verba, não cria campanhas e não fala com o cliente.** Serve para qualquer segmento; o playbook de um segmento muda só os nomes e as referências.

> **Situação:** o núcleo de cálculo está pronto e testado. **Nada está em operação ainda.** A coleta diária, os relatórios, o dossiê e a integração com o ClickUp dependem dos fluxos do n8n, que ainda não foram criados. Detalhes em [Situação atual](#situação-atual).

## Ecossistema Trilha

| Etapa | Repositório | Papel |
|---|---|---|
| 1. Diagnóstico e planejamento | [Trilha-briefing](https://github.com/davi-barbosap/Trilha-briefing) | entende o cliente e decide a estratégia; é a fonte de tudo o que as outras ferramentas usam |
| 2. Copy | [Trilha-copy](https://github.com/davi-barbosap/Trilha-copy) | estrutura e revisa os textos dos anúncios, fiel ao briefing |
| 3. Página | [Trilha-LP](https://github.com/davi-barbosap/Trilha-LP) | landing page com o rastreamento que leva a origem do lead até o Kommo |
| 4. Execução e medição | **Trilha-ads (este)** | coleta, confere e calcula: raio-x do funil, conversão real, freio, material das reuniões |
| Dados dos clientes | Trilha-clientes (privado) | os arquivos reais de cada cliente; este sistema lê a pasta `ads/` |

O código da célula da grade (`PT01`, `GB01`…) amarra as etapas: nasce na grade do briefing, vai no anúncio como `utm_content` e na mensagem do WhatsApp da página, e chega ao lead no Kommo. O raio-x agrupa os resultados por esse código; o padrão do código é editável por cliente (`crm.padrao_codigo`).

## O que faz

### Pronto no código, com testes

| Capacidade | Comando · rota da API | O que entrega |
|---|---|---|
| **Validação do cliente** | `validar` · `POST /validar` | Confere `perfil.yaml` e `ofertas/` contra o esquema. Lista as etapas do funil sem mapa no Kommo, as perguntas do diagnóstico de aderência da oferta sem resposta e os sinais de risco da oferta. |
| **Metas pela economia unitária** | `calcular` · `POST /calcular` | CAC, CPL e CPL qualificado máximos. Calcula a verba mensal para a plataforma aprender em cada degrau (lead, qualificado, agendamento, venda) e mostra quais degraus a verba sustenta. |
| **Raio-x do funil** | `raio-x` · `POST /funil/raio-x` | Mostra cada etapa contra a referência do playbook e o maior vazamento, em vendas e em R$. Separa as perdas por categoria (qualidade do lead, atendimento, comercial, externa). Mede o primeiro contato humano em minutos de expediente e a cadência. Põe lado a lado o que o marketing entregou e o que o comercial converteu, compara SDR e closer, traça o perfil de cada pessoa do time e aponta os leads parados. **Por criativo:** leads, qualificados e vendas por código da célula (`utm_content`), com os custos quando há o gasto de cada código. **Retorno** (`--retorno ads/<id>/retornos`): grava o resultado por código e os motivos de perda do período para o briefing ligar às hipóteses e para a copy. |
| **Conversão real** | `simular-webhook` · `POST /conversao` | Quando o lead muda de etapa no Kommo, confirma a etapa lendo o Kommo e monta o evento para o Meta (API de Conversões) e o Google (Data Manager API), com hash e deduplicação. O envio ao Meta está implementado; ao Google, por enquanto, só o payload. |
| **Freio de emergência** | `POST /freio/avaliar` | Duas regras: gasto desde o último lead de 3× o CPL máximo ou mais, e 6 h ou mais sem evento de conversão com a campanha gastando. Devolve a ação (pausar e avisar). Quem executa é o fluxo do n8n, com botão de desfazer. |
| **Saúde das contas** | `POST /contas/saude` | Avisa dias de saldo pré-pago (prioridade 1 abaixo de 5 dias, 2 abaixo de 10), sugere a recarga para 30 dias e aponta anúncios reprovados e conta desativada ou com pagamento pendente. |
| **Carteira** | `GET /clientes` | Os clientes válidos com a agenda de cada material, para os fluxos do n8n percorrerem. |

### Planejado: depende dos fluxos do n8n

| Material | Para qual compromisso do assessor | Fluxo |
|---|---|---|
| Coleta diária de Meta, Google e Kommo (gasto, leads, histórico de etapas, primeiro contato, tags) | base de todos os materiais | W02 |
| Urgências, freio executado e pacing da verba | monitoramento | W03 · W04 |
| Leitura diária da carteira no Slack | dia a dia | W05 |
| **Dossiê da otimização semanal**: vendas e valor vendido da semana, maior vazamento, o que mudou na conta, efeito das decisões anteriores, pontos de atenção | sessão de otimização | W12 |
| Execução do que o assessor aprovar no ClickUp | otimização | W06 |
| **Números do relatório semanal**: marketing entregou × comercial converteu, perdas por categoria, criativos e ações | relatório ao cliente (o assessor escreve a leitura) | W07 |
| Pacote de dados do briefing de criativo: o que converte, o que cansou, objeções e motivos de perda | briefing para a equipe de criação | W08 |
| **Pacote da reunião mensal** e **painel da carteira** | reunião com o cliente e reunião de equipe | W11 · W14 |

Nada sai do sistema direto para o cliente. Urgências vão para o Slack da operação e materiais chegam como tarefas no ClickUp, na véspera de cada compromisso.

## Como faz

1. **Cadastro.** O Trilha-briefing exporta marca, ofertas e um perfil parcial para `Trilha-clientes/ads/<id>/`. O assessor completa o `perfil.yaml` (contas, mapa de etapas do Kommo, freio, agenda dos materiais) e o `validar` confere ([ADR-005](docs/decisoes/005-cadastro-pelo-trilha-briefing.md)).
2. **Régua da Trilha.** Resultado é venda e valor vendido; CPL é diagnóstico. Os custos são calculados sobre a mídia paga, então o custo por venda é teto e o retorno é piso. Cada pessoa conta uma vez por mês, e o primeiro contato só conta mensagem de uma pessoa, não de bot ([métricas](docs/metricas.md)).
3. **Funil padrão** para todos os segmentos: novo lead → em atendimento → qualificado → agendado → compareceu → proposta → venda. Cada perda tem motivo e categoria ([raio-x do funil](docs/raio-x-do-funil.md), [ADR-008](docs/decisoes/008-funil-padrao.md)).
4. **Conversão real.** O webhook do Kommo chega à API, que confirma a etapa lendo o Kommo e envia o evento com hash. As plataformas passam a aprender com quem compra, não só com quem clica.
5. **Orquestração.** O n8n autohospedado agenda e chama a trilha-api; a API é o núcleo testado, que calcula e decide ([ADR-002](docs/decisoes/002-n8n-orquestrador.md)).
6. **Uma única ação automática:** o freio. Reativar é sempre decisão do assessor ([ADR-006](docs/decisoes/006-freio-de-emergencia.md)).

**Entradas:**
- `perfil.yaml`, `ofertas/` e `correcoes.yaml` do cliente;
- o playbook do segmento;
- o Kommo, pelo webhook e pela API;
- depois da coleta, também Meta e Google.

**Saídas:** raio-x em texto ou JSON, eventos de conversão e decisões do freio e da saúde em JSON, que o n8n consome.

## O que não faz

- Não pensa a estratégia, não decide verba, não cria campanhas nem anúncios e não fala com o cliente.
- Não constrói página, fluxo de CRM ou disparo ([ecossistema](docs/ecossistema.md)).
- Não mede o contato do assessor com o cliente. Ele mede o time comercial **do cliente**.
- **Ainda não lê:**
  - campanhas e anúncios do Meta e do Google (gasto, criativos): o gasto por código é informado à mão (`--gasto-por-codigo`) até existir a coleta;
  - o plano de campanhas do Trilha-briefing, para comparar o planejado com o que está rodando;
  - o `marca.yaml`;
  - os campos `landing_page` e `event_id_lead` que a Trilha-LP grava.

## Situação atual

- **Pronto:**
  - esquemas do perfil e das ofertas;
  - funil padrão e playbook do imobiliário;
  - raio-x (inclusive por criativo), calculadora e conversão para o Meta;
  - regras do freio e da saúde;
  - API, fluxos-modelo W01 e W10 e infraestrutura descrita em `infra/`.
- **Falta para operar:**
  - subir o servidor do n8n;
  - pôr o Kommo do cliente piloto no padrão;
  - criar os fluxos de coleta (W02) e de materiais (W03 a W14);
  - implementar o envio ao Google.

A ordem está no [roadmap](docs/roadmap.md).

Estimativa do [modelo operacional](docs/modelo-operacional.md) §5: cerca de 3,75 h de trabalho do assessor por cliente por semana, contra cerca de 7,6 h sem o sistema, o que permitiria uns 10 clientes por assessor. É estimativa: só vai ser medida em operação.

## Exemplo

Números de um cliente do imobiliário da operação, sem identificação: R$ 7.550 investidos, 425 leads, 4 vendas, R$ 7.084.000 em VGV. O raio-x de `tests/fixtures/` reproduz esses números, com as etapas do meio ilustrativas:

```
Resultado: 4 vendas · R$ 7.084.000 vendidos · retorno de 938,3× o investimento
  custo por visita realizada: R$ 302,00 · custo por venda: R$ 1.888 · CPL (diagnóstico): R$ 17,76
Primeiro contato: mediana 12 min úteis (110,5 corridos) · 74,3% dentro de 30 min úteis · 125 leads sem primeiro contato
Maior vazamento: Visita realizada (comercial) — 50,0% contra 65,0% de referência ≈ 1,2 venda(s) a menos, R$ 2.125.200
Marketing entregou: 425 leads · 120 qualificados · 50 agendamentos · R$ 62,92 por qualificado
```

## Como usar

```bash
pip install -e .        # editável: o sistema lê os playbooks da pasta do repositório

python -m trilha validar clientes/_exemplo/perfil.yaml      # confere a ficha de um cliente
python -m trilha calcular clientes/_exemplo/perfil.yaml     # CAC, CPL máximos e verba por degrau
python -m trilha raio-x tests/fixtures/funil_leads.json \
  --perfil clientes/_exemplo/perfil.yaml --investimento 7550 # raio-x do funil
  # com --gasto-por-codigo gasto.json ({"v0": 1800, ...}), o raio-x por criativo mostra os custos
  # com --retorno ads/<id>/retornos [--inicio 2026-10-01 --fim 2026-10-31], grava o retorno para o briefing
python -m trilha simular-webhook tests/fixtures/kommo_webhook.txt \
  --perfil clientes/_exemplo/perfil.yaml \
  --lead tests/fixtures/kommo_lead.json --contato tests/fixtures/kommo_contato.json   # o que seria enviado, sem enviar
TRILHA_CLIENTES_DIR=../Trilha-clientes/ads python -m trilha servir --porta 8080      # API do n8n (exige TRILHA_API_TOKEN)
```

Clientes reais ficam no repositório privado Trilha-clientes, pasta `ads/<id>/` ([ADR-004](docs/decisoes/004-dados-de-clientes.md)). Segredos: copie `.env.example` para `.env` (uso local) ou `infra/.env.example` e `infra/kommo.env.example` (servidor). Nenhum `.env` é versionado.

## Estrutura

```
trilha/            código: API, CLI, regras, integrações
tests/             testes (unittest) e fixtures
docs/              documentação
n8n/modelos/       fluxos-modelo do n8n (W01, W10)
infra/             servidor: Docker, n8n, Postgres, Redis, HTTPS, backup
playbooks/         funil padrão (todos os segmentos) e padrões do imobiliário
clientes/_exemplo/ ficha de cliente de exemplo; clientes reais ficam no Trilha-clientes
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [ecossistema](docs/ecossistema.md) | o que é deste sistema, do assessor e das outras ferramentas, e o que cada uma precisa entregar |
| [roadmap](docs/roadmap.md) | o que está pronto e o que falta para entrar em operação |
| [modelo operacional](docs/modelo-operacional.md) | o cargo de assessor item por item, o material de cada compromisso, capacidade |
| [raio-x do funil](docs/raio-x-do-funil.md) | funil padrão, perdas por categoria, maior vazamento, marketing × comercial |
| [métricas](docs/metricas.md) | dicionário de métricas da Trilha: definição e fórmula de cada número |
| [arquitetura](docs/arquitetura/) | núcleo, Meta Ads e Google Ads |
| [integrações](docs/integracoes/) | n8n, Kommo, ClickUp e demais ferramentas |
| [decisões](docs/decisoes/) | por que as coisas são como são |
| [mudanças](CHANGELOG.md) | o que mudou em cada versão |

## Testes

```bash
python -m unittest discover -s tests -v
```

A CI roda os testes, o `validar` do exemplo e confere os fluxos do n8n a cada push.
