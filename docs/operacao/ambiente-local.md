# Ambiente local: n8n + trilha-api + Kommo de teste

> Produção: [`infra/docker-compose.yml`](../../infra/docker-compose.yml) · Fluxos: [n8n](../integracoes/n8n.md) · Kommo: [Kommo](../integracoes/kommo.md)

Serve para desenvolver e testar fluxos e regras antes de qualquer cliente real. Roda os **mesmos fluxos e as mesmas variáveis** da produção ([`infra/local/docker-compose.yml`](../../infra/local/docker-compose.yml)); muda só o que não faz sentido num computador: SQLite no lugar de Postgres, sem fila, sem Caddy, portas só em `127.0.0.1`.

## 1. Organização das pastas

```
Trilha/                      pasta de trabalho (qualquer nome)
  Trilha-ads/                este repositório; .env local (fora do Git)
  Trilha-briefing/ Trilha-copy/ Trilha-LP/
  Trilha-clientes/           repositório PRIVADO com os arquivos reais; o Trilha-ads lê ads/<id>/perfil.yaml
```

## 2. Subir

Pré-requisito: Docker Desktop, com **Settings → General → Start Docker Desktop when you sign in** marcado (sem isso, o n8n some quando o computador reinicia).

1. Copiar `.env.example` para `.env` e preencher: `N8N_VERSION`, `N8N_DADOS`, `TRILHA_CLIENTES_DIR`, `TRILHA_API_TOKEN` (gerar: `python -c "import secrets; print(secrets.token_urlsafe(32))"`), `KOMMO_TOKEN_<CLIENTE>`, `KOMMO_WEBHOOK_TOKEN_<CLIENTE>`, `N8N_API_KEY` (depois do passo 3).
2. Subir:
   ```bash
   docker compose -f infra/local/docker-compose.yml --env-file .env up -d --build
   ```
   A trilha-api precisa ficar `healthy`; o n8n só sobe depois dela. O n8n abre em http://localhost:5678.
3. No n8n: **Settings → n8n API → Create an API key**; gravar em `N8N_API_KEY` no `.env`.
4. Importar os fluxos ([n8n](../integracoes/n8n.md) §7) e **ativar o W10 e o W01** no editor:
   ```bash
   python infra/n8n_importar.py --aplicar
   ```

## 3. Kommo de teste

```bash
python -m trilha kommo preparar ../Trilha-clientes/ads/<cliente>/perfil.yaml --aplicar
python -m trilha kommo conferir ../Trilha-clientes/ads/<cliente>/perfil.yaml
```

O `preparar` cria o funil padrão, os campos e os motivos de perda do playbook, e imprime o `crm.mapa_eventos` para o perfil. O `conferir` só lê e sai com erro se algo não estiver no padrão (inclusive IDs do perfil que não existem na conta).

## 4. Túnel (para o Kommo alcançar o n8n)

O Kommo está na internet; o n8n local, não. O túnel cria um endereço HTTPS público até o n8n. **Abre o editor do n8n para a internet** (protegido pelo login) e os webhooks (protegidos pelo segredo de cada cliente): ligar só durante os testes.

```bash
docker compose -f infra/local/docker-compose.yml --env-file .env --profile tunel up -d
docker compose -f infra/local/docker-compose.yml --env-file .env logs tunel | grep trycloudflare.com
```

- Gravar o endereço em `N8N_URL_PUBLICA` (com `/` no fim) e subir de novo o n8n, para ele mostrar os endereços de webhook certos.
- Cadastrar o webhook no Kommo ([Kommo](kommo.md) §4.1).
- **O endereço muda a cada vez que o túnel reinicia**: atualizar o webhook no Kommo. Um túnel só por vez.
- Desligar: `docker compose -f infra/local/docker-compose.yml --env-file .env stop tunel`.

## 5. Teste de ponta a ponta

1. Criar um lead de teste no funil do Kommo e movê-lo para **Qualificado**.
2. No n8n, em *Executions* do W01: uma execução por evento, todas com sucesso; a resposta da trilha-api diz o evento identificado (`lead_qualificado`) e, sem pixel no perfil, "perfil sem plataformas.meta.pixel_id".
3. Teste negativo: o mesmo webhook com `token=errado` precisa terminar em erro no W01 **e** aparecer nas execuções do W10.

## 6. Problemas conhecidos

| Sintoma | Causa | O que fazer |
|---|---|---|
| `localhost:5678` não abre; `docker ps` vazio | o contêiner foi apagado (atualização do Docker, limpeza) | os dados ficam em `N8N_DADOS`; subir de novo com o compose (§2). Antes de mexer, copiar a pasta de dados |
| Falha num fluxo e nada no W10 | W10 inativo: fluxo de erro desligado não recebe nada | ativar o W10; o importador avisa enquanto estiver inativo |
| Duas execuções por ação no Kommo | evento "Lead alterado" marcado no webhook | deixar só "Lead adicionado" e "Etapa do lead alterada"; o W01 descarta o resto de qualquer forma |
| `kommo conferir`: "Kommo inacessível" | subdomínio errado | `crm.subdominio` é só a parte antes de `.kommo.com`; a validação do perfil recusa o endereço inteiro |
| HTTP 401 do Kommo | token inválido ou vencido | gerar outro token de longa duração na integração privada; atualizar `KOMMO_TOKEN_<CLIENTE>` |
| HTTP 402 do Kommo | conta sem plano ativo (teste vencido) | a API para junto com o plano |
| `trilha-api` 403 "segredo de webhook inválido" | `token=` do webhook diferente de `KOMMO_WEBHOOK_TOKEN_<CLIENTE>` | conferir o endereço cadastrado no Kommo |
| Túnel com linhas `ERR … udp6 … no route to host` | a rede não tem IPv6; o túnel tenta e cai para IPv4 | normal se aparecer "Registered tunnel connection" logo depois |
| Assistente de IA não alcança o n8n local (`SSRF protection: Localhost access is blocked`) | o servidor MCP do n8n bloqueia `localhost` no modo estrito | na configuração do servidor MCP: `WEBHOOK_SECURITY_MODE=moderate` |
| Nova tentativa do n8n vem em 5 s, não no tempo configurado | o n8n limita `waitBetweenTries` a 5000 ms | os modelos já respeitam o limite (teste em `tests/test_fluxos_n8n.py`) |
