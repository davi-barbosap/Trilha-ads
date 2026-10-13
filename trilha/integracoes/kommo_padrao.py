"""Kommo no padrão da Trilha: funil, campos de rastreamento e motivos de perda (docs/integracoes/kommo.md §4).

`planejar()` é pura: compara o que existe na conta com o padrão e devolve só o que falta. Nada que já existe
é alterado ou apagado, então rodar de novo é seguro. `aplicar()` cria o que o plano pede.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from trilha.core.playbook import Playbook

# Campos personalizados que o sistema lê ou que as ferramentas paralelas gravam (Trilha-LP, BotConversa, GTM).
# Fonte única: o comando `kommo preparar` e a documentação seguem esta lista.
CAMPOS_TEXTO = (
    "gclid", "gbraid", "wbraid", "fbclid", "ttclid", "ctwa_clid", "meta_lead_id",
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "codigo_criativo", "landing_page", "event_id_lead",
)
ORIGENS = ("meta", "google", "tiktok", "portal_zap", "portal_vivareal", "portal_olx", "indicacao", "organico", "site", "lista")

# Etapas criadas no funil, na ordem do funil padrão (ADR-008). Ganho (142) e perdido (143) o Kommo cria sozinho.
ETAPAS_DO_FUNIL = ("lead", "em_atendimento", "lead_qualificado", "agendamento", "comparecimento", "proposta")
_CORES = ("#c1e0ff", "#98cbff", "#fffeb2", "#ffdc7f", "#ffce5a", "#deff81")  # paleta aceita pelo Kommo


@dataclass
class EstadoConta:
    funis: list[dict] = field(default_factory=list)            # /leads/pipelines (com _embedded.statuses)
    campos: list[dict] = field(default_factory=list)           # /leads/custom_fields
    motivos_perda: list[dict] | None = None                    # /leads/loss_reasons; None = API não expõe


@dataclass
class Plano:
    funil: dict | None = None                                  # corpo do POST, se o funil não existir
    campos: list[dict] = field(default_factory=list)
    motivos_perda: list[dict] = field(default_factory=list)
    motivos_indisponiveis: bool = False                        # cadastrar à mão em Configurações

    @property
    def vazio(self) -> bool:
        return not (self.funil or self.campos or self.motivos_perda)


def planejar(estado: EstadoConta, playbook: Playbook, nome_funil: str) -> Plano:
    plano = Plano()

    if not any(f.get("name") == nome_funil for f in estado.funis):
        plano.funil = {
            "name": nome_funil, "is_main": False, "is_unsorted_on": False, "sort": 50,
            "_embedded": {"statuses": [
                {"name": playbook.rotulo(etapa), "sort": (i + 1) * 10, "color": _CORES[i]}
                for i, etapa in enumerate(ETAPAS_DO_FUNIL)
            ]},
        }

    existentes = {(c.get("name") or "").strip().lower() for c in estado.campos}
    plano.campos = [{"name": n, "type": "text"} for n in CAMPOS_TEXTO if n not in existentes]
    if "origem" not in existentes:
        plano.campos.append({"name": "origem", "type": "select",
                             "enums": [{"value": v, "sort": (i + 1) * 10} for i, v in enumerate(ORIGENS)]})

    if estado.motivos_perda is None:
        plano.motivos_indisponiveis = True
    else:
        nomes = {m.get("name") for m in estado.motivos_perda}
        faltam = [m for m in playbook.motivos_perda if m not in nomes]
        plano.motivos_perda = [{"name": m, "sort": (i + 1) * 10} for i, m in enumerate(faltam)]
    return plano


def ler_estado(cliente) -> EstadoConta:
    """`cliente` é um KommoClient."""
    return EstadoConta(
        funis=cliente.listar("/leads/pipelines", "pipelines"),
        campos=cliente.listar("/leads/custom_fields", "custom_fields"),
        motivos_perda=cliente.listar("/leads/loss_reasons", "loss_reasons", opcional=True),
    )


def aplicar(cliente, plano: Plano) -> None:
    if plano.funil:
        cliente.criar("/leads/pipelines", [plano.funil])
    if plano.campos:
        cliente.criar("/leads/custom_fields", plano.campos)
    if plano.motivos_perda:
        cliente.criar("/leads/loss_reasons", plano.motivos_perda)


def mapa_eventos(funil: dict, playbook: Playbook) -> list[dict]:
    """Bloco `crm.mapa_eventos` do perfil.yaml a partir do funil criado, casando cada etapa pelo rótulo do playbook.

    A etapa de entrada que o Kommo cria sozinho (antes da primeira) também conta como `lead`.
    """
    por_rotulo = {playbook.rotulo(e): e for e in ETAPAS_DO_FUNIL}
    mapa = []
    for s in (funil.get("_embedded") or {}).get("statuses", []):
        if s["id"] in (142, 143):
            continue
        evento = por_rotulo.get(s["name"])
        if evento is None and not mapa:
            evento = "lead"  # etapa de entrada criada pelo Kommo
        if evento:
            mapa.append({"pipeline_id": funil["id"], "status_id": s["id"], "evento": evento, "_etapa": s["name"]})
    return mapa
