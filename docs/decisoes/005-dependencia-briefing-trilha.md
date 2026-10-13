# ADR-005 — Dependência do briefing-trilha

**Status:** proposta — precisa do acordo da responsável pelo repositório `briefing-trilha`

## Contexto
O wizard de onboarding (Streamlit), o `build_kommo_json.py`, os textos de objeções/apelos e o playbook imobiliário vêm do `briefing-trilha`, um repositório de outra pessoa. Sem regra, uma mudança lá quebra o onboarding aqui sem aviso.

## Decisão proposta
1. **Contrato de dados, não de código:** o wizard produz `perfil.yaml`, `marca.yaml` e `ofertas/*.yaml`; o Trilha valida com `python -m trilha validar`. Qualquer mudança de formato passa pelo esquema em `trilha/core/perfil.py`.
2. **Versão fixada:** o Trilha consome o `briefing-trilha` por tag de versão (submódulo Git ou pacote), nunca pela branch principal.
3. **Conteúdo de playbook** (objeções, apelos, fluxos) é copiado para `playbooks/imobiliario/` com referência à versão de origem; atualizações são deliberadas.
4. **Responsáveis:** definir quem mantém o wizard e como as etapas de mídia (núcleo §4.2) entram lá — preferência por contribuição no próprio `briefing-trilha`.

## Consequências
Enquanto não houver acordo, o onboarding de mídia roda pelo `clientes/_exemplo/` preenchido à mão e validado pelo CLI.

## O que o briefing-trilha entrega hoje (leitura completa, out/2026)
- **Não coleta os IDs do Kommo:** a etapa de orquestração foi retirada do wizard e os fluxos saem com marcadores no lugar dos IDs de etapa. `crm.mapa_eventos` continua sendo preenchido à mão.
- **Não coleta o diagnóstico de aderência:** o bloco `aderencia` das ofertas é preenchido pelo assessor.
- **Junta dois estados numa etapa:** o modelo pede um só status para "não cadastrou" e "lead frio". Para o raio-x são perdas diferentes (contato inválido × não respondeu); pedir os dois separados, e o status de "em atendimento humano".
- **Campos que mudam de nome ao virar `ofertas/*.yaml`:** `estagio_obra` → `estagio`, `condicoes_pagamento` → `condicoes_comerciais.pagamento`, `diferenciais_comerciais` → `condicao_excepcional`, `comparativo_concorrentes` → `posicionamento_preco`, `jornada_media` ("30 dias") → `perfil_lead.jornada_media_dias` (30), `ticket_medio` (texto) → número. `construtora`, `tipologia`, `plantas`, `vias_acesso`, `valorizacao`, `critica_localizacao` e `objecoes_avulsas` já existem no esquema da oferta.
- **Prazo de resposta:** `sla_resposta` vira `crm.sla_primeiro_contato_min` (30 min → 30, 2 h → 120, 24 h+ → 1440; "mesmo dia" a combinar com o cliente).
- **ClickUp:** mesmos nomes de variável nos dois repositórios ([ClickUp](../integracoes/clickup.md) §7). O wizard publica na primeira lista da pasta quando não acha a "Operação"; o Trilha para e avisa.
- **Tags que os fluxos aplicam** (Interesse Confirmado, lead frio, não-cadastrou, reativado) são lidas pelo raio-x ([Kommo](../integracoes/kommo.md) §3.2).
