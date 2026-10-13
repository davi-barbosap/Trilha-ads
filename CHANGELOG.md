# Mudanças

As versões anteriores estão descritas no histórico do Git.

## 0.8.0 — raio-x por criativo (out/2026)

- **`por_criativo` no raio-x:** leads, qualificados, vendas e taxa de qualificação por código da célula da grade, lido do `utm_content` pela régua das UTMs ("VD01 | Ana" → "VD01"; `{{…}}`, vazio e "—" contam como vazio).
- **Gasto por código:** com `--gasto-por-codigo` (CLI) ou `gasto_por_codigo` (API), entram o CPL, o custo por qualificado e o custo por venda de cada código. Código com gasto e sem lead também aparece.
- **Padrão do código editável por cliente** em `crm.padrao_codigo`. O padrão é o da grade (`[A-Z0-9]{2,8}`). O perfil de exemplo usa `v[0-9]+`, a convenção daquele cliente.
- **Qualidade dos dados:** `leads_pagos_sem_codigo_criativo`, com sinal acima de 20%.
- **Nomes curtos:** a seção de taxonomia do núcleo passa a ancorar o nome do anúncio no código (`PT01 | v1`). As características do criativo ficam nos arquivos, ligadas ao código.

## 0.7.1 — organização do ecossistema (out/2026)

Nenhuma mudança de comportamento: documentação, nomes e referências.

- **Ecossistema:** a documentação passa a nomear o Trilha-briefing (diagnóstico, estratégia e cadastro), o Trilha-copy (verificador de copy, que saiu do roadmap daqui), a Trilha-LP (landing pages) e o Trilha-clientes (dados reais; este sistema lê a pasta `ads/`).
- **ADR-005 reescrita:** o cadastro do cliente vem do Trilha-briefing, por contrato de dados testado no briefing.
- **Anonimização:** nomes de clientes e de repositórios de clientes saíram da documentação, dos testes e dos comentários. O mapeamento de onde veio cada padrão (`origem-dos-padroes.md`) fica só no histórico.
- **Roadmap honesto:**
  - o envio ao Google aparece como parcial, porque só o payload existe;
  - os fluxos do n8n aparecem como modelos ainda não importados;
  - entram três itens que não dependem do n8n: raio-x por código da célula, leitura dos campos da Trilha-LP e validação do `marca.yaml`.
- **Raio-x:** a documentação não afirma mais atribuição por criativo, que ainda não existe.
- **README:** separa o que está pronto no código do que depende dos fluxos do n8n.
- **Versão:** `pyproject.toml` e `trilha/__init__.py` agora dizem a mesma coisa.
