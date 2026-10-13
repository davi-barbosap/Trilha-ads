# Arquitetura — Núcleo

> **Escopo:** [ecossistema](../ecossistema.md) · **Quem faz o quê:** [modelo operacional](../modelo-operacional.md) — ambos prevalecem sobre este documento em caso de conflito.
> Este documento reúne tudo o que é **comum a todas as plataformas**: estratégia, onboarding, perfil do cliente, brand kit, playbooks de segmento, conversão real, motores estatísticos, governança.
> Módulos específicos: [Meta Ads](meta-ads.md) · [Google Ads](google-ads.md)
> Status de implantação: [roadmap](../roadmap.md) · Métricas: [dicionário](../metricas.md) · Decisões: [`docs/decisoes/`](../decisoes/) · Integrações: [`docs/integracoes/`](../integracoes/)
> Diagnóstico, estratégia e cadastro do cliente: [Trilha-briefing](https://github.com/davi-barbosap/Trilha-briefing) ([ADR-005](../decisoes/005-cadastro-pelo-trilha-briefing.md)). Copy dos anúncios: [Trilha-copy](https://github.com/davi-barbosap/Trilha-copy). Landing pages: [Trilha-LP](https://github.com/davi-barbosap/Trilha-LP).

## 1. Princípios

1. **Núcleo fixo, personalização por dados.** Nenhuma regra, meta ou número de cliente vive no código do núcleo.
2. **Negócio antes da conta de anúncios.** Metas derivam da economia unitária do cliente, não de chute.
3. **Opera com dado incompleto.** O sistema se ajusta ao nível de maturidade do cliente em vez de exigir tudo preenchido.
4. **Cálculo em código, nunca "de cabeça".** O modelo interpreta e recomenda; Python/R calcula.
5. **Conversão real acima da métrica da plataforma.** Resultado é venda e valor vendido; CPL é diagnóstico.
6. **Concretude obrigatória.** Copy sem número, fato ou nome próprio é barrada.
7. **Coerência do funil inteiro.** Anúncio → landing page → WhatsApp → atendimento comercial falam a mesma coisa. Este sistema cuida do lado dos anúncios e dos dados; páginas e atendimento são ferramentas paralelas que usam a mesma fonte (`marca.yaml`, `ofertas/`).
8. **Leitura livre, escrita com aprovação**, com simulação prévia e possibilidade de reversão. Única exceção: o freio de emergência (§10).
9. **Respeito ao algoritmo.** Menos mexidas, mais bem fundamentadas; proteção da fase de aprendizado.
10. **Filtro humano obrigatório** em toda decisão que envolva verba ou promessa ao consumidor.
11. **O sistema executa o trabalho manual; o assessor pensa, decide e se relaciona.** O sistema não fala com o cliente, não escreve mensagem, roteiro ou estratégia, e não mede o contato do assessor com o cliente.
12. **Funil é o raio-x da operação.** O meio do funil é medido etapa por etapa, com o que o marketing entregou separado do que o comercial converteu ([raio-x do funil](../raio-x-do-funil.md)).

## 2. Visão geral das camadas

```
┌──────────────────────────────────────────────────────────────┐
│ CAMADA 0 — DIAGNÓSTICO E ESTRATÉGIA (onboarding)             │
│  economia unitária · maturidade · auditoria · plano 90 dias  │
└──────────────────────────────┬───────────────────────────────┘
┌──────────────────────────────▼───────────────────────────────┐
│ CONECTORES   Meta (API) · Google Ads API · Data Manager API ·│
│              Kommo · ClickUp · (GA4: ferramenta paralela)    │
└──────────────────────────────┬───────────────────────────────┘
┌──────────────────────────────▼───────────────────────────────┐
│ CAMADA 1 — NÚCLEO                                            │
│  normalização · motores · estatística · histórico de         │
│  alterações · conversão real · saídas · registro de decisões │
└──────────────────────────────┬───────────────────────────────┘
┌──────────────────────────────▼───────────────────────────────┐
│ CAMADA 2 — CLIENTE = playbook do segmento + respostas do     │
│  onboarding + ajustes   (perfil · marca · ofertas · avatares)│
└──────────────────────────────┬───────────────────────────────┘
┌──────────────────────────────▼───────────────────────────────┐
│ CAMADA 3 — REGRAS DERIVADAS (calibração automática)          │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 Infraestrutura (decidida)

| Peça | Decisão | Registro |
|---|---|---|
| Armazenamento | Postgres gerenciado para eventos, alterações e decisões; BigQuery para histórico de mídia (transferência nativa do Google Ads, exportação do Meta) | [ADR-001](../decisoes/001-armazenamento.md) |
| Orquestração | n8n no próprio servidor (modo fila) agenda e conecta; trilha-api decide o que custa dinheiro ou envolve dado pessoal | [ADR-002](../decisoes/002-n8n-orquestrador.md) · [n8n](../integracoes/n8n.md) |
| Painel | Looker Studio sobre BigQuery (padrão); Metabase se o cliente exigir login próprio | [ADR-003](../decisoes/003-painel.md) |
| Dados de clientes | Fora do repositório de código: repositório privado `trilha-clientes` ou banco; aqui só `clientes/_exemplo/` | [ADR-004](../decisoes/004-dados-de-clientes.md) |
| Esquema comum | Tabela `fato_midia` diária (data, plataforma, conta, campanha, conjunto/grupo, anúncio, etiquetas da taxonomia, gasto, impressões, cliques, conversões por evento) e `fato_eventos_crm` (lead, evento, data, origem, IDs de clique) | §7 e `trilha/` |
| Validação de configuração | Todo YAML de cliente é validado por esquema (`python -m trilha validar`) antes de ligar qualquer módulo | `trilha/core/perfil.py` |

## 3. Camada 0 — Diagnóstico e estratégia

Roda no onboarding de todo cliente e é revisada a cada trimestre. **As decisões são tomadas e registradas no [Trilha-briefing](https://github.com/davi-barbosap/Trilha-briefing)** (economia, maturidade, estratégia, marcos, hipóteses). Este sistema usa o resultado: a calculadora é a mesma nos dois (um teste de contrato confere que os números batem), a aderência da oferta é conferida pelo `validar` e a auditoria técnica é deste sistema (ainda a fazer).

### 3.1 Calculadora de economia unitária (matemática reversa)

**Primeiro passo: qual é a receita real de uma venda.** O campo `modelo_receita` evita o erro mais caro do onboarding — usar o preço do produto como se fosse receita.

| `modelo_receita` | Receita bruta por venda | Exemplo |
|---|---|---|
| `venda_direta` | ticket médio | curso de R$ 3.000 |
| `comissao` | valor médio do bem × % de comissão × participação do cliente na comissão | imóvel de R$ 450.000 × 5% × 50% = **R$ 11.250** (não R$ 450.000) |
| `recorrencia` | mensalidade × meses médios de retenção (LTV) | R$ 300 × 14 meses = R$ 4.200 |

| Entrada | Exemplo imobiliário |
|---|---|
| Receita bruta por venda (acima) | R$ 11.250 |
| Margem de contribuição sobre a receita | 50% |
| % da margem que aceita investir em aquisição | 50% |
| Taxa de fechamento (lead → venda) | 1% |
| Taxa de qualificação (lead → lead qualificado) | 25% |
| Taxa de agendamento (lead → visita/reunião) — opcional | 5% |

Saídas derivadas (implementadas em `trilha/core/economia.py`):
- **CAC máximo** = receita bruta × margem × % investível → R$ 2.812
- **CPL máximo** = CAC máximo × taxa de fechamento → R$ 28
- **CPL qualificado máximo** = CAC máximo × (fechamento ÷ qualificação) → R$ 112
- **Custo máximo por agendamento** = CAC máximo × (fechamento ÷ agendamento) → R$ 562
- **Verba mensal por degrau da escada de otimização** = eventos semanais para sair do aprendizado (padrão 50, configurável) × custo máximo do evento × 4,35 semanas
  - `lead` → R$ 6.115 · `lead_qualificado` → R$ 24.459 · `agendamento` → R$ 122.294 · `venda` → R$ 611.468
- **Verba mínima viável** = verba do degrau `lead` (o mais barato) para **um** conjunto/campanha. Abaixo dela, o sistema recomenda uma plataforma, uma oferta, uma campanha — e avisa que os números serão de leitura lenta.
- **Degraus viáveis** = degraus cuja verba cabe na verba planejada. O sistema **diz explicitamente** ao cliente quando otimizar por lead qualificado é inviável para a verba dele (é o caso da maioria das PMEs) e aplica as alternativas da §7.2.
- **Ponto de equilíbrio** e metas por fase (aprendizado, otimização, escala).

Validação: taxa de qualificação ≥ agendamento ≥ fechamento; quando o cliente não sabe uma taxa, usa-se o padrão do playbook do segmento, marcado como **estimado** até haver dado próprio. Os padrões do playbook são conservadores (imobiliário: fechamento 1%, não 5%).

### 3.2 Nota de maturidade

Registrada no Trilha-briefing (`pesquisa.yaml`, bloco `maturidade`), com esta régua.

| Dimensão | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Rastreamento | nada | pixel/tag básico | eventos + API de Conversões/tag avançada | conversão real retornando à plataforma |
| CRM | nenhum | planilha/WhatsApp manual | CRM sem integração | CRM integrado com status de qualificação |
| Capacidade criativa | sem material | fotos/artes avulsas | produção mensal | produção recorrente + vídeo/UGC |
| Histórico de conta | conta nova | < 3 meses | 3–12 meses | > 12 meses com conversões |
| Verba | abaixo da mínima viável | na mínima | 2–5× mínima | > 5× mínima |

A nota **liga e desliga módulos** e define regras: um cliente com rastreamento 0 não recebe detector de vencedores por conversão (só por métricas intermediárias, sinalizadas como tal); um cliente com verba abaixo da mínima recebe recomendação de concentrar em uma plataforma e uma oferta.

### 3.3 Auditoria inicial

Checklist técnico por plataforma (pixel/API de Conversões, tag, eventos, estrutura, nomenclatura, políticas, acessos, histórico de reprovações), gerado automaticamente onde houver acesso de leitura. Saída: lista priorizada de correções.

### 3.4 Plano de 90 dias

O plano de cada cliente é decidido no Trilha-briefing (estratégia e marcos). As fases abaixo são a referência que ele segue.

| Fase | Duração típica | Objetivo | Meta |
|---|---|---|---|
| Fundação | semanas 1–2 | rastreamento, funil padrão e motivos de perda no Kommo, diagnóstico de aderência, primeiros criativos | conta pronta, eventos validados, Kommo no padrão |
| Aprendizado | semanas 3–6 | volume de dados, testes de ângulo, primeiro raio-x | custo por qualificado ≤ 1,3× máximo |
| Otimização | semanas 7–10 | atacar o maior vazamento do funil (mídia ou comercial), iterar vencedores | custo por qualificado ≤ máximo; vazamentos do atendimento tratados com o cliente |
| Escala | semanas 11–13 | aumentar verba com controle | manter o custo por venda com mais volume |

### 3.5 Diagnóstico de aderência da oferta

Antes de anunciar, o assessor responde as perguntas de aderência do playbook (`perguntas_aderencia`) e registra as respostas no bloco `aderencia` da oferta (§5.2): quem comprou até agora, uso próprio ou investimento, flexibilidade de pagamento, reputação de quem entrega, como estão as vendas fora do digital e a avaliação final de aderência ao digital.

- O sistema não avalia: confere se o diagnóstico foi feito (`python -m trilha validar` lista as pendências) e leva os sinais de risco para o dossiê e para o pacote de briefing.
- Produto com vendas fracas fora do digital: o digital tende a expor o problema mais rápido e mais caro. Pede nutrição mais longa, prova social mais robusta e contorno de objeção já no criativo.
- No imobiliário, alto padrão raramente converte via tráfego frio.

### 3.6 Uso da calculadora fora deste sistema

A calculadora (`python -m trilha calcular`) também serve para prospecção comercial, mas esse é um uso paralelo ([ecossistema](../ecossistema.md) §4). Aqui ela existe para as metas de cada cliente.

## 4. Onboarding flexível

### 4.1 Composição do cliente

```
cliente final = playbook do segmento  (padrões)
              + respostas do onboarding (sobrescrevem)
              + ajustes manuais        (sobrescrevem tudo)
```

Cada campo tem um nível:
- **Obrigatório** — sem ele o sistema não liga (ex.: métrica principal, conta de anúncios, oferta).
- **Recomendado** — usa padrão do playbook, marcado como `estimado`, e lembra de pedir.
- **Opcional** — enriquece, nunca bloqueia.

O sistema sempre informa **o que está usando como padrão** e qual o impacto de não ter o dado real.

### 4.2 Onboarding (ferramenta paralela)

O cadastro do cliente vem do [Trilha-briefing](https://github.com/davi-barbosap/Trilha-briefing) (`exportar --para trilha`), que grava em `Trilha-clientes/ads/<id>/`. Este sistema só exige que o resultado passe no `python -m trilha validar`. O contrato entre os dois é o esquema validado; a forma de consumo está em [ADR-005](../decisoes/005-cadastro-pelo-trilha-briefing.md). O briefing gera:

| Saída | Usada neste sistema por | Também usada por (paralelas) |
|---|---|---|
| `marca.yaml` | pacote de briefing de criativo (ainda não lido: o validar não confere este arquivo) | — |
| `ofertas/<oferta>.yaml` | diagnóstico de aderência, pacote de briefing (diferenciais, objeções) | fluxos Kommo |
| `perfil.parcial.yaml` | economia, métrica principal e verba; o assessor completa contas, Kommo e freio e salva como `perfil.yaml` | — |

Copy e páginas não passam por aqui: o briefing exporta direto para o [Trilha-copy](https://github.com/davi-barbosap/Trilha-copy) (`copy.yaml`) e para a [Trilha-LP](https://github.com/davi-barbosap/Trilha-LP) (`pagina.yaml`). Os fluxos do Kommo (salesbots e etapas) são da ferramenta paralela de fluxos de CRM.

O que o briefing ainda não exporta e o assessor preenche no `perfil.yaml`: contas e IDs das plataformas, mapa de etapas do Kommo (`crm.mapa_eventos`), regras do freio e entrega de relatórios e alertas.

### 4.3 Versionamento do perfil

Metas, ofertas e condições comerciais mudam. Cada alteração no perfil gera nova versão com data, e os relatórios comparam resultados contra a meta **vigente na época**, não a atual.

## 5. Brand kit

Hierarquia em três níveis, para qualquer segmento.

```
MARCA      identidade, voz, compliance, regras comerciais — vale para tudo
  └── OFERTA   produto/serviço/empreendimento/curso — diferenciais, objeções, condições
        └── CAMPANHA   ângulo, avatar, criativos, período
```

### 5.1 `marca.yaml`

```yaml
marca:
  nome: ""
  segmento: ""                      # aponta para playbooks/<segmento>/
identidade_visual:
  cores: { primaria: "", secundaria: "", apoio: [] }
  tipografia: { titulos: "", texto: "" }
  logo: { arquivo: "", versoes: [] }
  estilo_imagem: ""                 # ex.: fotos reais da obra; sem banco de imagem genérico
voz:
  assinatura: ""                    # marca | pessoa | marca_pessoa
  nome_pessoa: ""                   # quando assinatura inclui pessoa
  abordagem: ""                     # scripted | conversacional | misto
  pessoa_gramatical: ""             # eu | nós | impessoal (derivado da assinatura)
  tom: []                           # ex.: próximo, direto, sem gíria
  assim_sim: []                     # 3–5 exemplos reais aprovados
  assim_nao: []                     # 3–5 exemplos reprovados e por quê
  termos_obrigatorios: []
  termos_proibidos: []
atendimento:
  sla_resposta: ""                  # 30min | 2h | dia | 24h+
  handoff: ""                       # direto | bot | horario
  canais: []                        # WhatsApp, Instagram Direct...
  horario_comercial: ""
regras_comerciais:                  # o que pode aparecer em cada canal
  preco:
    anuncio: ""                     # nunca | a_partir_de | parcela | valor_cheio
    whatsapp: ""                    # padrão imobiliário: nunca valor fechado → simulação/agendamento
    landing: ""
  promessas_proibidas: []           # ex.: "aprovação garantida", "sem consulta"
compliance:
  registros_profissionais: []       # ex.: CRECI, CRM, OAB — com número e onde exibir
  categoria_especial_anuncio: null  # verificar regras da plataforma por país
  avisos_legais: []
  lgpd: { base_legal: "", politica_privacidade_url: "" }
prova_social:
  depoimentos_video: []
  depoimentos_texto: []
  numeros: []                       # ex.: "+500 famílias atendidas" — com fonte
```

Regra de derivação: a **assinatura** define a pessoa gramatical e o formato criativo preferencial. `pessoa` → primeira pessoa, criativos com o próprio profissional em vídeo; `marca` → institucional; `marca_pessoa` → apresentação pessoal com respaldo da marca.

### 5.2 `ofertas/<oferta>.yaml`

Formato que o Trilha-briefing exporta (`exportar --para trilha`):

```yaml
oferta:
  nome: ""
  tipo: ""                          # empreendimento, curso, serviço, produto
  estagio: ""                       # lançamento, em andamento, pronto, últimas vagas/unidades
  localizacao: { bairro: "", cidade_uf: "", regiao: "" }   # quando aplicável
aderencia:                          # diagnóstico antes de anunciar (§3.5) — respostas do assessor
  perfil_compradores: ""            # perfil financeiro, onde moram, o que fazem, o que motivou a compra
  finalidade: ""                    # uso_proprio | investimento | ambos
  pagamento_flexivel: null          # true | false
  pagamento_comunicavel: ""
  reputacao: ""                     # ativo | neutra | obstaculo
  reputacao_nota: ""
  vendas_fora_do_digital: { canais: [], ritmo: "", avaliacao: "" }   # boa | regular | fraca
  aderencia_digital: ""             # alta | media | baixa
  justificativa: ""
diferenciais:                       # mínimo 3 — número, fato ou nome próprio
  - ""
raridade: ""                        # diferencial único no mercado local
ancoras:                            # mínimo 3 quando localização importa — nome próprio + distância/tempo
  - ""
condicoes_comerciais:
  faixa_preco: ""
  ticket_medio: null
  pagamento: ""
  condicao_excepcional: ""          # com prazo de validade, se houver
  validade: ""
  posicionamento_preco: ""          # abaixo | média | acima dos concorrentes — e por quê
objecoes:                           # o insumo mais importante
  - eixo: ""                        # eixos definidos pelo playbook do segmento
    objecao: ""
    resposta_do_time: ""            # frase real usada ao vivo
perfil_lead:
  origem_principal: ""
  perfil: ""
  jornada_media_dias: null          # alimenta janela de atribuição e atraso de conversão
  motivo_perda: ""
assets:
  imagens: []
  videos: []
  materiais: []                     # PDFs, tabelas, plantas
```

### 5.3 Verificador de copy

Feito pelo [Trilha-copy](https://github.com/davi-barbosap/Trilha-copy), que revisa os anúncios de Meta e Google e os roteiros contra o briefing: termos e promessas proibidos, lastro de números e provas, urgência real, limites e políticas de cada plataforma, voz e intensidade. Só peça aprovada sai, com o código da célula em `utm_content`.

### 5.4 Código do criativo (liga a grade aos resultados)

Todo anúncio carrega o **código da célula** da grade do Trilha-briefing (`PT01`, `GB01`…): no nome (`PT01 | v1`) e no `utm_content`. O nome fica curto de propósito, porque é digitado à mão, e um nome com muitas etiquetas quebra.

- As características do criativo (persona, argumento, oferta, eixo, formato, gancho) ficam nos arquivos do briefing e da copy, ligadas ao código, e não no nome.
- O raio-x agrupa leads, qualificados e vendas por código (`por_criativo`). Com o gasto de cada código, mostra também os custos. O padrão do código é editável por cliente (`crm.padrao_codigo`).
- Cruzando o código com a grade, o material responde **qual argumento converte** para qual persona, e não só qual anúncio.
- Cobertura (a fazer): apontar no dossiê os eixos do segmento sem criativo ativo ou sem teste recente.

## 6. Playbooks de segmento

```
playbooks/<segmento>/
├── playbook.yaml        # eixos de objeção, métricas típicas, taxas padrão, sazonalidade,
│                        # regras comerciais padrão, compliance do setor
├── negativas.md         # palavras-chave negativas do segmento (Google)
├── avatares_base.md     # pontos de partida, refinados por cliente
├── objecoes_e_apelos.md # framework de objeção → copy
└── (fluxos de atendimento ficam na ferramenta paralela de fluxos de CRM)
```

**Imobiliário (primeiro playbook)** — arquivo em [`playbooks/imobiliario/playbook.yaml`](../../playbooks/imobiliario/playbook.yaml):
- `modelo_receita: comissao` por padrão — a receita é a comissão retida, não o valor do imóvel.
- Taxas padrão conservadoras: fechamento 1%, qualificação 25%, agendamento 5% (sempre marcadas como estimadas).
- **Portais imobiliários** (ZAP, VivaReal, OLX e similares) são fonte de lead de primeira classe: entram no Kommo com origem própria, contam no CAC total e na visão consolidada, e servem de referência de custo por lead para comparar com mídia paga.
- Eixos: preço, produto, localização — todos obrigatórios na régua.
- Regra padrão: preço pedido no WhatsApp → simulação/agendamento, nunca valor fechado. Em anúncio, configurável (ex.: valor de parcela pode filtrar lead).
- Compliance: CRECI; verificar regras de categoria especial de anúncio para habitação conforme país e plataforma.
- Fluxos de atendimento e salesbots do Kommo ficam na ferramenta paralela de fluxos de CRM.

Próximos playbooks: educação, serviço local, saúde, e-commerce — mesmo molde, com eixos próprios (ex.: educação → preço, resultado, método/tempo).

## 7. Conversão real e qualidade de lead

### 7.1 Fluxo

```
Anúncio → landing / formulário / WhatsApp
   → captura de IDs de clique e UTMs (feita pelas ferramentas paralelas — contrato em ecossistema.md §3):
       site: fbclid · gclid · gbraid/wbraid · UTMs (campos ocultos da landing; GTM)
       clique para WhatsApp: ctwa_clid (integração do WhatsApp no Kommo ou BotConversa) · site → WhatsApp: código curto na mensagem
       formulário instantâneo do Meta: lead_id do Meta
   → CRM (Kommo): lead + origem + campanha + criativo (campos personalizados padrão — ver integração Kommo)
   → mudança de etapa no funil (webhook do Kommo, com segredo próprio de cada cliente)
   → etapa confirmada lendo o lead no Kommo (webhook forjado não vira conversão)
   → mapa etapa → evento, configurado por cliente (crm.mapa_eventos no perfil.yaml)
   → (a) banco: fato_eventos_crm → painel com CPL, CPL qualificado, CAC e ROAS reais por campanha, ângulo e termo
   → (b) retorno às plataformas: Meta (API de Conversões v26.0, event_id para deduplicação) · Google (Data Manager API: gclid/gbraid/wbraid ou e-mail/telefone em hash, transactionId para deduplicação)
```

**Google: Data Manager API.** Desde 15/06/2026 a Google não aceita novos integradores no envio de conversões offline pela Google Ads API (`UploadClickConversions`); a entrada é a Data Manager API (`events:ingest`). O primeiro envio de cada cliente roda com `validateOnly`.

**GA4 e GTM (ferramenta paralela).** GA4 é a referência de comportamento no site e não é a fonte da verdade de conversão — o Kommo é. Pixel, tag do Google e GTM são configurados fora deste sistema; o Trilha depende deles funcionando (o freio usa "horas sem evento de conversão").

Especificação técnica completa: [Kommo](../integracoes/kommo.md). Código: `trilha/integracoes/kommo.py`, `trilha/plataformas/meta/capi.py`, `trilha/plataformas/google/conversoes_offline.py`.

### 7.2 Mapa de eventos de qualidade

Cada funil do Kommo tem um papel (`crm.funis`: entrada, fechamento, nutrição, base, ignorar); o "ganho" (142) só é venda no funil de fechamento; nos demais precisa de `ganho_significa` ([Kommo](../integracoes/kommo.md) §3.1). As etapas seguem o **funil padrão da Trilha**, igual para todos os segmentos ([raio-x do funil](../raio-x-do-funil.md), [ADR-008](../decisoes/008-funil-padrao.md)). **Os IDs de funil e de etapa mudam em cada conta Kommo**, então o mapa vive no `perfil.yaml` de cada cliente (`crm.mapa_eventos`); apenas as etapas de sistema do Kommo são fixas (142 = venda ganha, 143 = perdida) e entram como padrão.

| Etapa no Kommo (nome do imobiliário) | Evento padrão | Retorno à plataforma |
|---|---|---|
| Novo lead | `lead` | sim (otimização inicial) |
| Em atendimento | `em_atendimento` | uso interno (raio-x: primeiro contato) |
| Qualificado | `lead_qualificado` | sim — **evento de otimização preferido** quando houver volume |
| Visita agendada | `agendamento` | sim |
| Visita realizada | `comparecimento` | opcional — sinal mais forte que o agendamento |
| Proposta enviada | `proposta` | uso interno |
| Venda (etapa 142) | `venda` (+ valor) | sim — base para ROAS-alvo |
| Perdido (etapa 143) | `perdido` | uso interno; classificado pela categoria do motivo e pelo momento da perda |
| Reativado | `reativado` | uso interno |

**Quando o volume não sustenta otimizar por `lead_qualificado`** (§3.1 — o caso comum em PME):
1. Otimizar por `lead`, mas com atrito qualificador na origem (perguntas no formulário, mensagem pré-preenchida que exige uma escolha, faixa de preço/parcela no anúncio quando a regra comercial permite).
2. Enviar todos os eventos de qualidade mesmo assim: eles alimentam o painel, os relatórios e, nas plataformas, os modelos de qualidade de lead.
3. Quando a plataforma aceitar valor por evento, atribuir **valor ponderado** a cada degrau (ex.: `lead` = CPL máximo; `lead_qualificado` = CPL qualificado máximo; `venda` = receita) e otimizar por valor — sinal mais rico sem exigir volume de um único evento.
4. Reavaliar a cada mês: o sistema recomenda subir de degrau quando o evento superior atinge o volume semanal configurado.

### 7.3 WhatsApp

No Brasil, a conversão principal costuma ser a conversa, não o formulário. Este sistema cuida só do **rastreamento**; o atendimento (Kommo, BotConversa) é paralelo.
- **Anúncio de clique para WhatsApp:** a conversa traz o `ctwa_clid`, que a integração do WhatsApp no Kommo — ou o BotConversa, quando ele faz o primeiro atendimento — precisa gravar no lead. É esse identificador que permite devolver ao Meta os eventos de qualidade da conversa (API de Conversões para mensagens).
- **Site → WhatsApp:** botão com mensagem pré-preenchida contendo um código curto da campanha/criativo, gravado no lead (contrato com a ferramenta de landing pages).
- **Funil do cliente:** o tempo até o primeiro contato do time comercial do cliente e a qualificação por atendente aparecem no dossiê e no relatório — não como alerta em tempo real.
- **Atendimento × mídia:** o raio-x do funil (primeiro contato, cadência e conversão **por atendente/corretor**) separa problema de mídia de problema de atendimento — antes de cortar uma campanha, verifica-se quem atendeu os leads dela.

### 7.4 Outras fontes de lead

Portais (imobiliário), indicação, orgânico e lista própria entram no CRM com `origem` padronizada. Não recebem retorno de conversão, mas entram no CAC total e na visão consolidada (§8) para que a mídia paga não seja julgada isoladamente nem receba crédito por vendas de outra origem.

## 8. Motores do núcleo

| Motor | O que faz | Detalhes de plataforma |
|---|---|---|
| **Saúde das contas** | status da conta, dias de saldo pré-pago pela queima de 7 dias, recarga de 30 dias; alertas P1/P2 com ação e responsável | `trilha/core/saude.py`, painel da carteira |
| **Raio-x do funil** | etapa por etapa, primeiro contato, cadência, perdas por categoria, maior vazamento, marketing entregou × comercial converteu, atribuição pelo Kommo | [raio-x do funil](../raio-x-do-funil.md) |
| Relatórios | pontual, histórico, MTD com metas da versão vigente do perfil | em cada documento de plataforma |
| Anomalias | contas e campanhas, boas e más | §9 |
| Vencedores/potenciais | por anúncio, ângulo e termo | §9 |
| Histórico de alterações | registra toda edição (nossa ou do cliente) com data, autor, antes/depois | correlaciona com anomalias |
| Conversão real | §7 | — |
| Visão consolidada | Meta + Google + orgânico: CAC total, custo de mídia ÷ receita, participação de cada canal | evita contar a mesma venda duas vezes |
| Alocação de verba | recomenda distribuição entre canais e ofertas pelo CAC marginal | sempre como recomendação |
| Dossiê de otimização | prepara a sessão semanal do assessor: placar, mudanças, efeito das decisões anteriores, 3–5 pontos de atenção com números e simulação | modelo-operacional.md §3.1 |
| Relatório semanal | números e gráficos em três blocos (leads · criativos · ações) para o assessor escrever os insights | modelo-operacional.md §3.2 |
| Pacote de briefing | dados para o briefing de criativo: o que converte, o que cansou, objeções e motivos de perda | modelo-operacional.md §3.3 |
| Pacote da reunião | prepara a reunião mensal com os números do mês | modelo-operacional.md §3.4 |
| Painel da carteira | prepara a reunião de equipe: semáforo por cliente, pendências por pessoa | modelo-operacional.md §3.5 |
| Ritmo de gasto (pacing) | projeta o gasto até o fim do mês contra a verba contratada, por plataforma e campanha; avisa sub ou sobre-entrega com dias de antecedência | complementa o alerta de "orçamento esgotado cedo" |
| Calendário sazonal | datas do segmento (lançamentos, feirões, Black Friday, matrículas) e do cliente; marca períodos fora da linha de base e antecipa ajustes de verba e criativo | `playbooks/<segmento>/playbook.yaml` + `perfil.yaml` |
| Base de referência da carteira | benchmarks anônimos por segmento, região e plataforma (CPL, taxa de qualificação, CPM) calculados sobre todos os clientes; recalibra os padrões dos playbooks | só agregados, nunca dado de um cliente exposto a outro |

## 9. Estatística e alertas

### 9.0 Modo por volume (padrão: baixo volume)

A maioria da carteira-alvo (PME, imobiliário, serviço local) tem **menos de 20 conversões por dia** — muitas vezes menos de 1 lead qualificado por dia. O motor estatístico é ligado em camadas, pela nota de volume de cada conta:

| Modo | Quando | O que roda |
|---|---|---|
| **Baixo volume** (padrão) | < 20 conversões/dia na conta | alertas operacionais (§9.3) · pacing · comparação de janelas de 7/14/28 dias contra meta · divergência plataforma × CRM · regras simples de corte com gasto mínimo (ex.: anúncio com gasto ≥ 2× CPL máximo e zero lead) |
| **Médio** | 20–100/dia | + linha de base mediana/MAD por dia da semana, correção de atraso de atribuição |
| **Alto** | ≥ 100/dia | + encolhimento bayesiano, controle de falsos alarmes entre muitas comparações |

Nenhum alerta estatístico é exibido sem o mínimo de dados da faixa; abaixo disso, o sistema diz "dados insuficientes para conclusão" em vez de produzir um número instável.

### 9.1 Correções obrigatórias antes de ligar alertas

- **Atraso de atribuição:** conversões chegam com atraso (janela de atribuição + jornada média da oferta). Os últimos N dias são corrigidos pela curva histórica de maturação da conta, ou excluídos da comparação, e marcados como "parciais".
- **Contagens, não razões:** com poucas conversões, CPA/CPL diário é instável. Modelar conversões como contagem dado o gasto (Poisson / binomial negativa) e só então derivar o custo.
- **Sazonalidade semanal:** linha de base comparando com os mesmos dias da semana.
- **Períodos marcados** no perfil (promoções, lançamentos, datas) ficam fora da linha de base.
- **Muitas comparações:** controlar a taxa de falsos alarmes ao testar várias campanhas × métricas × janelas (ex.: limiar ajustado ou controle de taxa de descoberta falsa).

### 9.2 Método

- Linha de base robusta: mediana + MAD (métricas contínuas, como CPM) ou modelo de contagem (conversões).
- Vencedores: encolhimento bayesiano em direção à média da conta/campanha (Beta-Binomial para taxas, Gamma-Poisson para conversões por gasto); classificação por probabilidade posterior de bater a meta, ex.: `P(CPL < máximo) > 0,8`.
- Janelas e frequência calibradas pelo volume:

| Conversões/dia | Janelas | Frequência de alertas | Requisito mínimo |
|---|---|---|---|
| ≥ 100 | 1, 3, 7 dias | até 4×/dia | gasto baixo |
| 20–100 | 3, 7, 14 dias | 1–2×/dia | gasto moderado |
| < 20 | 7, 14 dias | 1×/dia | gasto alto + mínimo de conversões |

### 9.3 Priorização por impacto

- Todo alerta mostra **R$ em risco por dia** (ou oportunidade) e é ordenado por isso.
- Limite de alertas por relatório; o resto vai para um anexo.
- **Fora da rotina, só urgência.** Achados não urgentes (anomalias, vencedores, oportunidades) vão para o dossiê semanal, não para o Slack.
- **Alertas operacionais** sempre passam, independentemente de estatística: gasto zerado, entrega parada, reprovação, orçamento esgotado cedo, tag/pixel sem disparar.
- Alerta logo após uma alteração registrada é anotado como "possivelmente causado por alteração de <data>".

### 9.4 Protocolo de testes

Todo teste (criativo, ângulo, público, lance) é registrado antes de começar:
`hipótese · variável testada · métrica de decisão · amostra mínima · duração máxima · regra de decisão`.
Testes sem volume para atingir a amostra mínima não são abertos — o sistema sugere testar uma variável de maior impacto ou concentrar verba.

## 10. Operação, segurança e governança

- **Nenhuma alteração sem o assessor.** Toda mudança em conta é decidida pelo assessor (a partir dos pontos de atenção do dossiê semanal) e marcada para execução na tarefa do ClickUp ([ClickUp](../integracoes/clickup.md) §2). Antes de executar, o sistema confere se a conta ainda está no estado da simulação.
- **Freio de emergência** ([ADR-006](../decisoes/006-freio-de-emergencia.md)), a única exceção: campanha com gasto ≥ 3× o CPL máximo desde o último lead, ou gastando há ≥ 6h sem nenhum evento de conversão. Modo `pausar` (opção A, padrão: pausa e avisa com desfazer) ou `avisar` (opção B), por cliente no `perfil.yaml`. Regra em `trilha/core/freio.py`; reativar é sempre decisão do assessor.
- **Simulação antes de escrever:** toda alteração mostra o "antes → depois" e o impacto estimado; aplicação só após aprovação.
- **Reversão:** toda escrita guarda o estado anterior para desfazer.
- **Proteção do algoritmo:** recomendações agrupadas em janelas (ex.: 1–2×/semana por campanha); bloqueio de alterações estruturais durante fase de aprendizado, salvo emergência.
- **Monitoramento das rotinas:** se uma tarefa agendada não rodar ou falhar, aviso imediato (falha silenciosa é o pior cenário).
- **Acessos:** o cliente é dono das contas; a agência entra como parceira. Checklist de entrada e de saída do cliente (remover acessos, entregar dados e relatórios).
- **Segredos:** `.env` fora do Git; `.env.example` só com os nomes.
- **Dados de clientes fora do repositório de código** ([ADR-004](../decisoes/004-dados-de-clientes.md)): margens, tickets, regras comerciais e qualquer dado pessoal vivem em repositório privado separado ou no banco. Aqui fica só `clientes/_exemplo/`; o `.gitignore` bloqueia o resto.
- **LGPD:** dados pessoais enviados às plataformas sempre com hash e lidos só pela trilha-api (nunca passam pelo n8n); captura do mínimo necessário; registro de quais dados vão para quais plataformas. Base legal e aviso de privacidade nos pontos de captura são responsabilidade das ferramentas paralelas (landing pages, formulários, BotConversa).
- **Custo de tokens:** dados volumosos processados no script; só resumos chegam ao modelo.

## 11. Saídas

| Saída | Público | Frequência | Conteúdo |
|---|---|---|---|
| Urgências e freio | assessor | quando ocorre | só o que não pode esperar a sessão semanal; com R$ em risco e desfazer |
| Leitura diária | assessor | dias úteis | a carteira em 5 linhas por cliente, no Slack |
| Dossiê de otimização | assessor | semanal, por cliente | prepara a sessão de otimização (modelo-operacional.md §3.1) |
| Relatório semanal (números) | assessor (leva ao cliente) | semanal, por cliente | três blocos — leads, criativos, ações; o assessor escreve os insights e entrega |
| Pacote de briefing | assessor | com o dossiê e sob demanda | dados para o briefing de criativo; a estratégia é do assessor |
| Painel da carteira | assessor + equipe | semanal | prepara a reunião de equipe |
| Painel MTD | operação | ao vivo | mesmo layout para todos os clientes |
| Pacote da reunião | assessor (leva ao cliente) | mensal, por cliente | resultado de negócio, o que foi testado e aprendido, números para a proposta de 30 dias — o assessor monta a narrativa e conduz |
| Registro de decisões | operação | contínuo | o que o assessor decidiu → o que aconteceu |

**Canais de entrega:** urgências, freio e leitura diária vão para o Slack da operação; dossiês, relatórios e pacotes chegam como tarefas no ClickUp. **Nada sai do sistema direto para o cliente.**

**Definições:** [dicionário de métricas da Trilha](../metricas.md) (lead, qualificado, reunião, oportunidade, venda, CPL, CPO, CAC teto, ROAS piso, deduplicação, semanas w1–w4).

**Hierarquia de métricas por cliente:** resultado (vendas, valor vendido — VGV no imobiliário —, retorno sobre o investimento, custo por venda e por comparecimento) → métrica principal da plataforma (custo por lead qualificado, ROAS) → diagnóstico (CPL, CPM, CTR, retenção de vídeo). Relatórios nunca apresentam métrica de diagnóstico como resultado.

## 12. Estrutura do repositório

Legenda: ✅ existe · ⬜ previsto no [roadmap](../roadmap.md).

```
/
├── README.md
├── pyproject.toml · .env.example · .gitignore · .github/workflows/testes.yml
├── docs/
│   ├── ecossistema.md · modelo-operacional.md · raio-x-do-funil.md · metricas.md · roadmap.md
│   ├── arquitetura/           ✅ nucleo.md · meta-ads.md · google-ads.md
│   ├── decisoes/              ✅ ADRs 001–008
│   └── integracoes/           ✅ n8n.md · kommo.md · clickup.md · ferramentas.md
├── trilha/                    pacote Python = trilha-api
│   ├── api.py                 ✅ HTTP para o n8n
│   ├── __main__.py            ✅ CLI: validar · calcular · raio-x · simular-webhook · servir
│   ├── core/                  ✅ perfil.py · oferta.py · playbook.py · economia.py · funil.py · atribuicao.py · freio.py · saude.py
│   │                          ⬜ materiais (dossiê, relatório, briefing, reunião, painel)
│   ├── conversao/             ✅ hash.py · pipeline.py
│   ├── integracoes/           ✅ kommo.py · ⬜ clickup.py
│   └── plataformas/           ✅ meta/capi.py · google/conversoes_offline.py
├── tests/                     ✅ unittest + fixtures
├── n8n/
│   ├── modelos/               ✅ w01-conversao-real.json · w10-vigia-de-falhas.json
│   └── fluxos/                exportação diária da produção (gerada pelo backup)
├── infra/                     ✅ Dockerfile · docker-compose.yml · Caddyfile · backup.sh · .env.example · kommo.env.example
├── playbooks/                ✅ padrao/ (todos os segmentos) · imobiliario/
└── clientes/_exemplo/         ✅ perfil.yaml · marca.yaml · ofertas/
```

Clientes reais: repositório privado Trilha-clientes, pasta `ads/` (mesma estrutura de `clientes/_exemplo/`), montada na trilha-api pela variável `TRILHA_CLIENTES_DIR`.

## 13. Roadmap

O que está pronto e o que falta para entrar em operação: [roadmap](../roadmap.md).

## 14. Plataformas e canais futuros

Mesmo núcleo, novo módulo em `plataformas/`, ativado pela Camada 0 quando o segmento justificar:
- **TikTok Ads** — públicos jovens, educação, varejo; mesmo módulo criativo e taxonomia do Meta.
- **LinkedIn Ads** — clientes B2B; lead gen nativo com retorno de qualidade pelo CRM.
- **Orgânico** (Instagram, Perfil da Empresa no Google, SEO local) — entra primeiro como **fonte medida** na visão consolidada, depois como módulo de conteúdo alimentado pelos mesmos ângulos vencedores.
