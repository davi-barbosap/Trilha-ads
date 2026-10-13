"""Integração Kommo: parser de webhook, leitura de lead (API v4) e extração de identificadores.

Especificação: docs/integracoes/kommo.md.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import parse_qs

IDENTIFICADORES = ("gclid", "gbraid", "wbraid", "fbclid", "ctwa_clid", "meta_lead_id")

_CHAVE = re.compile(r"^leads\[(status|add)\]\[(\d+)\]\[(\w+)\]$")
_SUBDOMINIO = "account[subdomain]"


@dataclass
class MudancaEtapa:
    lead_id: int
    status_id: int
    pipeline_id: int | None
    old_status_id: int | None = None
    tipo: str = "status"
    atualizado_em: int | None = None  # unix


def _achatar(obj, prefixo: str = "") -> list[tuple[str, str]]:
    """Volta um corpo já interpretado (ex.: pelo nó Webhook do n8n) para chaves no formato leads[status][0][id]."""
    if isinstance(obj, dict):
        itens = obj.items()
    elif isinstance(obj, list):
        itens = enumerate(obj)
    else:
        return [(prefixo, "" if obj is None else str(obj))]
    pares = []
    for k, v in itens:
        k = str(k)
        if prefixo:
            k = k if k.startswith("[") else f"[{k}]"
        pares += _achatar(v, prefixo + k)
    return pares


def _pares(corpo: str | bytes | dict) -> list[tuple[str, str]]:
    if isinstance(corpo, bytes):
        corpo = corpo.decode("utf-8")
    if isinstance(corpo, str):
        return [(k, v[0]) for k, v in parse_qs(corpo, keep_blank_values=True).items()]
    return _achatar(corpo)


def subdominio_do_webhook(corpo: str | bytes | dict) -> str | None:
    """Conta Kommo que disparou o webhook (account[subdomain]), quando vier no corpo."""
    for chave, valor in _pares(corpo):
        if chave == _SUBDOMINIO and valor:
            return valor
    return None


def parse_webhook(corpo: str | bytes | dict) -> list[MudancaEtapa]:
    """Lê o webhook do Kommo (lead criado e mudança de etapa).

    Aceita o POST form-urlencoded original ou o mesmo conteúdo já interpretado como dicionário,
    plano ({"leads[status][0][id]": "1"}) ou aninhado ({"leads": {"status": [{"id": "1"}]}}).
    """
    pares = _pares(corpo)
    itens: dict[tuple[str, str], dict[str, str]] = {}
    for chave, valor in pares:
        m = _CHAVE.match(chave)
        if m:
            tipo, indice, campo = m.groups()
            itens.setdefault((tipo, indice), {})[campo] = valor

    def inteiro(v: str | None) -> int | None:
        return int(v) if v not in (None, "") else None

    mudancas = []
    for (tipo, _), campos in sorted(itens.items()):
        if inteiro(campos.get("id")) is None or inteiro(campos.get("status_id")) is None:
            continue
        mudancas.append(
            MudancaEtapa(
                lead_id=int(campos["id"]),
                status_id=int(campos["status_id"]),
                pipeline_id=inteiro(campos.get("pipeline_id")),
                old_status_id=inteiro(campos.get("old_status_id")),
                tipo=tipo,
                atualizado_em=inteiro(campos.get("updated_at") or campos.get("last_modified")),
            )
        )
    return mudancas


@dataclass
class DadosLead:
    lead_id: int
    status_id: int | None = None  # etapa ATUAL no Kommo (confirma o webhook)
    pipeline_id: int | None = None
    valor: float | None = None  # valor do negócio no Kommo (VGV no imobiliário)
    responsavel_id: int | None = None
    motivo_perda: str | None = None
    criado_em: int | None = None  # unix
    ids: dict[str, str] = field(default_factory=dict)
    utm: dict[str, str] = field(default_factory=dict)
    emails: list[str] = field(default_factory=list)
    telefones: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def _valores_campo(campos: list[dict] | None, nome: str) -> list[str]:
    alvo = nome.strip().lower()
    for c in campos or []:
        chaves = {str(c.get("field_id", "")), str(c.get("field_name") or "").lower(), str(c.get("field_code") or "").lower()}
        if alvo in chaves:
            return [str(v["value"]) for v in c.get("values") or [] if v.get("value") not in (None, "")]
    return []


def extrair_dados_lead(lead: dict, contatos: list[dict], campos: dict[str, str]) -> DadosLead:
    """Extrai identificadores de clique, UTMs e contato de um lead da API v4.

    `campos` mapeia o nome padrão (gclid, fbclid…) para o nome/código/ID do campo personalizado na conta.
    Cada campo é procurado primeiro no lead e, se vazio, no contato: há contas em que a integração
    (ou o bot) grava origem e UTMs no contato.
    """
    cfv = lead.get("custom_fields_values")
    dados = DadosLead(
        lead_id=int(lead["id"]),
        status_id=lead.get("status_id"),
        pipeline_id=lead.get("pipeline_id"),
        responsavel_id=lead.get("responsible_user_id"),
        valor=float(lead["price"]) if lead.get("price") else None,
        criado_em=lead.get("created_at"),
    )
    for padrao, nome_na_conta in campos.items():
        valores = _valores_campo(cfv, nome_na_conta)
        for contato in contatos:
            if valores:
                break
            valores = _valores_campo(contato.get("custom_fields_values"), nome_na_conta)
        if not valores:
            continue
        if padrao in IDENTIFICADORES:
            dados.ids[padrao] = valores[0]
        elif padrao.startswith("utm_") or padrao in ("codigo_criativo", "origem"):
            dados.utm[padrao] = valores[0]
    dados.tags = [t["name"] for t in (lead.get("_embedded") or {}).get("tags") or [] if t.get("name")]
    motivos = (lead.get("_embedded") or {}).get("loss_reason") or []
    if motivos and motivos[0].get("name"):
        dados.motivo_perda = motivos[0]["name"]
    elif "motivo_perda" in campos:
        valores = _valores_campo(cfv, campos["motivo_perda"])
        dados.motivo_perda = valores[0] if valores else None
    for contato in contatos:
        dados.emails += _valores_campo(contato.get("custom_fields_values"), "EMAIL")
        dados.telefones += _valores_campo(contato.get("custom_fields_values"), "PHONE")
    return dados


class KommoClient:
    """Cliente mínimo da API v4 (token de longa duração ou OAuth)."""

    def __init__(self, subdominio: str, token: str, tentativas: int = 3, timeout: float = 10):
        self.base = f"https://{subdominio}.kommo.com/api/v4"
        self.token = token
        self.tentativas = tentativas
        self.timeout = timeout

    def _requisicao(self, metodo: str, caminho: str, corpo=None) -> dict:
        req = urllib.request.Request(
            self.base + caminho, method=metodo,
            data=json.dumps(corpo).encode() if corpo is not None else None,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json",
                     "Content-Type": "application/json"},
        )
        for tentativa in range(self.tentativas):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                # só GET é repetido: repetir um POST que o Kommo talvez já tenha gravado criaria duplicatas
                if metodo != "GET" or e.code not in (429, 500, 502, 503, 504) or tentativa == self.tentativas - 1:
                    raise
            time.sleep(2 ** (tentativa + 1))
        raise RuntimeError("inalcançável")

    def _get(self, caminho: str) -> dict:
        return self._requisicao("GET", caminho)

    def listar(self, caminho: str, chave: str, opcional: bool = False) -> list[dict] | None:
        """Todas as páginas de uma listagem da API v4. Com `opcional`, um 404 devolve None (recurso não exposto)."""
        itens, pagina = [], 1
        while True:
            sep = "&" if "?" in caminho else "?"
            try:
                d = self._get(f"{caminho}{sep}page={pagina}&limit=250")
            except urllib.error.HTTPError as e:
                if opcional and e.code == 404:
                    return None
                raise
            itens += (d.get("_embedded") or {}).get(chave, [])  # 204 (lista vazia) chega como {}
            if "next" not in (d.get("_links") or {}):
                return itens
            pagina += 1

    def criar(self, caminho: str, itens: list[dict]) -> dict:
        return self._requisicao("POST", caminho, itens)

    def conta(self) -> dict:
        return self._get("/account")

    def buscar_lead(self, lead_id: int) -> dict:
        return self._get(f"/leads/{lead_id}?with=contacts,loss_reason")

    def buscar_contato(self, contato_id: int) -> dict:
        return self._get(f"/contacts/{contato_id}")

    def dados_lead(self, lead_id: int, campos: dict[str, str]) -> DadosLead:
        """Lead + contato principal (no máximo 2 leituras, para caber no tempo de espera do n8n)."""
        lead = self.buscar_lead(lead_id)
        vinculados = (lead.get("_embedded") or {}).get("contacts", [])
        principal = next((c for c in vinculados if c.get("is_main")), vinculados[0] if vinculados else None)
        contatos = [self.buscar_contato(principal["id"])] if principal else []
        return extrair_dados_lead(lead, contatos, campos)
