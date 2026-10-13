# Trilha

Sistema que executa o trabalho manual por trás dos serviços de mídia paga (Meta Ads e Google Ads) da Trilha, para que o assessor de marketing gaste o tempo dele pensando, decidindo e cuidando do cliente.

## O que é

Um assessor que atende vários clientes passa boa parte da semana em tarefas braçais: abrir o Gerenciador de Anúncios e o Google Ads, copiar números, conferir no Kommo quantos leads realmente viraram oportunidade, montar planilhas, comparar com a meta, levantar dados para o briefing e preparar a reunião do mês.

O Trilha faz esse trabalho. Ele **não pensa a estratégia, não decide verba e não fala com o cliente** — isso é do assessor.

## A régua da Trilha

A maioria das operações olha para as duas pontas: quantos leads entraram e quantas vendas saíram. O que acontece no meio é tratado no achismo — e é aí que se decide aumentar verba quando o vazamento está no atendimento, ou cobrar o marketing por venda quando ele já entregou volume, qualidade e visita.

Por isso o Trilha mede **o funil inteiro, etapa por etapa**, e trata **venda e valor vendido como resultado**. CPL é diagnóstico: custo por lead baixo com lead que não fecha é prejuízo disfarçado de eficiência.

## O que faz na prática

**Todos os dias, sozinho**
- **Raio-x do funil.** Para cada cliente, mostra quantos leads passaram por cada etapa (novo lead → em atendimento → qualificado → agendado → compareceu → proposta → venda), quanto tempo o time comercial do cliente leva para o primeiro contato (só conta mensagem de uma pessoa, não do bot, em horário de expediente), quantas tentativas faz antes de desistir, onde e por que os leads são perdidos — separando perda por qualidade do lead, por atendimento, comercial ou externa — e **qual etapa está vazando mais vendas e quanto isso custa em R$**. Mostra lado a lado o que o **marketing entregou** e o que o **comercial converteu**, separa SDR e closer, compara as pessoas do time (perfil, distribuição de leads, carteira parada), mostra a que horas os leads chegam, aponta leads parados há mais de 15 dias e segue a régua de métricas da Trilha (a mesma pessoa conta uma vez por mês, CPL só sobre mídia paga, custo por venda como teto e retorno como piso). Entende operações com vários funis no Kommo (SDR, Closer, Nutrição), em que o "ganho" de um funil não é venda, e lê as tags reais da operação (estado do bot, reunião realizada, reativado). Vale para qualquer segmento; o imobiliário só muda os nomes (visita agendada, visita realizada).
- **Devolve a venda real para o Meta e o Google.** Quando o lead muda de etapa no Kommo (qualificado, visita, venda), o sistema avisa as plataformas. Assim elas aprendem a buscar gente parecida com quem compra, não só com quem clica.
- **Coleta e confere os números** de Meta, Google e Kommo, e acompanha se a verba do mês vai sobrar ou faltar.
- **Avisa só o que é urgente:** anúncio reprovado, campanha parada, rastreamento quebrado, conta de anúncio desativada, com pagamento pendente ou com saldo pré-pago para menos de 5 dias (com a recarga sugerida), anúncio com problema de entrega. Alerta técnico (credencial recusada, coleta parada) vai para o responsável técnico, uma vez só.
- **Freio de emergência:** se uma campanha está gastando sem trazer nenhum lead, ou com o rastreamento quebrado, pausa e avisa na hora, com um botão para desfazer. É a única coisa que o sistema faz sem pedir. Reativar é sempre decisão do assessor.

**Na véspera de cada compromisso do assessor, deixa o material pronto no ClickUp**

| Compromisso do assessor | O que o sistema deixa pronto |
|---|---|
| Otimização semanal de cada cliente | **Dossiê:** vendas e valor vendido da semana, o maior vazamento do funil, o que mudou na conta, o efeito das decisões anteriores e os pontos de atenção com os números de cada um |
| Relatório semanal ao cliente | **Números** de leads (marketing entregou × comercial converteu, perdas por categoria), criativos e ações — para o assessor escrever a leitura dele e entregar |
| Briefing para a equipe de criação | **Pacote de dados:** o que está convertendo, o que cansou, objeções e motivos de perda registrados no Kommo, riscos do diagnóstico de aderência da oferta |
| Reunião mensal com o cliente | **Pacote da reunião:** resultado do mês (vendas, valor vendido, retorno), raio-x do funil por campanha e por responsável, testes, decisões e efeitos |
| Reunião de equipe | **Painel da carteira:** situação e maior vazamento de cada cliente, freios acionados, pendências |

**Antes de anunciar,** o sistema exige o diagnóstico de aderência da oferta: quem já comprou, uso próprio ou investimento, flexibilidade de pagamento, reputação de quem entrega e como estão as vendas fora do digital. As respostas são do assessor; o sistema confere se foram dadas e leva os sinais de risco para o material.

**O que continua sendo do assessor:** estratégia, decisões de verba e criativo, criação de campanhas, contatos proativos com o cliente, respostas no grupo, a leitura dos relatórios e a condução das reuniões.

**O que fica fora deste sistema** (ferramentas paralelas): landing pages, disparos em massa, fluxos de CRM, BotConversa, GA4/GTM e a captura de tarefas no ClickUp. Ver [ecossistema](docs/ecossistema.md).

## Exemplo

Caso real da Trilha (imobiliário): **R$ 7.550 investidos, 425 leads, 4 vendas, R$ 7.084.000 em VGV.** O raio-x do exemplo em `tests/fixtures/` reproduz esses números — com etapas do meio ilustrativas — e mostra o tipo de leitura que o assessor recebe:

```
Resultado: 4 vendas · R$ 7.084.000 vendidos · retorno de 938,3× o investimento
  custo por visita realizada: R$ 302,00 · custo por venda: R$ 1.888 · CPL (diagnóstico): R$ 17,76
Primeiro contato: mediana 12 min úteis (110,5 corridos) · 74,3% dentro de 30 min úteis · 125 leads sem primeiro contato
Maior vazamento: Visita realizada (comercial) — 50,0% contra 65,0% de referência ≈ 1,2 venda(s) a menos, R$ 2.125.200
Marketing entregou: 425 leads · 120 qualificados · 50 agendamentos · R$ 62,92 por qualificado
```

## Resultado esperado

Cerca de **3,75 h de trabalho do assessor por cliente por semana**, contra ~7,6 h sem o sistema. Isso permite atender **~10 clientes por assessor** sem perder a qualidade do relacionamento ([modelo operacional](docs/modelo-operacional.md) §5).

## Situação atual

A base de código está pronta e testada: ficha validada de cada cliente e de cada oferta, cálculo de metas, raio-x do funil, conversão real para Meta e Google, regras do freio e a API que o n8n chama. Para entrar em operação falta subir o servidor autohospedado do n8n e montar os fluxos de cada material, na ordem descrita no [roadmap](docs/roadmap.md).

## Documentação

| Documento | Conteúdo |
|---|---|
| [docs/ecossistema.md](docs/ecossistema.md) | O que é do sistema, do assessor e das ferramentas paralelas — e o que as paralelas precisam entregar |
| [docs/modelo-operacional.md](docs/modelo-operacional.md) | O cargo de assessor item por item, o material de cada compromisso, capacidade, freio |
| [docs/raio-x-do-funil.md](docs/raio-x-do-funil.md) | Funil padrão, perdas por categoria, maior vazamento, marketing × comercial, padrão no Kommo |
| [docs/metricas.md](docs/metricas.md) | Dicionário de métricas da Trilha: definição e fórmula de cada número |
| [docs/origem-dos-padroes.md](docs/origem-dos-padroes.md) | De que repositório da operação veio cada padrão |
| [docs/roadmap.md](docs/roadmap.md) | O que está pronto e o que falta para entrar em operação |
| [playbooks/README.md](playbooks/README.md) | Segmentos atendidos pela Trilha, o que cada um precisa para ter playbook próprio |
| [docs/arquitetura/](docs/arquitetura/) | Núcleo, Meta Ads e Google Ads |
| [docs/integracoes/](docs/integracoes/) | n8n, Kommo, ClickUp e demais ferramentas |
| [docs/decisoes/](docs/decisoes/) | Decisões de arquitetura |

## Uso técnico

```bash
pip install -e .

python -m trilha validar clientes/_exemplo/perfil.yaml      # confere a ficha de um cliente
python -m trilha calcular clientes/_exemplo/perfil.yaml     # CAC, CPL máximos e verba por etapa
python -m trilha raio-x tests/fixtures/funil_leads.json \
  --perfil clientes/_exemplo/perfil.yaml --investimento 7550 # raio-x do funil
python -m trilha simular-webhook tests/fixtures/kommo_webhook.txt \
  --perfil clientes/_exemplo/perfil.yaml \
  --lead tests/fixtures/kommo_lead.json --contato tests/fixtures/kommo_contato.json   # o que seria enviado, sem enviar
python -m trilha servir --porta 8080                        # API chamada pelo n8n (exige TRILHA_API_TOKEN)

python -m unittest discover -s tests -v
```

## Estrutura

```
trilha/            código (API, CLI, regras, integrações)
tests/             testes
docs/              documentação
n8n/modelos/       fluxos-modelo do n8n
infra/             servidor: Docker, n8n, Postgres, Redis, HTTPS, backup
playbooks/         funil padrão (todos os segmentos) e padrões do imobiliário
clientes/_exemplo/ ficha de cliente de exemplo — clientes reais ficam em repositório privado
```

Segredos: copiar `.env.example` para `.env` (uso local) ou `infra/.env.example` e `infra/kommo.env.example` (servidor). Nenhum `.env` é versionado.
