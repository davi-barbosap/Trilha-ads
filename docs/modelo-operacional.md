# Modelo operacional — quem faz o quê

> Escopo do sistema e ferramentas paralelas: [ecossistema](ecossistema.md) · Técnico: [núcleo](arquitetura/nucleo.md) · Orquestração: [n8n](integracoes/n8n.md)
> Decisões: [ADR-002](decisoes/002-n8n-orquestrador.md) (n8n), [ADR-006](decisoes/006-freio-de-emergencia.md) (freio), [ADR-007](decisoes/007-escopo-do-sistema.md) (escopo)

## 1. Princípio

**O sistema executa o trabalho manual. O assessor pensa, decide e se relaciona com o cliente.**

O Trilha deixa pronto, na véspera, o material de cada compromisso do assessor: dados coletados, conferidos com o Kommo, comparados com a meta, organizados e com as contas feitas. O que fazer com isso é decisão do assessor.

## 2. O cargo e o sistema

Responsabilidades e indicadores do cargo de Assessor de Marketing, e o que o sistema faz em cada um:

| No cargo | O assessor | O sistema |
|---|---|---|
| **Gestão de tráfego** — criação, otimização e monitoramento (Meta, Google) | decide tudo na sessão semanal; cria campanhas e anúncios | coleta, pacing, urgências, freio; dossiê da sessão; executa o que for aprovado |
| **Copy & briefing** — briefings para criação com base em dados | escreve a estratégia do briefing e a copy | pacote de dados do briefing (o que converte, o que cansou, objeções e motivos de perda) |
| **Relatórios** — análises semanais e mensais com insights | escreve os insights e apresenta | números e gráficos do relatório semanal (leads · criativos · ações) e do pacote mensal |
| **Atendimento** — principal ponto de contato | **100% humano** | — |
| **CRM** — jornada do lead no funil | acompanha e cobra o time comercial do cliente | **raio-x do funil**: etapa por etapa, primeiro contato, cadência, perdas por categoria, maior vazamento, marketing × comercial |
| **Automações** — fluxos de CRM, disparos, landing pages | configura | **fora deste sistema** — ferramentas paralelas ([ecossistema](ecossistema.md)) |
| KPI: 1 otimização semanal por cliente | faz | dossiê na véspera |
| KPI: ≥ 1 reunião mensal por cliente | conduz | pacote dois dias úteis antes |
| KPI: feedbacks semanais (leads, criativos, ações) | dá o feedback | o relatório semanal traz os números dos três blocos |
| KPI: ≥ 3 contatos proativos por cliente por semana | **faz, sem participação do sistema** | — |
| KPI: tempo de resposta no grupo ≤ 2 h | **faz, sem participação do sistema** | — |
| KPI: 100% das tarefas no ClickUp no mesmo dia | registra | **fora deste sistema** — automação paralela no n8n |

**O sistema nunca:** fala com o cliente · escreve mensagem, roteiro ou estratégia · decide verba, estrutura ou criativo · altera uma conta sem aprovação (exceto o freio, §4) · mede ou cobra o contato do assessor com o cliente.

## 3. O que fica pronto para cada compromisso

### 3.1 Sessão semanal de otimização (por cliente)

**Dossiê de otimização**, na véspera do `operacao.dia_otimizacao`, como tarefa no ClickUp:

| Bloco | Conteúdo |
|---|---|
| Placar | vendas e valor vendido, custo por comparecimento e por venda, e o funil **pelo Kommo**, contra a meta vigente do perfil; pacing do mês |
| **Raio-x do funil** | maior vazamento da semana e passagens abaixo da referência, com quanto custam em vendas e R$ — lido **antes** de qualquer ponto de atenção de mídia ([raio-x do funil](raio-x-do-funil.md)) |
| O que mudou | alterações na conta desde a última sessão (nossas, do cliente, da plataforma) e o que veio depois |
| Decisões anteriores | o que foi aprovado na semana passada e o efeito observado |
| Pontos de atenção | 3 a 5 achados ordenados por R$ em jogo, cada um com os números que o sustentam e a simulação das ações possíveis |
| Testes em andamento | amostra atual × mínima, previsão de conclusão |
| Freio | o que foi pausado na semana e por quê |
| Time comercial do cliente | primeiro contato (minutos de expediente, só mensagem humana), cadência, conversão, carteira parada e distribuição de leads por responsável; chegada dos leads fora do horário; qualificados perdidos por motivo de lead (critério a revisar) |
| Mídia sem retorno | conjuntos e anúncios com gasto e nenhum lead na semana; anúncios reprovados ou com problema de entrega; idade de cada criativo ativo (data de criação no Meta) contra o ciclo do perfil |

**O assessor** decide o que fazer. Mudanças simples (orçamento, pausar/ativar) ele marca na tarefa e o sistema executa, registra e guarda como desfazer. Campanhas e anúncios novos, ele cria.
**Tempo-alvo:** 30–45 min por cliente.

### 3.2 Relatório semanal ao cliente

**Números do relatório**, na véspera do `operacao.dia_relatorio`, em três blocos — os mesmos três tipos de feedback que o cargo pede:

| Bloco | Números |
|---|---|
| **Leads** | semana atual contra a anterior (semanas da Trilha: w1 = 1–7, w2 = 8–14, w3 = 15–21, w4 = 22–fim); dois lados, explícitos: **marketing entregou** (leads, qualificados, agendamentos e custo de cada um) e **comercial converteu** (prazo de primeiro contato, comparecimento, propostas, vendas, valor vendido); perdas por etapa e por categoria (lead, atendimento, comercial, externo); maior vazamento; comparação com a semana anterior e com a meta |
| **Criativos** | desempenho por anúncio e por argumento; o que está cansando; o que entrou e saiu |
| **Ações** | o que foi feito na conta na semana (do histórico de alterações) e o resultado até agora |

**O assessor** escreve os insights, decide o formato e entrega. O sistema não envia nada ao cliente.
**Tempo-alvo:** 15 min por cliente.

### 3.3 Briefing de criativo

**Pacote de dados do briefing**, junto com o dossiê e sob demanda:
- argumentos (eixos), públicos e formatos com melhor e pior resultado;
- criativos que estão cansando, por desempenho e por idade (dias no ar);
- objeções e motivos de perda registrados no Kommo;
- sinais de risco do diagnóstico de aderência da oferta (ex.: vendas fracas fora do digital pedem nutrição mais longa, prova social mais robusta e contorno de objeção já no criativo);
- diferenciais e objeções da oferta (`ofertas/*.yaml`);
- o modelo de briefing do time de criação com esses campos preenchidos.

**O assessor** escreve a estratégia: o ângulo, a mensagem, o pedido ao time de criação.
**Tempo-alvo:** 20–30 min por briefing.

### 3.4 Reunião mensal

**Pacote da reunião**, dois dias úteis antes, no formato do relatório mensal da Trilha:

0. Conferência dos dados: fontes e data de cada coleta; conjuntos e anúncios com gasto e nenhum lead (e a % da verba); % sem score; vendas sem valor ou sem contato; duplicatas removidas; % sem atribuição; correções confirmadas aplicadas
1. Resumo executivo (placar: leads, qualificados, reuniões agendadas e realizadas, propostas, vendas, investimento, valor vendido; a leitura é do assessor)
2. Funil por semana (w1–w4) com as perdas de cada semana e as taxas contra a meta do cliente, dizendo a base de cada meta (÷ leads ou ÷ etapa anterior)
3. Indicadores financeiros com as fórmulas: investimento, CPL (diagnóstico, sobre o investimento de captação), CPL qualificado, CPO por canal, custo por venda (teto), retorno (piso), valor vendido, ticket
4. Desempenho por público, por criativo e por público × criativo, com a linha "sem atribuição"
5. Qualidade dos leads por score, com "sem score"
6. Vendas fechadas no mês e a jornada de cada uma no CRM (primeiro card → fechamento → venda, com datas e dias; canal)
7. Bloco "sem atribuição": não rastreado e canais sem gasto medido, em linhas separadas
8. Raio-x do funil do mês por campanha, por SDR e por closer
9. Testes, decisões do mês e efeito
10. Números de apoio para as recomendações (escalar · pausar · investigar e corrigir dados) e para as metas do mês seguinte, incluindo a % de atribuição

Definições em [métricas](metricas.md). Sai como documento ou slides para o assessor completar.

**O assessor** prepara a narrativa, conduz e registra os combinados. (Transformar a ata em tarefas é da automação paralela de captura de tarefas.)

### 3.5 Alinhamento com a equipe

**Painel da carteira**, na véspera da reunião de equipe: semáforo por cliente (dentro da meta · atenção · crítico), **saúde das contas de anúncio** (status, dias de saldo pré-pago e recarga sugerida, anúncios com problema — P1 resolver hoje, P2 esta semana; um cliente pode ter várias contas), maior vazamento de cada cliente, leads parados (janela fixa de 45 dias), freio acionado na semana, tarefas atrasadas por pessoa e criativos pendentes (lidos do ClickUp), tokens de integração perto de vencer. Alertas de conta são do assessor; alertas técnicos (credencial recusada, conta fora do acesso, coleta ou material sem atualizar, coleta com zero leads quando o período anterior teve) são do responsável técnico. O painel confere o conteúdo, não só se o fluxo rodou: o painel antigo mostrava verde com zero leads e Meta vazio, e um token quebrado virava 23 avisos separados.

## 4. Freio de emergência

A única ação sem aprovação prévia ([ADR-006](decisoes/006-freio-de-emergencia.md)). Protege a verba entre as sessões semanais, à noite e no fim de semana.

| Gatilho | Padrão (configurável no `perfil.yaml`) |
|---|---|
| Gasto sem lead | campanha gastou ≥ 3× o CPL máximo desde o último lead |
| Rastreamento quebrado | campanha gastando há ≥ 6 h sem nenhum evento de conversão |

| Modo | Comportamento |
|---|---|
| **`pausar` (opção A, padrão)** | pausa, avisa o assessor na hora com o motivo e o botão de desfazer |
| `avisar` (opção B) | só avisa |

Reativar é sempre decisão do assessor.

## 5. Capacidade (estimativa realista)

Horas do assessor por cliente por semana:

| Atividade | Sem o sistema | Com o sistema |
|---|---|---|
| Sessão de otimização (levantar dados + decidir) | 2,5 | 0,75 |
| Execução que continua manual (criar campanhas e anúncios, subir criativos) | 0,75 | 0,75 |
| Relatório semanal (números + insights) | 1,5 | 0,25 |
| Briefing de criativo (dados + estratégia) | 1,0 | 0,4 |
| Contatos proativos (≥ 3) e respostas no grupo (≤ 2 h) | 1,0 | 1,0 |
| Reunião mensal + preparação (÷ 4,3 semanas) | 0,6 | 0,3 |
| Equipe e registro no ClickUp | 0,3 | 0,3 |
| **Total por cliente** | **≈ 7,6 h** | **≈ 3,75 h** |

- **8 clientes ≈ 30 h por semana** com o sistema, contra ~60 h sem ele.
- **Teto saudável: cerca de 10 clientes por assessor.** O sistema corta o trabalho de levantar e organizar dados; o relacionamento e a execução criativa continuam tomando tempo, e é assim que deve ser.
- Estimativas de partida, a confirmar com as horas medidas no cliente piloto.
- A carteira de hoje (catálogo do painel da carteira): 23 clientes em dois assessores, um com 16 e outro com 7 (imobiliário 17, automotivo 3, hotelaria 3). O assessor com 16 está acima do teto mesmo com o sistema.

## 6. Agenda de referência para 8 clientes

| | Manhã | Tarde |
|---|---|---|
| **Segunda** | painel da carteira + reunião de equipe | otimização: clientes 1–3 |
| **Terça** | otimização: clientes 4–6 | execução e briefings |
| **Quarta** | otimização: clientes 7–8 | execução e briefings |
| **Quinta** | relatórios semanais: clientes 1–8 | execução |
| **Sexta** | 2 reuniões mensais (4 semanas = 8 clientes) | fechamento da semana |

Contatos proativos e respostas no grupo acontecem ao longo de todos os dias. Os dias de cada cliente ficam no bloco `operacao` do `perfil.yaml`.

## 7. Faixas de serviço

Classificação pela nota de maturidade (núcleo §3.2), em `operacao.faixa`:

| Faixa | Perfil do cliente | Profundidade do material | Exigência mínima |
|---|---|---|---|
| **Essencial** | rastreamento 0–1, verba perto da mínima | placar, pacing, freio, relatório semanal | Kommo com etapas padronizadas |
| **Performance** | Kommo integrado, verba 2–5× a mínima | + conversão real, plataforma × Kommo, dados por atendente, pacote de briefing | identificador de clique em > 80% dos leads de mídia |
| **Escala** | histórico > 12 meses, verba > 5× a mínima | + testes estruturados, vencedores por argumento | volume para o modo estatístico médio (núcleo §9.0) |

## 8. Indicadores do sistema

Medem se o sistema está cumprindo o papel dele (os indicadores do cargo são do assessor):

- Horas do assessor por cliente por semana (meta ≤ 3,75 h).
- Dossiês, relatórios e pacotes entregues **na véspera** (meta 100%).
- % de leads de mídia com identificador de clique no Kommo (meta > 80%).
- % de conversões aceitas por Meta e Google sem erro.
- Falhas silenciosas (meta zero).

## 9. Papéis

| Papel | Responsabilidade |
|---|---|
| **Assessor** | tudo da coluna "o assessor" da §2 |
| **Analista** (quando houver) | criação e subida de campanhas aprovadas, organização de criativos |
| **Responsável técnico** (interno ou freelancer) | n8n, trilha-api, credenciais, backups — segue o runbook de [n8n](integracoes/n8n.md); também é o ponto de contato com quem cuida das ferramentas paralelas |
