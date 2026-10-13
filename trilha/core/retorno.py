"""O que volta do Trilha-ads para o briefing e para a copy: o contrato `retorno`.

Um arquivo por período, em ads/<id>/retornos/<inicio>_<fim>.yaml no Trilha-clientes:
- `por_codigo`: leads, qualificados, agendamentos, comparecimentos e vendas de cada código de criativo (a célula da
  grade), com os custos quando o gasto por código foi informado;
- `motivos_perda`: cada motivo do Kommo com a categoria do playbook e quantos leads, do mais comum ao menos comum.

O Trilha-briefing lê com `registrar-resultados`: liga os códigos às hipóteses, mostra quais já podem ser decididas e
guarda uma cópia em briefing/<id>/resultados/. A decisão (validada, refutada) continua com o assessor.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

import yaml

from trilha.core.funil import LeadFunil, classificar_perda
from trilha.core.perfil import Perfil
from trilha.core.playbook import Playbook

VERSAO_RETORNO = 1


def periodo_dos_leads(leads: list[LeadFunil]) -> tuple[date | None, date | None]:
    datas = [l.etapas["lead"].date() for l in leads if "lead" in l.etapas]
    return (min(datas), max(datas)) if datas else (None, None)


def motivos_de_perda(leads: list[LeadFunil], playbook: Playbook) -> list[dict]:
    contagem: Counter = Counter()
    categoria: dict[str, str] = {}
    for l in leads:
        if not l.perdido_em or l.vendido() or not l.motivo_perda:
            continue
        cat, _ = classificar_perda(l, playbook)
        if cat == "duplicado":
            continue
        motivo = " ".join(l.motivo_perda.split())
        contagem[motivo] += 1
        categoria[motivo] = cat
    return [{"motivo": m, "categoria": categoria[m], "leads": n} for m, n in contagem.most_common()]


def montar_retorno(r: dict, leads: list[LeadFunil], perfil: Perfil, playbook: Playbook,
                   inicio: date | None = None, fim: date | None = None) -> dict:
    """O retorno do período a partir do raio-x já calculado (`raio_x(...)`) e dos leads."""
    de, ate = periodo_dos_leads(leads)
    return {
        "retorno": VERSAO_RETORNO,
        "cliente": perfil.cliente.id,
        "periodo": {"inicio": (inicio or de), "fim": (fim or ate)},
        "gerado_em": date.today(),
        "leads": r["leads"],
        "por_codigo": {codigo: dict(d) for codigo, d in r["por_criativo"].items()},
        "motivos_perda": motivos_de_perda(leads, playbook),
        "perdas_por_categoria": dict(r["perdas"]["por_categoria"]),
    }


def gravar_retorno(retorno: dict, pasta: str | Path) -> Path:
    p = retorno["periodo"]
    nome = f"{p['inicio'] or 'inicio'}_{p['fim'] or 'fim'}.yaml"
    destino = Path(pasta) / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    cab = ("# Retorno do Trilha-ads para o briefing e a copy (contrato retorno, versão 1).\n"
           "# Gerado por: python -m trilha raio-x ... --retorno <pasta>. Não edite: gere de novo.\n"
           f"# No briefing: python -m trilha_briefing registrar-resultados {destino} briefing/{retorno['cliente']}\n")
    destino.write_text(cab + yaml.safe_dump(retorno, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    return destino
