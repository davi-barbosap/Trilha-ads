# Integração ClickUp

> Quem faz o quê: [modelo operacional](../modelo-operacional.md) · Escopo: [ecossistema](../ecossistema.md) · Fluxos: [n8n](n8n.md) (W06, W07, W08, W11, W12, W14)
> Princípio: o ClickUp é **a mesa de trabalho do assessor**. O material que o sistema prepara chega como tarefa; a decisão do assessor é tomada na tarefa. O Trilha não tem tela própria.

## 1. Espaço padrão

Segue a estrutura que a Trilha já usa (a mesma das ferramentas da equipe): um **espaço de clientes** com **uma pasta por cliente** e a lista padrão **"Operação"**. As listas abaixo são as que o sistema usa dentro da pasta de cada cliente; o ID do espaço vai em `CLICKUP_CLIENTS_SPACE_ID`. Cliente sem pasta (uma lista só) é aceito com `CLICKUP_CLIENT_MODE=list`; itens arquivados são ignorados.

```
Espaço de clientes
├── Pasta por cliente
│   ├── Lista "Operação"             ← lista padrão da equipe
│   ├── Lista "Otimização semanal"   ← um dossiê por semana (W12)
│   ├── Lista "Relatório semanal"    ← números da semana em três blocos (W07)
│   ├── Lista "Briefings"            ← pacote de dados do briefing (W08)
│   ├── Lista "Reuniões"             ← pacote da reunião mensal (W11)
│   └── Lista "Testes"               ← protocolo de testes (núcleo §9.4)
├── Lista "Carteira"                 ← painel da carteira para a reunião de equipe (W14)
└── Lista "Decisões"                 ← o que o assessor decidiu → o que aconteceu, todas as contas
```

A tarefa de onboarding criada na "Operação" ("Briefing — <oferta>", tags `briefing` e `imobiliário`, um JSON de fluxo anexado por fluxo) é diferente do pacote de dados do briefing de criativo, que vai para "Briefings". Quem lê o ClickUp (painel da carteira) distingue as duas pela lista.

Demais listas da operação (demandas do cliente, criação, onboarding) seguem o padrão da equipe e são alimentadas pela **automação paralela de captura de tarefas** ([ecossistema](../ecossistema.md)), não por este sistema.

## 2. Sessão semanal de otimização (W12 → W06)

```
Véspera do dia_otimizacao, 16:00 — W12 cria "Otimização · <cliente> · semana NN"
  descrição: placar, mudanças, decisões anteriores e efeito, pontos de atenção (com números e simulação),
             testes, freio, funil do cliente

Na sessão, o assessor decide. Para mudanças simples (orçamento, pausar, ativar), cria uma subtarefa
pelo modelo "Ação" (plataforma, entidade, mudança) e muda o status para "Aprovado":
  W06 confere a assinatura do webhook do ClickUp e se a entidade ainda está no estado "antes";
      executa, registra no histórico de alterações e comenta o resultado.
  Se a conta mudou entre o dossiê e a aprovação, não executa e devolve a subtarefa com a diferença.
Campanhas e anúncios novos o assessor cria direto nas plataformas (subida pelo sistema: evolução futura, ver roadmap).
```

## 3. Relatório semanal (W07)

Tarefa "Relatório · <cliente> · semana NN", criada na véspera do `dia_relatorio`, com os números e gráficos em três blocos — **leads**, **criativos**, **ações**. O assessor escreve os insights no campo "Leitura do assessor", escolhe o formato e entrega ao cliente pelo canal dele. O sistema não envia nada.

## 4. Briefing de criativo (W08)

Junto com o dossiê, ou quando o assessor muda uma tarefa da lista "Briefings" para "Gerar pacote": dados do que converte e do que cansou, objeções e motivos de perda, diferenciais da oferta, e o modelo de briefing do time de criação com esses campos preenchidos. A estratégia (ângulo, mensagem, pedido) é escrita pelo assessor; depois a tarefa segue o fluxo normal da equipe de criação.

## 5. Reunião mensal (W11)

Tarefa "Reunião mensal · <cliente> · <mês>", dois dias úteis antes, com o pacote (documento ou slides com os dados). A narrativa e a condução são do assessor. Os combinados viram tarefas pela automação paralela de captura.

## 6. Painel da carteira (W14)

Tarefa semanal em "Carteira": semáforo por cliente, freio acionado na semana, tarefas atrasadas por pessoa e criativos pendentes (lidos das listas da equipe), tokens de integração perto de vencer. Alertas de conta vão para o assessor do cliente; alertas técnicos (credencial, coleta, acesso a conta, material atrasado) vão para o responsável técnico (`TRILHA_RESPONSAVEL_TECNICO`), agrupados: credencial recusada é uma linha, não uma por cliente.

## 7. Implementação

API v2 do ClickUp (`https://api.clickup.com/api/v2`) com o token no cabeçalho `Authorization`, sem "Bearer". Variáveis iguais às das ferramentas da equipe: `CLICKUP_API_TOKEN`, `CLICKUP_TEAM_ID`, `CLICKUP_CLIENTS_SPACE_ID`, `CLICKUP_CLIENT_MODE`, `CLICKUP_DEFAULT_LIST_NAME`. Webhooks do ClickUp com assinatura conferida (`CLICKUP_WEBHOOK_SECRET`). Lista procurada pelo nome (sem diferenciar maiúsculas); se não existir, o fluxo **para e avisa**, nunca publica na primeira lista da pasta (a ferramenta de onboarding anterior fazia esse fallback e podia publicar no lugar errado). Os gatilhos rodam nos fluxos do n8n ([n8n](n8n.md)); a decisão de executar (estado "antes" igual, valor dentro do teto contratado) passa pela trilha-api.
