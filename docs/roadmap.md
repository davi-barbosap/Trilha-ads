# Roadmap — implantação

> Escopo: [ecossistema](ecossistema.md) · Quem faz o quê: [modelo operacional](modelo-operacional.md)
> Legenda: ✅ pronto · 🟡 parcialmente pronto · ⬜ a fazer

O sistema entra em operação num cliente piloto, é testado na prática e depois é estendido ao resto da carteira (só configuração: um `perfil.yaml` por cliente, nenhum fluxo novo). A lista abaixo está na ordem em que um item depende do anterior.

## Pronto

- ✅ Esquema validado do `perfil.yaml` (agenda do material, freio, mapa de eventos do Kommo) e das ofertas, com o diagnóstico de aderência
- ✅ Funil padrão para todos os segmentos (`playbooks/padrao/`) e playbook imobiliário com nomes, referências e motivos de perda
- ✅ **Raio-x do funil**: etapa por etapa, primeiro contato, cadência, perdas por categoria e momento, maior vazamento, marketing entregou × comercial converteu, atribuição pelo Kommo (`python -m trilha raio-x`, `POST /funil/raio-x`)
- ✅ Calculadora de economia unitária (CAC, CPL e CPL qualificado máximos, verba por degrau)
- ✅ Leitura do Kommo com confirmação da etapa real do lead
- ✅ Conversões para o Meta (API de Conversões v26.0), com hash e deduplicação; o envio real só roda com `TRILHA_SIMULAR=0` e ainda não foi usado em produção
- 🟡 Conversões para o Google (Data Manager API): o payload está pronto e testado; o envio ainda não está implementado (item 3 abaixo)
- ✅ Regras do freio de emergência e da saúde das contas (status, dias de saldo, recarga, anúncios com problema, alertas técnicos com dono próprio, várias contas por cliente)
- ✅ Régua de métricas da Trilha ([métricas](metricas.md)), da leitura completa dos repositórios da operação: vários funis com o papel de cada um, etapas de saída, tags reais do Kommo, deduplicação de leads e vendas, canal normalizado com apelidos do cliente, custos sobre mídia paga (teto/piso), primeiro contato humano em minutos de expediente, SDR × closer, perfil e distribuição por pessoa, chegada dos leads por hora, reativação, leads parados e base velha, sinais, correções confirmadas, comparação de períodos
- ✅ trilha-api: `/saude`, `/clientes`, `/validar`, `/calcular`, `/conversao`, `/freio/avaliar`, `/funil/raio-x`, `/contas/saude`, com segredo de webhook por cliente
- ✅ Fluxos-modelo do n8n: W01 (conversão real) e W10 (vigia de falhas), em `n8n/modelos/`; nenhum fluxo está importado num servidor
- ✅ Infraestrutura descrita em `infra/` (n8n 2.x, Postgres, Redis, trilha-api, HTTPS, backup)
- ✅ 96 testes e verificação automática no GitHub

## Para entrar em operação

| # | Item | Material que passa a ficar pronto | Pronto quando | Status |
|---|---|---|---|---|
| 1 | **Servidor autohospedado** do n8n + **W10** vigia de falhas | — (base) | `/saude` responde; uma falha forçada chega no Slack; um backup é restaurado | 🟡 tudo escrito; falta o servidor |
| 2 | **Kommo do piloto no padrão** (funis cadastrados com papel, funil padrão, motivos de perda nativos obrigatórios, responsável, campos de rastreamento) + **W01** conversão real (Meta) | todos | `lead_qualificado` aparece no Gerenciador de Eventos, primeiro com `META_TEST_EVENT_CODE`, depois em produção | 🟡 falta configurar o Kommo do piloto e importar o W01 |
| 3 | Envio ao Google (Data Manager API) + **W02** coleta diária, incluindo o **histórico de etapas, o primeiro contato humano, as tarefas de reunião e as tags do Kommo** que alimentam o raio-x | dossiê, relatório | `validateOnly` aceito, depois envio real; raio-x do piloto gerado com dados reais às 05:30 | 🟡 payload e cálculo do raio-x prontos; falta a coleta |
| 4 | **W03** urgências + freio + saúde das contas, **W04** pacing, **W05** leitura diária | monitoramento | uma pausa de teste com aviso e desfazer; leitura diária no Slack às 07:30 | 🟡 regra do freio pronta |
| 5 | **W12** dossiê de otimização (com o raio-x da semana) + histórico de alterações | otimização semanal | o assessor faz a sessão do piloto só com o dossiê | ⬜ |
| 6 | **W06** execução do aprovado (ClickUp) | otimização semanal | uma mudança aprovada é executada e desfeita em teste | ⬜ |
| 7 | **W07** números do relatório semanal | relatório semanal | relatório do piloto na véspera, com marketing entregou × comercial converteu, perdas por categoria, criativos e ações | ⬜ |
| 8 | **W08** pacote de dados do briefing | briefing de criativo | um briefing do piloto escrito sobre o pacote | ⬜ |
| 9 | **W11** pacote da reunião + **W14** painel da carteira | reunião mensal, alinhamento com a equipe | uma reunião preparada em ≤ 15 min; painel na véspera da reunião de equipe | ⬜ |
| 10 | Entrada dos demais clientes | tudo | perfis válidos em `/clientes`; material de todos chegando na véspera | ⬜ |

## Antes de operar, sem depender do n8n

- ⬜ **Raio-x por código da célula** (`utm_content` = `PT01`…): leads, qualificados e vendas por criativo, e o gasto por anúncio quando houver coleta. Hoje o lead já chega com o código, mas o raio-x agrupa só por campanha. É o que permite concluir as hipóteses do briefing (PT01 contra PT02).
- ⬜ Ler `landing_page` e `event_id_lead`, que a Trilha-LP já grava no Kommo: raio-x por versão de página e deduplicação do `Lead` com o do navegador.
- ⬜ Validar o `marca.yaml` que o Trilha-briefing exporta (hoje chega e não é lido).

## Depois de operar

Sem prazo. Cada item entra quando a operação mostrar que vale a pena.

- Taxonomia de ângulos e renomeação dos anúncios existentes (o material passa a dizer "qual argumento converte").
- Subida de campanhas e anúncios aprovados pelo assessor.
- Auditoria de onboarding automatizada (Meta, Google, desperdício em termos de pesquisa).
- Varredura de termos de pesquisa do Google como ponto de atenção no dossiê.
- Painel MTD no Looker Studio e calendário sazonal.
- Estatística avançada (quando algum cliente tiver 20+ conversões por dia) e vencedores por argumento.
- Novos segmentos e plataformas (TikTok, LinkedIn). A carteira já tem automotivo e hotelaria: playbooks desses segmentos a partir dos relatórios de cada cliente.
- Alinhar os painéis de mensuração por cliente ao [dicionário de métricas](metricas.md) e, depois, fazê-los ler os dados do sistema.

## Em paralelo (fora deste repositório)

BotConversa · GA4/GTM · disparos em massa · fluxos de CRM no Kommo · captura de tarefas no ClickUp. Diagnóstico e estratégia: [Trilha-briefing](https://github.com/davi-barbosap/Trilha-briefing). Copy dos anúncios: [Trilha-copy](https://github.com/davi-barbosap/Trilha-copy). Landing pages: [Trilha-LP](https://github.com/davi-barbosap/Trilha-LP). Ver [ecossistema](ecossistema.md).
