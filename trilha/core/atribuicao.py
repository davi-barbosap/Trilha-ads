"""Canal de origem do lead, na régua da Trilha (portado do painel de mensuração da operação).

O campo "Origem" do CRM chega escrito de muitas formas ('Meta+Ads', 'Facebook',
'instagram', 'google', 'Fonte: Busca Paga | google', '(referral)', 'unknown'…).
Tudo é reduzido a um canal canônico. Origem sem regra própria sai com o nome que
o CRM registrou, nunca num balde "outros": é assim que um canal novo aparece.
"""

from __future__ import annotations

import re
import unicodedata

META = "Meta Ads"
GOOGLE = "Google Ads"
NAO_RASTREADO = "Não rastreado"
CANAIS_PAGOS = (META, GOOGLE)

_VAZIOS = {"unknown", "none", "null", "nao_definido", "not_set", "notset", "fonte_sem_fonte", "sem_fonte"}


def slug(texto: str | None) -> str:
    """Minúsculo, sem acento, separadores virando '_'."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto).replace("+", " ")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")


def _legivel(origem: str) -> str:
    nome = re.sub(r"(?i)^\s*fonte\s*:\s*", "", str(origem or "")).replace("+", " ")
    nome = re.sub(r"\s+", " ", nome).strip()
    if nome.islower() and "." not in nome:
        nome = nome.capitalize()
    return nome or NAO_RASTREADO


def normalizar_canal(origem: str | None, apelidos: dict[str, str] | None = None) -> str:
    """`apelidos` do perfil (crm.origens) valem antes da regra geral: {"trilha-performance": "Meta Ads"}."""
    s = slug(origem)
    for apelido, canal in (apelidos or {}).items():
        if s and slug(apelido) == s:
            return canal
    if not s or s in _VAZIOS or not any(c.isalpha() for c in s):
        return NAO_RASTREADO
    tokens = s.split("_")
    if any(k in s for k in ("meta", "facebook", "instagram")) or {"fb", "ig", "an"} & set(tokens):
        return META
    if "google" in s or "gads" in tokens:
        return GOOGLE
    if "indicacao" in s or "recomendacao" in s:
        return "Indicação"
    if "referral" in s:  # visita vinda de outro site (gravado pelas landing pages), não indicação de pessoa
        return "Outro site"
    if "direct" in s or "organic" in s or "site" in s:
        return "Direto/Orgânico"
    return _legivel(origem)


def eh_pago(canal: str | None) -> bool:
    return canal in CANAIS_PAGOS


# ---------- código do criativo (a célula da grade do Trilha-briefing) ----------

PADRAO_CODIGO = r"[A-Z0-9]{2,8}"  # o mesmo da grade do Trilha-briefing: PT01, GB01…
SEM_CODIGO = "sem código"
_UTM_VAZIA = {"", "—", "–", "-", "(not set)", "not set"}


def limpar_utm(valor: str | None) -> str | None:
    """Régua das UTMs: '+' vira espaço; '{{…}}' (parâmetro que a plataforma não preencheu), vazio e '—' são vazio."""
    if valor is None:
        return None
    v = str(valor).replace("+", " ").strip()
    if v.lower() in _UTM_VAZIA or (v.startswith("{{") and v.endswith("}}")):
        return None
    return v


def codigo_criativo(utm_content: str | None, padrao: str = PADRAO_CODIGO) -> str | None:
    """O código da célula no utm_content: o que vem antes de ' | ' ('VD01 | Ana' → 'VD01'), se seguir o padrão.

    Fora do padrão volta None: um código inventado no nome do anúncio não pode virar uma célula que não existe.
    """
    v = limpar_utm(utm_content)
    if v is None:
        return None
    candidato = v.split("|")[0].strip()
    return candidato if re.fullmatch(padrao, candidato) else None
