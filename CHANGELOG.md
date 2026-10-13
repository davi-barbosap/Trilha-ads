# Mudanças

As versões anteriores estão descritas no histórico do Git.

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
