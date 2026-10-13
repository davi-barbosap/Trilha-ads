# Origem dos padrões operacionais

Padrões extraídos das ferramentas que a operação da Trilha já usa (painéis de mensuração, relatórios comerciais, landing pages e o `briefing-trilha`) e onde cada um entrou neste sistema.

Clientes aparecem por letra (cliente A, cliente B…). O nome real de cada um fica no repositório privado de clientes ([ADR-004](decisoes/004-dados-de-clientes.md)).

## Cobertura da leitura

As 8 ferramentas abaixo foram lidas **por inteiro**, arquivo por arquivo (268 arquivos):
- **Código, documentação, configuração, HTML, CSS e fluxos:** lidos do início ao fim, inclusive os painéis grandes (painel do cliente B, 9.660 linhas; painel do cliente A, 2.940 linhas).
- **Arquivos de dados gerados** (JSON de leads, exports de salesbot em uma linha, blocos de dados embutidos nos painéis): lidos pela estrutura (chaves, tipos, contagens, exemplos).
- **Mídia** (imagens, vídeos, fontes): listada, não lida.

| Ferramenta | O que é | Padrões extraídos | Onde entrou |
|---|---|---|---|
| Painel do cliente A (imobiliário) | Painel de mídia e funil (Kommo + Meta + Google) | dicionário oficial de métricas; vários funis com o 142 mudando de sentido; venda só no Closer, pela data de fechamento; card direto no Closer de pessoa nunca vista conta como entrada; deduplicação por pessoa e mês e de vendas por pessoa/dia/valor/produto; ticket só com vendas de valor; custo por reunião como piso; canal normalizado com "Não rastreado" e apelidos do cliente; CAC teto e ROAS piso; reunião agendada pela tarefa de reunião e realizada pela data; janela anterior do mesmo tamanho; taxa em pp e volume em %; coleta que falha alto e trava antes de publicar | [métricas](metricas.md), `crm.funis`, `funil.py`, `atribuicao.py`, `periodo.py`, [Kommo](integracoes/kommo.md) §3 |
| Painel do cliente B (imobiliário) | Painel, fluxos do salesbot, rotinas de tags e relatórios de análise | primeiro contato pela primeira mensagem **humana** (`created_by` ≠ 0; 2 de cada 3 mensagens são do bot), em horário útil; regra exata do "Interagiu"; tags reais do bot (`bot-nao-iniciado` sem acento) e prioridade entre elas; reunião realizada pela tag quando o card sai do 142; reativados pela tag `lead reativado` e variantes; régua de score da gestora do CRM (A–D) × campo do Kommo (A–F); CPL de WhatsApp separado; status de entrega dos anúncios; modelo de relatório mensal (conferência dos dados, placar, funil semanal com perdas, financeiro com fórmulas, público × criativo, score, jornada da venda, sem atribuição, recomendações com metas do mês seguinte e % de atribuição); metas do cliente com base declarada; correções confirmadas registradas | `funil.py` (primeiro contato, tags, reativação, score), `saude.py` (anúncios), [métricas](metricas.md), pacote da reunião ([modelo operacional](modelo-operacional.md) §3.4), `correcoes.py` |
| Painel de saúde da carteira | Painel interno com todos os clientes, por assessor | catálogo de clientes por segmento e assessor; várias contas por cliente e conta compartilhada; saldo pré-pago lido do `funding_source_details`; dias de saldo, recarga de 30 dias, P1/P2; dono do alerta (assessor × responsável técnico); falha silenciosa (um token quebrado vira dezenas de avisos; relatório verde com zero leads) | `saude.py` (status corrigidos, alertas técnicos, credencial como alerta único), `Meta.ad_account_ids`, painel da carteira |
| Ranking de corretores (cliente C) | Ranking de corretores para TV (CRM próprio do cliente) | score composto (vendas 28, conversão 20, volume 16, primeiro contato 16, movimentação 10, consistência 10; nota relativa ao time, empate 50, sem dado = pior); leads parados há mais de 15 dias numa janela fixa de 45 dias; baldes do sistema; qualificador × corretor; primeiro contato até a qualificação, descartando valores fora de 0–30 dias | perfil por pessoa, leads parados, `por_closer`, primeiro contato. A amostra mínima (SDR 20, closer 5) é regra do Trilha: o ranking não tem |
| Relatório comercial (cliente D) | Relatório a partir de planilhas de corretores + Meta | status livres normalizados; motivos categorizados ("lead repetido" é dado, não perda); plano de ação por regra ("não responde" > 30% → resgatar a base antes de aumentar volume e revisar o primeiro toque); ciclo de 30 dias por criativo | sinais do raio-x, categoria `duplicado`, idade do criativo no dossiê |
| Painel comercial (cliente E) | Painel comercial (CRM próprio do cliente + Meta) | carteira parada e base velha por pessoa; equilíbrio da distribuição de leads (1,6× / 0,5× a média); balde da empresa e gestor fora da média; chegada dos leads por hora e dia da semana; CPL sem as campanhas de topo de funil; mês corrente comparado do dia 1 ao dia D; plano de ação semanal (regras) | distribuição, `crm.baldes`/`gestores`, chegada dos leads, investimento de captação, `periodo.py`, sinais |
| Landing page de referência (cliente F) | Landing page estática | captura de UTMs e identificadores de clique com esquema fixo; "o último clique com campanha na sessão vence" em `sessionStorage`; `(referral)` gravado para visita de outro site; evento de lead só após o webhook confirmar | contrato das landing pages ([ecossistema](ecossistema.md) §3), canal "Outro site" |
| `briefing-trilha` | Wizard de briefing de empreendimento → fluxos do Kommo → ClickUp | estrutura e variáveis do ClickUp; 9 seções do briefing e o mapa para `ofertas/*.yaml`; tags e etapas que os fluxos aplicam (Interesse Confirmado, lead frio, não-cadastrou, reativado, atendimento humano); "Interesse Confirmado" não é qualificação; etapas de saída que não são o 143 | [ClickUp](integracoes/clickup.md), `crm.tags`, `mapa_eventos[].motivo`, esquema da oferta, [ADR-005](decisoes/005-dependencia-briefing-trilha.md) |

## Onde o Trilha corrige a operação

A leitura também mostrou regras dos painéis que divergem do dicionário. O Trilha segue o dicionário; os painéis devem ser alinhados:
- CPL e CAC sobre **todos** os leads e vendas, e não só os de mídia: superestimam o retorno quando poucas vendas são atribuídas.
- Funil pela foto do momento e taxa sobre a base inicial: subestimam as etapas do meio.
- Deduplicação só por telefone no período inteiro, ou nenhuma deduplicação.
- Coleta que engole erro e publica zero, ou publica gasto parcial.
- Janela anterior com um dia a mais e ROAS mensal com receita de todos os canais ÷ gasto só do Meta.
- `(referral)` tratado como indicação; origem "trilha-performance" fora do Meta.
- Semanas começando na segunda e ciclo de vendas pela média.

## Fora do Trilha, para os responsáveis pelos painéis

Os achados de segurança e de rastreamento de cada painel foram passados diretamente a quem cuida deles. Em resumo, o que todo painel e toda página publicada precisam garantir:
- nenhuma senha no código de uma página pública;
- nenhum dado pessoal de lead (nome, e-mail, telefone, link do lead) em arquivo ou página pública;
- rótulos de status de conta do Meta conferidos com a documentação;
- landing pages que gravam identificadores de clique e UTMs em campo próprio e enviam o lead ([ecossistema](ecossistema.md) §3).

## Também observado (fora do escopo)

- Outros CRMs na carteira (CRMs imobiliários próprios, planilhas). O sistema segue só com Kommo ([ADR-007](decisoes/007-escopo-do-sistema.md)); os padrões de normalização valem para quando outro CRM for necessário.
- Rotinas de tags, salesbots, disparos (Mailchimp) e landing pages rodam como ferramentas paralelas; o raio-x lê o resultado.
- Painéis por cliente publicados na web: são a camada de relatório existente e devem seguir o mesmo [dicionário de métricas](metricas.md).
