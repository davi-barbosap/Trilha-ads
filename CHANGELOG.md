# Mudanças

As versões anteriores estão descritas no histórico do Git.

## 0.10.0 — operação padronizada: ambiente local, Kommo e fluxos à prova de erro (out/2026)

- **Ambiente local igual à produção** (`infra/local/docker-compose.yml`): n8n + trilha-api com as mesmas variáveis, para os fluxos de `n8n/modelos/` rodarem iguais nos dois lugares. Túnel opcional (`--profile tunel`). Guia e problemas conhecidos: `docs/operacao/ambiente-local.md`.
- **`kommo conferir` e `kommo preparar`:** o próprio sistema confere e prepara a conta do Kommo do cliente.
  - **Preparar:** cria o funil padrão com os nomes do playbook, os campos de rastreamento e os motivos de perda. Nunca altera nem apaga; rodar de novo não duplica. Imprime o `crm.mapa_eventos` com os IDs reais.
  - **Conferir:** só leitura; sai com erro se faltar campo ou motivo, ou se o perfil apontar para funil ou etapa que não existe na conta.
  - **Campos:** lista única em `trilha/integracoes/kommo_padrao.py`; entram `ttclid` e a origem `tiktok` (o site da Trilha vende TikTok Ads).
- **`infra/n8n_importar.py`:** importa os fluxos-modelo por nome, liga a credencial da trilha-api e o fluxo de erro. Nunca ativa; avisa quando o W10 está inativo e quando um fluxo ativo ficou só como rascunho.
- **W01:** descarta "lead alterado" antes de chamar a trilha-api; endereço da API por `$env.TRILHA_API_URL`; aviso no Slack só com Slack configurado; espera entre tentativas dentro do limite do n8n (5 s).
- **W10:** não falha quando o Slack ainda não está configurado.
- **Correções:**
  - o perfil recusa `crm.subdominio` com o endereço inteiro (`https://…kommo.com`), que antes só falhava depois, como erro de rede;
  - a pasta de logs da imagem nasce com o dono certo: antes, o registro de envios falharia por permissão depois de enviar ao Meta, e o n8n repetiria o envio;
  - o compose de produção grava o registro de envios em volume próprio e passa `TRILHA_RESPONSAVEL_TECNICO`;
  - versão única: `trilha/__init__.py` e `pyproject.toml` estavam diferentes (a `/saude` informava 0.8.0).
- **`.env` local** lido pelo `python -m trilha` sem sobrescrever o ambiente.
- **Documentação:** endereço certo do webhook (`/webhook/trilha-w01-kommo/kommo/<cliente>`), eventos a marcar no Kommo, importação dos fluxos, segmentos do site (`playbooks/README.md`) e a entrada de leads das landing pages (W15) como bloqueio no roadmap.

## 0.9.1 — um cliente fictício só (out/2026)

- **O exemplo documentado** (`clientes/_exemplo/`) passa a ser a Escola Exemplo de Inglês, o mesmo cliente fictício do Trilha-briefing, do Trilha-copy e da Trilha-LP.
  - **Origem:** `marca.yaml`, `ofertas/` e a parte de cima do `perfil.yaml` vêm do briefing (`exportar --para trilha`). A parte operacional (contas, Kommo, conversão, freio, operação) foi completada aqui.
  - **Antes:** era uma imobiliária fictícia.
- **A imobiliária fictícia** vai para `tests/fixtures/clientes/_exemplo/`. Os testes e os dados de funil e de webhook (que são de um cliente do imobiliário) usam ela, porque exercitam as regras do segmento.
- **Diagnóstico de aderência por segmento:** a finalidade (uso próprio ou investimento) e a flexibilidade de pagamento apareciam como pendência para qualquer oferta, inclusive um curso.
  - **Agora:** o playbook diz o que exige (`aderencia_exige`). O padrão exige a parte que vale para qualquer segmento, a mesma que o Trilha-briefing exporta. O imobiliário acrescenta as duas.
  - **Onde aparece:** `validar` e a API (`aderencia_pendente`).

## 0.9.0 — caminho de volta para o briefing (out/2026)

- **`raio-x … --retorno <pasta>`:** grava o retorno do período (`<inicio>_<fim>.yaml`, contrato `retorno` versão 1).
  - **Conteúdo:** o resultado por código de criativo e os motivos de perda do Kommo, com a categoria do playbook e a contagem.
  - **Destino:** `ads/<id>/retornos/` no Trilha-clientes. O Trilha-briefing lê com `registrar-resultados`.
  - **Período:** sai das datas dos leads, ou de `--inicio` e `--fim`.
- **`agendamentos`** entra no resumo por criativo, por responsável e por closer, para as hipóteses medidas em agendamento.

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
