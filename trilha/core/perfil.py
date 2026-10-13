"""Esquema validado do perfil.yaml do cliente (núcleo §4, §7.2, §10; modelo-operacional.md).

O perfil é o contrato entre o cadastro do cliente (parte exportada pelo Trilha-briefing, o resto
preenchido pelo assessor) e o núcleo: nenhum módulo liga com um perfil que não passe por aqui.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Funil padrão da Trilha, igual para todos os segmentos (o playbook só muda os nomes exibidos).
ETAPAS_FUNIL = ("lead", "em_atendimento", "lead_qualificado", "agendamento", "comparecimento", "proposta", "venda")
Etapa = Literal["lead", "em_atendimento", "lead_qualificado", "agendamento", "comparecimento", "proposta", "venda"]
Evento = Literal[
    "lead", "em_atendimento", "lead_qualificado", "agendamento", "comparecimento", "proposta", "venda",
    "perdido", "reativado",
]
ModeloReceita = Literal["venda_direta", "comissao", "recorrencia"]
DiaUtil = Literal["segunda", "terca", "quarta", "quinta", "sexta"]
Fracao = Annotated[float, Field(gt=0, le=1)]
Positivo = Annotated[float, Field(gt=0)]

# Etapas de sistema do Kommo, iguais em todas as contas.
KOMMO_STATUS_GANHO = 142
KOMMO_STATUS_PERDIDO = 143

class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Mesmo formato do nome da pasta do cliente em trilha-clientes (e do cliente_id da API).
ClienteId = Annotated[str, Field(pattern=r"^[a-z0-9_][a-z0-9_-]{0,63}$")]

# Blocos de versões anteriores: ignorados, com aviso no `validar`.
BLOCOS_LEGADOS = {"autonomia": "substituído pelo bloco freio (ADR-006); pode ser apagado"}


class Cliente(_Base):
    id: ClienteId
    nome: str
    segmento: str  # aponta para playbooks/<segmento>/


class Economia(_Base):
    """Entradas da calculadora de economia unitária (núcleo §3.1)."""

    modelo_receita: ModeloReceita
    # venda_direta
    ticket_medio: Positivo | None = None
    # comissao
    valor_medio_bem: Positivo | None = None
    comissao_pct: Fracao | None = None
    participacao_comissao: Fracao = 1.0
    # recorrencia
    mensalidade: Positivo | None = None
    meses_retencao: Positivo | None = None

    margem_contribuicao: Fracao
    pct_investivel: Fracao
    taxa_fechamento: Fracao
    taxa_qualificacao: Fracao
    taxa_agendamento: Fracao | None = None
    estimados: list[str] = Field(default_factory=list)  # campos que vieram do playbook

    @model_validator(mode="after")
    def _coerencia(self) -> Economia:
        exigidos = {
            "venda_direta": ("ticket_medio",),
            "comissao": ("valor_medio_bem", "comissao_pct"),
            "recorrencia": ("mensalidade", "meses_retencao"),
        }[self.modelo_receita]
        faltando = [c for c in exigidos if getattr(self, c) is None]
        if faltando:
            raise ValueError(f"modelo_receita={self.modelo_receita} exige: {', '.join(faltando)}")
        if self.taxa_qualificacao < self.taxa_fechamento:
            raise ValueError("taxa_qualificacao não pode ser menor que taxa_fechamento")
        if self.taxa_agendamento is not None and not (
            self.taxa_fechamento <= self.taxa_agendamento <= self.taxa_qualificacao
        ):
            raise ValueError("esperado taxa_fechamento ≤ taxa_agendamento ≤ taxa_qualificacao")
        desconhecidos = set(self.estimados) - set(type(self).model_fields)
        if desconhecidos:
            raise ValueError(f"estimados cita campos inexistentes: {sorted(desconhecidos)}")
        return self


class Verba(_Base):
    mensal_planejada: Positivo
    teto_mensal: Positivo | None = None
    moeda: str = "BRL"


class Meta(_Base):
    ad_account_id: str | None = None
    ad_account_ids: list[str] = Field(default_factory=list)  # cliente com mais de uma conta (ex.: vendas e pós-venda)
    pixel_id: str | None = None  # conjunto de dados da API de Conversões
    page_id: str | None = None  # necessário para eventos de WhatsApp (business_messaging)

    def contas(self) -> list[str]:
        return list(dict.fromkeys(([self.ad_account_id] if self.ad_account_id else []) + self.ad_account_ids))


class Google(_Base):
    customer_id: str | None = None
    login_customer_id: str | None = None  # MCC


class Plataformas(_Base):
    meta: Meta | None = None
    google: Google | None = None


class MapaEvento(_Base):
    pipeline_id: int | None = None  # None = qualquer funil
    status_id: int
    evento: Evento
    # Para etapas de saída que não são o 143 ("Descartado", "Frio"): motivo usado quando o lead não tem um.
    motivo: str | None = None


class Funil(_Base):
    """Um funil (pipeline) do Kommo e o papel dele na operação.

    O status 142 ("ganho") muda de sentido conforme o funil: no Closer é venda; no SDR
    costuma ser "reunião realizada". Por isso o significado vem do papel do funil.
    """

    pipeline_id: int
    nome: str = ""
    # entrada: onde o lead nasce (SDR) · fechamento: onde a venda acontece (Closer)
    # nutricao: leads em nutrição · base: trabalho sobre base importada · ignorar: teste
    papel: Literal["entrada", "fechamento", "nutricao", "base", "ignorar"]
    ganho_significa: Evento | None = None  # obrigatório para o 142 contar fora do funil de fechamento

    @model_validator(mode="after")
    def _ganho(self) -> Funil:
        if self.papel == "fechamento" and self.ganho_significa is None:
            self.ganho_significa = "venda"
        return self


class TagsCrm(_Base):
    """Nomes das tags do Kommo que o raio-x lê. Comparação sem maiúsculas e sem acento;
    "lead reativado" também reconhece "lead reativado | follow-up"."""

    bot_concluido: list[str] = Field(default_factory=lambda: ["bot-concluido", "Interesse Confirmado"])
    bot_incompleto: list[str] = Field(default_factory=lambda: ["bot-incompleto"])
    bot_nao_iniciado: list[str] = Field(default_factory=lambda: ["bot-nao-iniciado", "lead frio"])
    interagiu: list[str] = Field(default_factory=lambda: ["Interagiu"])
    qualificado: list[str] = Field(default_factory=lambda: ["lead-qualificado"])
    agendamento: list[str] = Field(default_factory=lambda: ["reuniao-agendada", "reagendar-reuniao", "visita-agendada"])
    comparecimento: list[str] = Field(default_factory=lambda: ["reuniao-realizada", "visita-realizada"])
    reativado: list[str] = Field(default_factory=lambda: ["lead reativado", "reativado"])
    contato_invalido: list[str] = Field(default_factory=lambda: ["nao-cadastrou"])


class HorarioComercial(_Base):
    dias: list[Annotated[int, Field(ge=0, le=6)]] = Field(default_factory=lambda: [0, 1, 2, 3, 4])  # 0 = segunda
    inicio: Annotated[int, Field(ge=0, le=23)] = 8
    fim: Annotated[int, Field(ge=1, le=24)] = 18
    fuso_utc: Annotated[int, Field(ge=-12, le=14)] = -3


class Crm(_Base):
    tipo: Literal["kommo"] = "kommo"
    subdominio: str
    funis: list[Funil] = Field(default_factory=list)  # vazio = conta com um funil só
    mapa_eventos: list[MapaEvento] = Field(default_factory=list)
    campos: dict[str, str] = Field(default_factory=dict)
    sla_primeiro_contato_min: Positivo = 30  # do time comercial do cliente com o lead
    tags: TagsCrm = Field(default_factory=TagsCrm)
    origens: dict[str, str] = Field(default_factory=dict)  # apelidos do cliente: {"trilha-performance": "Meta Ads"}
    baldes: list[str] = Field(default_factory=list)  # usuários que não são pessoas (ex.: o usuário da empresa)
    gestores: list[str] = Field(default_factory=list)  # aparecem no raio-x, fora da média e dos sinais por pessoa
    dias_parado: Annotated[int, Field(ge=1)] = 15
    dias_base_velha: Annotated[int, Field(ge=1)] = 30
    horario_comercial: HorarioComercial = Field(default_factory=HorarioComercial)

    def funil(self, pipeline_id: int | None) -> Funil | None:
        return next((f for f in self.funis if f.pipeline_id == pipeline_id), None)

    def mapa_completo(self) -> list[MapaEvento]:
        """Mapa do cliente + etapas de sistema do Kommo (142 e 143), resolvidas pelo papel de cada funil."""
        mapa = list(self.mapa_eventos)
        configurados = {(m.pipeline_id, m.status_id) for m in mapa}
        if not self.funis:
            for status, evento in ((KOMMO_STATUS_GANHO, "venda"), (KOMMO_STATUS_PERDIDO, "perdido")):
                if not any(s == status for _, s in configurados):
                    mapa.append(MapaEvento(status_id=status, evento=evento))
            return mapa
        for f in self.funis:
            if f.papel in ("base", "ignorar"):
                continue
            if f.ganho_significa and (f.pipeline_id, KOMMO_STATUS_GANHO) not in configurados:
                mapa.append(MapaEvento(pipeline_id=f.pipeline_id, status_id=KOMMO_STATUS_GANHO, evento=f.ganho_significa))
            if (f.pipeline_id, KOMMO_STATUS_PERDIDO) not in configurados:
                mapa.append(MapaEvento(pipeline_id=f.pipeline_id, status_id=KOMMO_STATUS_PERDIDO, evento="perdido"))
        return mapa

    def evento_para(self, status_id: int, pipeline_id: int | None) -> Evento | None:
        f = self.funil(pipeline_id)
        if f is not None and f.papel in ("base", "ignorar"):
            return None
        if self.funis and f is None:
            return None  # funil não cadastrado: na dúvida, não gera evento
        m = self._mapa_para(status_id, pipeline_id)
        return m.evento if m else None

    def motivo_para(self, status_id: int, pipeline_id: int | None) -> str | None:
        """Motivo de uma etapa de saída que não é o 143 (ex.: "Descartado" → "Contato inválido")."""
        m = self._mapa_para(status_id, pipeline_id)
        return m.motivo if m and self.evento_para(status_id, pipeline_id) else None

    def _mapa_para(self, status_id: int, pipeline_id: int | None) -> MapaEvento | None:
        for m in self.mapa_completo():
            if m.status_id == status_id and (m.pipeline_id is None or m.pipeline_id == pipeline_id):
                return m
        return None


class Destino(_Base):
    meta_event_name: str | None = None
    google_conversion_action_id: str | None = None
    # nenhum: sem valor · receita: receita real da venda (comissão, quando for o caso)
    # ponderado: custo máximo do evento pela calculadora (núcleo §7.2, alternativa 3)
    valor: Literal["nenhum", "receita", "ponderado"] = "nenhum"


class Conversao(_Base):
    eventos_semana_aprendizado: Annotated[int, Field(gt=0)] = 50
    destinos: dict[Evento, Destino] = Field(default_factory=dict)


class Freio(_Base):
    """Freio de emergência (ADR-006): a única ação automática do sistema.

    modo "pausar" (opção A, padrão): pausa e avisa na hora; desfazer é um clique.
    modo "avisar" (opção B): só avisa; a pausa fica com o responsável.
    """

    modo: Literal["pausar", "avisar"] = "pausar"
    gasto_sem_lead_multiplo: Positivo = 3.0  # × CPL máximo, desde o último lead
    horas_rastreamento_quebrado: Positivo = 6.0  # gastando sem nenhum evento de conversão registrado


class Operacao(_Base):
    """Agenda do assessor com o cliente — o sistema deixa pronto, na véspera, o material de cada compromisso.

    Contato com o cliente (contatos proativos, respostas no grupo) é do assessor e não entra aqui.
    """

    responsavel: str
    dia_otimizacao: DiaUtil
    dia_relatorio: DiaUtil
    semana_reuniao: Annotated[int, Field(ge=1, le=4)]  # semana do mês da reunião mensal
    dia_reuniao: DiaUtil = "sexta"
    faixa: Literal["essencial", "performance", "escala"] = "essencial"


class Perfil(_Base):
    @model_validator(mode="before")
    @classmethod
    def _ignorar_legado(cls, dados):
        if isinstance(dados, dict) and any(b in dados for b in BLOCOS_LEGADOS):
            dados = {k: v for k, v in dados.items() if k not in BLOCOS_LEGADOS}
        return dados

    versao: Annotated[int, Field(ge=1)]
    vigente_desde: date
    cliente: Cliente
    metrica_principal: Evento
    economia: Economia
    verba: Verba
    plataformas: Plataformas = Field(default_factory=Plataformas)
    crm: Crm | None = None
    conversao: Conversao = Field(default_factory=Conversao)
    freio: Freio = Field(default_factory=Freio)
    operacao: Operacao | None = None


def avisos_legado(caminho: str | Path) -> list[str]:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f) or {}
    return [f"bloco '{b}' ignorado: {motivo}" for b, motivo in BLOCOS_LEGADOS.items() if b in bruto]


def carregar_perfil(caminho: str | Path) -> Perfil:
    with open(caminho, encoding="utf-8") as f:
        return Perfil.model_validate(yaml.safe_load(f))
