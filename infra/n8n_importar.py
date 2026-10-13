"""Importa os fluxos de n8n/modelos/ para uma instância do n8n (local ou produção), sem passos manuais.

- Casa cada modelo com o fluxo de mesmo nome: atualiza se existe, cria se não existe. Nunca apaga.
- Liga as credenciais pelo nome que está no modelo (cria a "trilha-api" com TRILHA_API_TOKEN se faltar).
- Aponta o fluxo de erro de todos para o W10 (importado primeiro).
- Nunca ativa nem publica: isso é decisão de quem opera. Avisa quais precisam ser publicados.

Sem --aplicar, só mostra o plano. Lê N8N_API_URL, N8N_API_KEY e TRILHA_API_TOKEN do ambiente ou do .env.
Uso, na raiz do Trilha-ads:  python infra/n8n_importar.py [--aplicar]
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from trilha.ambiente import carregar_env  # noqa: E402

MODELOS = RAIZ / "n8n" / "modelos"
W10 = "w10-vigia-de-falhas.json"
MARCADOR_W10 = "DEFINIR_ID_DO_W10_APOS_IMPORTAR"
# chaves de settings que a API pública aceita
SETTINGS = {"executionOrder", "saveDataErrorExecution", "saveDataSuccessExecution", "saveManualExecutions",
            "saveExecutionProgress", "errorWorkflow", "timezone", "executionTimeout", "callerPolicy"}


class N8n:
    def __init__(self, url: str, chave: str):
        self.base = url.rstrip("/") + "/api/v1/"
        self.chave = chave

    def __call__(self, metodo: str, caminho: str, corpo=None) -> dict:
        req = urllib.request.Request(
            self.base + caminho, method=metodo, data=json.dumps(corpo).encode() if corpo is not None else None,
            headers={"X-N8N-API-KEY": self.chave, "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"n8n {metodo} {caminho}: HTTP {e.code} — {e.read().decode('utf-8', 'replace')[:400]}")
        except urllib.error.URLError as e:
            raise SystemExit(f"n8n inacessível em {self.base}: {e.reason}")

    def todos(self, recurso: str) -> list[dict]:
        itens, cursor = [], None
        while True:
            d = self("GET", f"{recurso}?limit=100" + (f"&cursor={cursor}" if cursor else ""))
            itens += d.get("data", [])
            cursor = d.get("nextCursor")
            if not cursor:
                return itens


def _modelos() -> list[tuple[str, dict]]:
    arquivos = sorted(MODELOS.glob("*.json"), key=lambda p: (p.name != W10, p.name))
    return [(p.name, json.loads(p.read_text(encoding="utf-8"))) for p in arquivos]


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    carregar_env(os.environ.get("TRILHA_ENV_FILE", RAIZ / ".env"))
    chave = os.environ.get("N8N_API_KEY")
    if not chave:
        raise SystemExit("Falta N8N_API_KEY (n8n → Settings → n8n API) no ambiente ou no .env")
    n8n = N8n(os.environ.get("N8N_API_URL", "http://localhost:5678"), chave)

    existentes = {w["name"]: w for w in n8n.todos("workflows")}
    credenciais = {c["name"]: c for c in n8n.todos("credentials")}
    print(f"n8n {n8n.base} · {'APLICAR' if aplicar else 'plano, nada é gravado'}")

    id_w10 = None
    publicar = []
    for arquivo, modelo in _modelos():
        nome = modelo["name"]
        nodes = json.loads(json.dumps(modelo["nodes"]))
        for n in nodes:
            for tipo, ref in (n.get("credentials") or {}).items():
                cred = credenciais.get(ref["name"])
                if cred is None and tipo == "httpHeaderAuth" and ref["name"].startswith("trilha-api"):
                    token = os.environ.get("TRILHA_API_TOKEN")
                    if not token:
                        raise SystemExit("Credencial da trilha-api ausente no n8n e TRILHA_API_TOKEN não definido")
                    print(f"  credencial '{ref['name']}': criar")
                    if aplicar:
                        cred = n8n("POST", "credentials", {"name": ref["name"], "type": tipo,
                                                           "data": {"name": "Authorization", "value": f"Bearer {token}"}})
                        credenciais[ref["name"]] = cred
                    else:
                        cred = {"id": "(a criar)"}
                elif cred is None:
                    raise SystemExit(f"{arquivo}: credencial '{ref['name']}' não existe no n8n; crie antes de importar")
                ref["id"] = cred["id"]

        settings = {k: v for k, v in modelo.get("settings", {}).items() if k in SETTINGS}
        if arquivo != W10:
            if id_w10 is None:
                raise SystemExit("o W10 precisa existir antes dos outros fluxos")
            settings["errorWorkflow"] = id_w10
        corpo = {"name": nome, "nodes": nodes, "connections": modelo["connections"], "settings": settings}

        atual = existentes.get(nome)
        print(f"  {nome}: {'atualizar' if atual else 'criar'}")
        if aplicar:
            r = n8n("PUT", f"workflows/{atual['id']}", corpo) if atual else n8n("POST", "workflows", corpo)
            wid = r["id"]
            if atual and atual.get("active"):
                # conforme a versão do n8n, a atualização vale na hora ou fica como rascunho até publicar:
                # compara o grafo publicado com o rascunho, nó a nó
                depois = n8n("GET", f"workflows/{wid}")
                publicado = depois.get("activeVersion") or {}
                def grafo(w):
                    return (sorted(json.dumps({k: n.get(k) for k in ("name", "type", "parameters", "credentials", "disabled")},
                                              sort_keys=True) for n in w.get("nodes", [])),
                            json.dumps(w.get("connections", {}), sort_keys=True))
                if grafo(publicado) != grafo(depois):
                    publicar.append(nome)
        else:
            wid = atual["id"] if atual else "(novo)"
        if arquivo == W10:
            id_w10 = wid

    # o fluxo de erro só recebe falhas se estiver ativo (publicado): sem ele, toda falha é silenciosa
    w10 = next((w for w in n8n.todos("workflows") if w["name"] == _modelos()[0][1]["name"]), None)
    if w10 is not None and not w10.get("active"):
        print("ATENÇÃO: o W10 (vigia de falhas) está inativo. Ative-o no n8n: sem isso, nenhuma falha é avisada.")

    if aplicar:
        print("Importado. Nada foi ativado.")
        if publicar:
            print("Ficaram como rascunho (publicar no n8n para valer): " + "; ".join(publicar))
        else:
            print("Fluxos ativos já rodam a versão importada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
