"""Playbook de segmento: nomes das etapas, referências de conversão e motivos de perda.

O funil é o mesmo para todos os segmentos (perfil.ETAPAS_FUNIL). O playbook muda só o
nome exibido de cada etapa, as taxas de referência e a lista de motivos de perda.
Segmento sem playbook próprio usa `playbooks/padrao/`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from trilha.core.oferta import ITENS_ADERENCIA
from trilha.core.perfil import Etapa

CategoriaPerda = Literal["lead", "atendimento", "comercial", "externo", "duplicado"]
Fracao = Annotated[float, Field(gt=0, le=1)]

RAIZ_PLAYBOOKS = Path(os.environ.get("TRILHA_PLAYBOOKS_DIR", Path(__file__).resolve().parents[2] / "playbooks"))


class Playbook(BaseModel):
    model_config = ConfigDict(extra="ignore")

    segmento: str
    rotulos_etapas: dict[Etapa, str] = Field(default_factory=dict)
    # conversão esperada da etapa anterior para esta (ex.: comparecimento: 0.65 = 65% dos agendados comparecem)
    taxas_referencia: dict[Etapa, Fracao] = Field(default_factory=dict)
    motivos_perda: dict[str, CategoriaPerda] = Field(default_factory=dict)
    perguntas_aderencia: list[str] = Field(default_factory=list)
    # itens do diagnóstico de aderência que contam como pendência (oferta.ITENS_ADERENCIA); vazio = todos
    aderencia_exige: list[str] = Field(default_factory=list)

    @field_validator("aderencia_exige")
    @classmethod
    def _itens_conhecidos(cls, v: list[str]) -> list[str]:
        fora = [x for x in v if x not in ITENS_ADERENCIA]
        if fora:
            raise ValueError(f"itens de aderência que não existem: {fora} (use: {', '.join(ITENS_ADERENCIA)})")
        return v

    def exige_na_aderencia(self) -> list[str]:
        return self.aderencia_exige or list(ITENS_ADERENCIA)

    def rotulo(self, etapa: str) -> str:
        return self.rotulos_etapas.get(etapa, etapa.replace("_", " "))


def carregar_playbook(segmento: str, raiz: Path | None = None) -> Playbook:
    """Playbook do segmento sobre o padrão: o que o segmento define substitui o padrão, chave a chave."""
    raiz = raiz or RAIZ_PLAYBOOKS
    with open(raiz / "padrao" / "playbook.yaml", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    proprio = raiz / segmento / "playbook.yaml"
    if re.fullmatch(r"[a-z0-9_-]+", segmento) and segmento != "padrao" and proprio.is_file():
        with open(proprio, encoding="utf-8") as f:
            especifico = yaml.safe_load(f)
        for chave, valor in especifico.items():
            if isinstance(valor, dict) and isinstance(dados.get(chave), dict):
                dados[chave] = {**dados[chave], **valor}
            else:
                dados[chave] = valor
    return Playbook.model_validate(dados)
