# ADR-005 — O cadastro do cliente vem do Trilha-briefing

**Status:** aceita (out/2026). Substitui a proposta anterior, que dependia de uma ferramenta de onboarding de outro repositório; a versão anterior está no histórico do Git.

## Contexto

Nenhum módulo deste sistema liga sem perfil, marca e ofertas validados. O onboarding vinha de uma ferramenta paralela, com campos que mudavam de nome no caminho e sem os IDs do Kommo. A Trilha passou a fazer o diagnóstico e o planejamento no [Trilha-briefing](https://github.com/davi-barbosap/Trilha-briefing), que é a fonte de todas as ferramentas.

## Decisão

1. **Contrato de dados, não de código.** O briefing exporta `marca.yaml`, `ofertas/*.yaml` e `perfil.parcial.yaml` (`exportar --para trilha`) para `Trilha-clientes/ads/<id>/`. Este sistema valida com `python -m trilha validar`. Nenhum dos dois importa código do outro.
2. **O teste de contrato fica no briefing.** O `tests/test_contrato.py` do Trilha-briefing confere que as ofertas exportadas passam no esquema daqui e que a economia dá os mesmos números. Mudou `trilha/core/perfil.py` ou `trilha/core/oferta.py`? A CI do briefing precisa continuar verde.
3. **O que só existe aqui é preenchido aqui:** contas e IDs das plataformas, `crm.mapa_eventos`, regras do freio e entrega dos materiais (no `perfil.yaml`), e as `correcoes.yaml`.
4. **Fluxos do Kommo** (etapas, salesbots, tags) continuam na ferramenta paralela de fluxos de CRM. O raio-x lê as tags com os nomes reais ([Kommo](../integracoes/kommo.md) §3.2).

## Consequências

- Uma fonte só para estratégia e oferta: corrige-se no briefing e exporta-se de novo; `ofertas/` não se edita à mão aqui.
- O `marca.yaml` chega mas ainda não é lido nem validado aqui. Vai ser usado no pacote de briefing de criativo (W08).
- O que o briefing ainda não coleta (IDs do Kommo, por exemplo) fica como lacuna do `perfil.yaml`, e o `validar` aponta.
