# ADR-004 — Dados de clientes fora do repositório de código

**Status:** aceita

## Contexto
Guardar `clientes/<cliente>/` (margem, ticket, regras comerciais, histórico) dentro deste repositório misturaria código (que pode ser compartilhado com freelancers e ferramentas) com dado sensível de negócio e, eventualmente, dado pessoal (LGPD).

## Decisão
- Este repositório guarda apenas `clientes/_exemplo/`. O `.gitignore` bloqueia qualquer outra pasta em `clientes/`.
- Clientes reais vivem no repositório **privado** Trilha-clientes, compartilhado pelas quatro ferramentas (uma pasta por ferramenta), com acesso só da equipe de operação. Este sistema lê a pasta `ads/` dele, apontada pela variável `TRILHA_CLIENTES_DIR`.
- Dados pessoais de leads nunca vão para nenhum repositório: ficam no Kommo e no banco (ADR-001), e saem para as plataformas apenas em hash.

## Consequências
- O código pode ser revisado e testado sem expor clientes.
- Saída de cliente (núcleo §10) = arquivar a pasta dele no repositório privado e apagar os dados no banco conforme a política de retenção.
