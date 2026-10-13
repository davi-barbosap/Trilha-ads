"""Raio-x do funil: o que acontece entre o lead que entrou e a venda que saiu.

Calcula, etapa por etapa, quantos leads passaram, quanto tempo levaram, onde e por que
foram perdidos, e qual vazamento custa mais vendas. Separa o que o marketing entregou
do que o comercial converteu. Atribui vendas a campanhas pelo próprio Kommo, sem
depender da janela de atribuição das plataformas.

O sistema mostra onde está o maior vazamento e quanto ele custa; a leitura é do assessor.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trilha.core.atribuicao import NAO_RASTREADO, eh_pago, slug
from trilha.core.perfil import ETAPAS_FUNIL, Crm, Etapa, HorarioComercial, TagsCrm
from trilha.core.playbook import Playbook

# De quem é cada passagem: chegar à etapa X depende de...
LADO_DA_ETAPA = {
    "em_atendimento": "atendimento",
    "lead_qualificado": "qualificacao",
    "agendamento": "comercial",
    "comparecimento": "comercial",
    "proposta": "comercial",
    "venda": "comercial",
}
ETAPAS_DO_MARKETING = ("lead", "lead_qualificado", "agendamento")
AMOSTRA_MINIMA = 20
AMOSTRA_MINIMA_SDR = 20  # leads, para o perfil por pessoa ser comparável
AMOSTRA_MINIMA_CLOSER = 5  # comparecimentos
DIAS_PARADO = 15
DIAS_BASE_VELHA = 30
PRIMEIRO_CONTATO_MAXIMO_MIN = 30 * 24 * 60  # acima disso (ou negativo) é erro de registro, não tempo de resposta
# "Responsáveis" que são baldes do sistema, não pessoas.
PSEUDO_RESPONSAVEIS = {"descarte", "sem corretor", "sem responsável", "(sem corretor)", "sem responsavel"}
# Perfil por pessoa: pesos das dimensões (painel de ranking do time comercial), notas relativas ao time.
PESOS_PERFIL = {"vendas": 28, "conversao": 20, "volume": 16, "primeiro_contato": 16, "movimentacao": 10, "consistencia": 10}
# Distribuição de leads entre pessoas (painel de distribuição de leads): desequilíbrio a partir de 1,6× ou até 0,5× a média.
DISTRIBUICAO_ALTA, DISTRIBUICAO_BAIXA, DISTRIBUICAO_MEDIA_MINIMA = 1.6, 0.5, 3


def semana_do_mes(d: datetime) -> str:
    """Semanas fixas da Trilha: w1 = 1–7, w2 = 8–14, w3 = 15–21, w4 = 22 até o fim do mês."""
    return "w1" if d.day <= 7 else "w2" if d.day <= 14 else "w3" if d.day <= 21 else "w4"


class LeadFunil(BaseModel):
    """Histórico de um lead no Kommo, normalizado."""

    model_config = ConfigDict(extra="forbid")

    lead_id: int
    etapas: dict[Etapa, datetime] = Field(default_factory=dict)  # quando entrou em cada etapa
    perdido_em: datetime | None = None
    motivo_perda: str | None = None
    tentativas_contato: int | None = None
    responsavel: str | None = None  # quem atende e qualifica (SDR, corretor)
    closer: str | None = None  # quem conduz reunião, proposta e fechamento, quando é outra pessoa
    pessoa: str | None = None  # chave da pessoa (hash do telefone) para deduplicar
    canal: str | None = None  # canal canônico (atribuicao.normalizar_canal)
    campanha: str | None = None  # utm_campaign gravada no lead
    criativo: str | None = None  # utm_content gravada no lead
    score: str | None = None  # lead score do CRM/bot (A, B, C…)
    bot: Literal["concluido", "incompleto", "nao_iniciado"] | None = None
    interagiu: bool | None = None  # houve mensagem humana e o lead respondeu depois
    produto: str | None = None
    valor: float | None = None  # valor do negócio (VGV no imobiliário)
    ultima_movimentacao: datetime | None = None
    # Primeira mensagem de saída enviada por uma pessoa (Kommo: created_by != 0). Mensagem de bot não conta.
    primeiro_contato_humano: datetime | None = None
    reativado: bool | None = None  # voltou da nutrição/reativação
    tags: list[str] = Field(default_factory=list)  # tags do lead no Kommo, lidas conforme crm.tags
    marcas: list[Etapa] = Field(default_factory=list)  # etapas confirmadas sem data (ex.: tag de reunião realizada)

    def indice(self) -> int:
        """Etapa mais avançada alcançada (etapas puladas contam como passadas)."""
        return max((ETAPAS_FUNIL.index(e) for e in (*self.etapas, *self.marcas)), default=0)

    def alcancou(self, etapa: str) -> bool:
        return self.indice() >= ETAPAS_FUNIL.index(etapa)

    def vendido(self) -> bool:
        return "venda" in self.etapas


def classificar_perda(lead: LeadFunil, playbook: Playbook) -> tuple[str, str]:
    """(categoria, momento) de uma perda. Categoria vem do motivo; momento, da etapa."""
    if lead.motivo_perda is None:
        categoria = "sem_motivo"
    else:
        categoria = playbook.motivos_perda.get(lead.motivo_perda, "nao_classificado")
    momento = "depois_da_qualificacao" if lead.alcancou("lead_qualificado") else "antes_da_qualificacao"
    return categoria, momento


def _tag_bate(tag: str, nomes: list[str]) -> bool:
    """Compara sem maiúsculas e sem acento; "lead reativado | follow-up" bate com "lead reativado"."""
    base = slug(tag.split("|")[0])
    return bool(base) and base in {slug(n) for n in nomes}


def aplicar_tags(lead: LeadFunil, regras: TagsCrm) -> None:
    """Lê as tags do Kommo para os campos do lead. O que veio preenchido pela coleta prevalece."""
    tem = {campo: any(_tag_bate(t, nomes) for t in lead.tags) for campo, nomes in regras}
    if lead.bot is None:
        lead.bot = next((e for e, c in (("concluido", "bot_concluido"), ("incompleto", "bot_incompleto"),
                                        ("nao_iniciado", "bot_nao_iniciado")) if tem[c]), None)
    if tem["interagiu"]:
        lead.interagiu = True
    for etapa in ("lead_qualificado", "agendamento", "comparecimento"):
        campo = "qualificado" if etapa == "lead_qualificado" else etapa
        if tem[campo] and etapa not in lead.etapas and etapa not in lead.marcas:
            lead.marcas.append(etapa)
    if tem["reativado"]:
        lead.reativado = True
    if tem["contato_invalido"] and not lead.vendido():
        lead.motivo_perda = lead.motivo_perda or "Contato inválido"
        lead.perdido_em = lead.perdido_em or lead.ultima_movimentacao or max(lead.etapas.values(), default=None)


def minutos_primeiro_contato(lead: LeadFunil) -> float | None:
    """Entrada → primeira mensagem humana; sem ela, entrada em atendimento; sem ela, a qualificação."""
    inicio = lead.etapas.get("lead")
    fim = lead.primeiro_contato_humano or lead.etapas.get("em_atendimento") or lead.etapas.get("lead_qualificado")
    if not inicio or not fim:
        return None
    minutos = (fim - inicio).total_seconds() / 60
    return minutos if 0 <= minutos < PRIMEIRO_CONTATO_MAXIMO_MIN else None


def _horas(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 3600


def _mediana(valores: list[float]) -> float | None:
    return round(median(valores), 1) if valores else None


def _taxa(parte: int, todo: int) -> float | None:
    return round(parte / todo, 4) if todo else None


def deduplicar(leads: list[LeadFunil]) -> tuple[list[LeadFunil], int, int]:
    """Régua canônica da Trilha.

    Lead: a mesma pessoa conta uma vez por mês de entrada (quem volta no mês seguinte
    é uma nova entrada). Venda: mesma pessoa, mesmo dia, mesmo valor e mesmo produto
    é o mesmo negócio cadastrado duas vezes; duas unidades no mesmo dia são duas vendas.
    """
    ordenados = sorted(leads, key=lambda l: l.etapas.get("lead") or min(l.etapas.values(), default=datetime.max.replace(tzinfo=timezone.utc)))
    vistos, saida, leads_dup = set(), [], 0
    for l in ordenados:
        entrada = l.etapas.get("lead")
        if l.pessoa and entrada:
            chave = (l.pessoa, entrada.year, entrada.month)
            if chave in vistos and not l.vendido():
                leads_dup += 1
                continue
            vistos.add(chave)
        saida.append(l)
    vendas_vistas, vendas_dup = set(), 0
    for l in saida:
        if l.vendido() and l.pessoa:
            chave = (l.pessoa, l.etapas["venda"].date(), l.valor, l.produto)
            if chave in vendas_vistas:
                l.etapas.pop("venda")
                vendas_dup += 1
            vendas_vistas.add(chave)
    return saida, leads_dup, vendas_dup


def _div(a: float | None, b: float | None) -> float | None:
    return round(a / b, 2) if a and b else None


def _resumo(leads: list[LeadFunil]) -> dict:
    vendidos = [l for l in leads if l.vendido()]
    return {
        "leads": len(leads),
        "qualificados": sum(l.alcancou("lead_qualificado") for l in leads),
        "comparecimentos": sum(l.alcancou("comparecimento") for l in leads),
        "vendas": len(vendidos),
        "valor_vendido": sum(l.valor or 0 for l in vendidos),
    }


def _local(d: datetime, horario: HorarioComercial) -> datetime:
    """Horário local do cliente (o Kommo devolve UTC)."""
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone(timedelta(hours=horario.fuso_utc)))


def _no_horario(d: datetime, horario: HorarioComercial) -> bool:
    d = _local(d, horario)
    return d.weekday() in horario.dias and horario.inicio <= d.hour < horario.fim


def minutos_uteis(inicio: datetime, fim: datetime, horario: HorarioComercial) -> float:
    """Minutos de expediente entre dois instantes: lead que chega às 23h e é atendido às 8h05 esperou 5 minutos úteis."""
    a, b = _local(inicio, horario), _local(fim, horario)
    total, dia = 0.0, a.replace(hour=0, minute=0, second=0, microsecond=0)
    while dia < b:
        if dia.weekday() in horario.dias:
            abre, fecha = dia + timedelta(hours=horario.inicio), dia + timedelta(hours=horario.fim)
            total += max(0.0, (min(b, fecha) - max(a, abre)).total_seconds() / 60)
        dia += timedelta(days=1)
    return total


def _pessoa_do_time(nome: str | None, baldes: set[str]) -> bool:
    return bool(nome) and nome.strip().lower() not in baldes


def _notas_relativas(valores: dict[str, float | None]) -> dict[str, float]:
    """Melhor do time = 100, pior = 0; empate = 50; sem dado = nota do pior."""
    presentes = [v for v in valores.values() if v is not None]
    if not presentes:
        return {k: 50.0 for k in valores}
    lo, hi = min(presentes), max(presentes)
    return {k: 50.0 if hi == lo else (0.0 if v is None else (v - lo) / (hi - lo) * 100) for k, v in valores.items()}


def raio_x(
    leads: list[LeadFunil],
    playbook: Playbook,
    investimento: float | None = None,
    sla_primeiro_contato_min: float | None = None,
    referencia: dict[str, float] | None = None,
    valor_medio_venda: float | None = None,
    agora: datetime | None = None,
    dias_parado: int | None = None,
    crm: Crm | None = None,
    investimento_captacao: float | None = None,
) -> dict:
    """Raio-x de um período (safra de leads).

    `crm` traz as regras do cliente (tags, baldes, gestores, expediente, dias de parado, prazo de primeiro
    contato); os parâmetros explícitos prevalecem. `referencia` (conversão por etapa) padrão: a do playbook.
    `investimento_captacao` (sem campanhas de topo de funil) é o divisor do CPL; os demais custos usam o total.
    """
    crm = crm or Crm(subdominio="-")
    sla = sla_primeiro_contato_min if sla_primeiro_contato_min is not None else crm.sla_primeiro_contato_min
    dias_parado = dias_parado if dias_parado is not None else crm.dias_parado
    horario = crm.horario_comercial
    baldes = PSEUDO_RESPONSAVEIS | {b.strip().lower() for b in crm.baldes}
    gestores = {g.strip().lower() for g in crm.gestores}
    referencia = referencia if referencia is not None else dict(playbook.taxas_referencia)

    leads = [l.model_copy(deep=True) for l in leads]
    for l in leads:
        aplicar_tags(l, crm.tags)
    if any(l.interagiu for l in leads):  # a conta usa a tag: quem não a tem não interagiu
        for l in leads:
            l.interagiu = bool(l.interagiu)
    leads, leads_duplicados, vendas_duplicadas = deduplicar(leads)
    n = len(leads)
    # Investimento só paga mídia: custos dividem pelo que veio de Meta/Google. Sem canal informado, todos contam.
    canal_informado = any(l.canal for l in leads)
    pagos = [l for l in leads if eh_pago(l.canal)] if canal_informado else leads

    # 1. Etapa por etapa
    alcancaram = {e: [l for l in leads if l.alcancou(e)] for e in ETAPAS_FUNIL}
    etapas = []
    for i, etapa in enumerate(ETAPAS_FUNIL):
        anterior = ETAPAS_FUNIL[i - 1] if i else None
        tempos = [
            _horas(l.etapas[anterior], l.etapas[etapa])
            for l in alcancaram[etapa]
            if anterior and anterior in l.etapas and etapa in l.etapas
        ]
        etapas.append({
            "etapa": etapa,
            "rotulo": playbook.rotulo(etapa),
            "lado": LADO_DA_ETAPA.get(etapa, "marketing"),
            "entraram": len(alcancaram[etapa]),
            "conversao_da_anterior": _taxa(len(alcancaram[etapa]), len(alcancaram[anterior])) if anterior else None,
            "referencia": referencia.get(etapa),
            "mediana_horas_desde_anterior": _mediana(tempos),
        })

    # 2. Primeiro contato (minutos de expediente; corridos à parte) e cadência do time comercial do cliente
    def _contato(ls):
        corridos, uteis = [], []
        for l in ls:
            m = minutos_primeiro_contato(l)
            if m is None:
                continue
            fim = l.etapas["lead"] + timedelta(minutes=m)
            corridos.append(m)
            uteis.append(minutos_uteis(l.etapas["lead"], fim, horario))
        return corridos, uteis

    corridos, uteis = _contato(leads)
    perdidos_antes = [l for l in leads if l.perdido_em and not l.alcancou("lead_qualificado")]
    no_horario = [l for l in leads if "lead" in l.etapas and _no_horario(l.etapas["lead"], horario)]
    fora_horario = [l for l in leads if "lead" in l.etapas and not _no_horario(l.etapas["lead"], horario)]
    primeiro_contato = {
        "sla_minutos": sla,
        "mediana_minutos_uteis": _mediana(uteis),
        "mediana_minutos_corridos": _mediana(corridos),
        "dentro_do_sla": _taxa(sum(m <= sla for m in uteis), len(uteis)),
        "medido_pela_mensagem_humana": sum(1 for l in leads if l.primeiro_contato_humano and minutos_primeiro_contato(l) is not None),
        "sem_primeiro_contato": sum(not l.primeiro_contato_humano and not l.alcancou("em_atendimento") for l in leads),
        "mediana_minutos_corridos_chegou_no_horario": _mediana(_contato(no_horario)[0]),
        "mediana_minutos_corridos_chegou_fora_do_horario": _mediana(_contato(fora_horario)[0]),
    }
    cadencia = {
        "mediana_tentativas_perdidos_antes_de_qualificar": _mediana(
            [l.tentativas_contato for l in perdidos_antes if l.tentativas_contato is not None]
        ),
        "mediana_tentativas_qualificados": _mediana(
            [l.tentativas_contato for l in alcancaram["lead_qualificado"] if l.tentativas_contato is not None]
        ),
    }

    # 3. Perdas: por etapa, por categoria, e critério de qualificação. Lead duplicado é dado, não perda.
    perdas_etapa: dict[str, Counter] = defaultdict(Counter)
    perdas_categoria: Counter = Counter()
    criterio_a_revisar = duplicados_como_perda = 0
    fora_da_lista: set[str] = set()
    for l in leads:
        if not l.perdido_em or l.vendido():
            continue
        categoria, momento = classificar_perda(l, playbook)
        if categoria == "duplicado":
            duplicados_como_perda += 1
            continue
        if categoria == "nao_classificado":
            fora_da_lista.add(" ".join(l.motivo_perda.lower().split()).rstrip("!. "))
        perdas_etapa[ETAPAS_FUNIL[l.indice()]][categoria] += 1
        perdas_categoria[categoria] += 1
        if categoria == "lead" and momento == "depois_da_qualificacao":
            criterio_a_revisar += 1
    perdas = {
        "por_etapa": {e: dict(c) for e, c in perdas_etapa.items()},
        "por_categoria": dict(perdas_categoria),
        "qualificados_perdidos_por_motivo_de_lead": criterio_a_revisar,
    }

    # 4. Maior vazamento: vendas que faltaram em cada passagem abaixo da referência
    convs = {x["etapa"]: x["conversao_da_anterior"] for x in etapas}
    vendidos = [l for l in leads if l.vendido()]
    com_valor = [l.valor for l in vendidos if l.valor]
    ticket = sum(com_valor) / len(com_valor) if com_valor else valor_medio_venda  # vendas sem valor não rebaixam o ticket
    vazamentos = []
    for i, etapa in enumerate(ETAPAS_FUNIL[1:], start=1):
        entraram_antes = len(alcancaram[ETAPAS_FUNIL[i - 1]])
        obs, ref = convs[etapa], referencia.get(etapa)
        if ref is None or obs is None or entraram_antes < AMOSTRA_MINIMA or obs >= ref:
            continue
        restante = 1.0
        for seguinte in ETAPAS_FUNIL[i + 1:]:
            taxa = convs[seguinte] if convs[seguinte] else referencia.get(seguinte)
            restante *= taxa or 0
        vendas_a_mais = entraram_antes * (ref - obs) * restante
        vazamentos.append({
            "etapa": etapa,
            "rotulo": playbook.rotulo(etapa),
            "lado": LADO_DA_ETAPA[etapa],
            "observado": obs,
            "referencia": ref,
            "base": entraram_antes,
            "vendas_a_mais": round(vendas_a_mais, 2),
            "valor_a_mais": round(vendas_a_mais * ticket, 2) if ticket else None,
        })
    vazamentos.sort(key=lambda v: v["vendas_a_mais"], reverse=True)

    # 5. Marketing entregou × comercial converteu
    mkt = {e: len(alcancaram[e]) for e in ETAPAS_DO_MARKETING}
    marketing = {
        "leads": mkt["lead"],
        "qualificados": mkt["lead_qualificado"],
        "agendamentos": mkt["agendamento"],
        "taxa_qualificacao": _taxa(mkt["lead_qualificado"], mkt["lead"]),
        "custo_por_qualificado": _div(investimento, sum(l.alcancou("lead_qualificado") for l in pagos)),
        "custo_por_agendamento": _div(investimento, sum(l.alcancou("agendamento") for l in pagos)),
    }
    ciclos = [(l.etapas["venda"] - l.etapas["lead"]).days for l in vendidos if "lead" in l.etapas]
    comercial = {
        "primeiro_contato_dentro_do_sla": primeiro_contato["dentro_do_sla"],
        "comparecimento": convs["comparecimento"],
        "propostas": len(alcancaram["proposta"]),
        "vendas": len(vendidos),
        "qualificado_para_venda": _taxa(len(vendidos), mkt["lead_qualificado"]),
        "conversao_sdr": _taxa(len(alcancaram["comparecimento"]), n),  # reuniões realizadas ÷ leads
        "conversao_closer": _taxa(len(vendidos), len(alcancaram["comparecimento"])),  # vendas ÷ reuniões realizadas
        "ciclo_de_vendas_mediana_dias": _mediana(ciclos),
        "perdas_atendimento": perdas_categoria.get("atendimento", 0),
        "perdas_comercial": perdas_categoria.get("comercial", 0),
    }

    # 6. Resultado: venda e valor vendido; CPL é diagnóstico.
    # Custos dividem só pelo que veio de mídia paga (o investimento só paga isso). Como parte
    # das vendas entra sem rastreio, o custo por venda é um teto e o retorno, um piso.
    vendidos_pagos = [l for l in pagos if l.vendido()]
    comparec_pagos = [l for l in pagos if l.alcancou("comparecimento")]
    valor_vendido = sum(l.valor or 0 for l in vendidos)
    valor_pago = sum(l.valor or 0 for l in vendidos_pagos)

    resultado = {
        "investimento": investimento,
        "vendas": len(vendidos),
        "valor_vendido": valor_vendido,
        "ticket_medio": round(ticket, 2) if com_valor else None,
        "vendas_de_midia_paga": len(vendidos_pagos),
        "vendas_nao_rastreadas": sum(1 for l in vendidos if canal_informado and (l.canal or NAO_RASTREADO) == NAO_RASTREADO),
        "retorno_sobre_investimento": round(valor_pago / investimento, 1) if investimento else None,  # piso
        "custo_por_comparecimento": _div(investimento, len(alcancaram["comparecimento"])),  # piso: inclui orgânicos
        "custo_por_comparecimento_de_midia_paga": _div(investimento, len(comparec_pagos)),
        "custo_por_venda": _div(investimento, len(vendidos_pagos)),  # teto
        "leads_de_midia_paga": len(pagos),
        "diagnostico_cpl": _div(investimento_captacao if investimento_captacao is not None else investimento, len(pagos)),
        "custo_por_venda_e_teto_retorno_e_piso": canal_informado,
    }

    # 7. Leads parados e base velha: ativos (nem venda nem perda) sem movimentação há mais de N dias
    agora = agora or datetime.now(timezone.utc)
    parados, base_velha = [], 0
    dias_sem_mov: dict[int, int] = {}
    for l in leads:
        if l.vendido() or l.perdido_em:
            continue
        ultima = l.ultima_movimentacao or max(l.etapas.values(), default=None)
        if not ultima or (agora - ultima) <= timedelta(days=dias_parado):
            continue
        dias_sem_mov[l.lead_id] = (agora - ultima).days
        base_velha += (agora - ultima) > timedelta(days=crm.dias_base_velha)
        parados.append({"lead_id": l.lead_id, "responsavel": l.responsavel, "etapa": playbook.rotulo(ETAPAS_FUNIL[l.indice()]),
                        "dias_parado": dias_sem_mov[l.lead_id], "sem_responsavel": not _pessoa_do_time(l.responsavel, baldes)})
    parados.sort(key=lambda p: -p["dias_parado"])

    # 8. Por pessoa do time do cliente (sem baldes do sistema), por canal, por campanha e por score
    def _agrupar(chave):
        grupos = defaultdict(list)
        for l in leads:
            grupos[chave(l)].append(l)
        return sorted(grupos.items(), key=lambda x: str(x[0]))

    por_responsavel = {}
    for nome, ls in _agrupar(lambda l: l.responsavel or "sem responsável"):
        if not _pessoa_do_time(nome, baldes):
            continue
        _, mins = _contato(ls)
        ativos = [l for l in ls if not l.vendido() and not l.perdido_em]
        parados_da_pessoa = sum(1 for l in ls if l.lead_id in dias_sem_mov)
        por_responsavel[nome] = {
            **_resumo(ls),
            "mediana_minutos_uteis_primeiro_contato": _mediana(mins),
            "dentro_do_sla": _taxa(sum(m <= sla for m in mins), len(mins)),
            "perdas_sem_motivo": sum(1 for l in ls if l.perdido_em and not l.vendido() and not l.motivo_perda),
            "parados": parados_da_pessoa,
            "carteira_parada": _taxa(parados_da_pessoa, len(ativos)),
            "gestor": nome.strip().lower() in gestores,
            "amostra_suficiente": len(ls) >= AMOSTRA_MINIMA_SDR,
        }
    time = {k: v for k, v in por_responsavel.items() if not v["gestor"] and v["leads"]}
    media_leads = sum(v["leads"] for v in time.values()) / len(time) if time else None
    for v in time.values():
        indice = v["leads"] / media_leads
        v["distribuicao"] = round(indice, 2)
        v["distribuicao_desbalanceada"] = media_leads >= DISTRIBUICAO_MEDIA_MINIMA and (
            indice >= DISTRIBUICAO_ALTA or indice <= DISTRIBUICAO_BAIXA)
    comparaveis = {k: v for k, v in time.items() if v["amostra_suficiente"]}
    if len(comparaveis) >= 2:
        dimensoes = {
            "vendas": {k: v["vendas"] for k, v in comparaveis.items()},
            "conversao": {k: v["vendas"] / v["leads"] for k, v in comparaveis.items()},
            "volume": {k: v["leads"] for k, v in comparaveis.items()},
            "primeiro_contato": {k: (-v["mediana_minutos_uteis_primeiro_contato"]
                                     if v["mediana_minutos_uteis_primeiro_contato"] is not None else None)
                                 for k, v in comparaveis.items()},
            "movimentacao": {k: sum(l.alcancou("em_atendimento") for l in leads if l.responsavel == k) / v["leads"]
                             for k, v in comparaveis.items()},
            "consistencia": {k: -v["parados"] / v["leads"] for k, v in comparaveis.items()},
        }
        notas = {d: _notas_relativas(vals) for d, vals in dimensoes.items()}
        for k, v in comparaveis.items():
            v["perfil"] = round(sum(notas[d][k] * PESOS_PERFIL[d] for d in PESOS_PERFIL) / sum(PESOS_PERFIL.values()))
            v["notas_perfil"] = {d: round(notas[d][k]) for d in PESOS_PERFIL}

    por_closer = {}
    for nome, ls in _agrupar(lambda l: l.closer):
        if not _pessoa_do_time(nome, baldes):
            continue
        comp = [l for l in ls if l.alcancou("comparecimento")]
        vend = [l for l in ls if l.vendido()]
        por_closer[nome] = {
            "comparecimentos": len(comp),
            "propostas": sum(l.alcancou("proposta") for l in ls),
            "vendas": len(vend),
            "valor_vendido": sum(l.valor or 0 for l in vend),
            "comparecimento_para_venda": _taxa(len(vend), len(comp)),
            "amostra_suficiente": len(comp) >= AMOSTRA_MINIMA_CLOSER,
        }
    por_canal = {nome: _resumo(ls) for nome, ls in _agrupar(lambda l: l.canal or NAO_RASTREADO)} if canal_informado else {}
    por_campanha = {nome: _resumo(ls) for nome, ls in _agrupar(lambda l: l.campanha or "sem campanha")}
    por_score = {nome: _resumo(ls) for nome, ls in _agrupar(lambda l: l.score or "sem score")} if any(l.score for l in leads) else {}

    # 9. Chegada dos leads por dia da semana e hora (horário do cliente): base do plantão e do prazo de contato
    entradas = [_local(l.etapas["lead"], horario) for l in leads if "lead" in l.etapas]
    mapa = [[0] * 24 for _ in range(7)]
    for d in entradas:
        mapa[d.weekday()][d.hour] += 1
    pico = max(((dia, hora) for dia in range(7) for hora in range(24)), key=lambda x: mapa[x[0]][x[1]]) if entradas else None
    chegada = {
        "mapa_semana_hora": mapa,  # [segunda..domingo][0..23h]
        "fora_do_horario_comercial": _taxa(len(fora_horario), len(entradas)),
        "noite": _taxa(sum(not horario.inicio <= d.hour < horario.fim for d in entradas), len(entradas)),
        "fim_de_semana": _taxa(sum(d.weekday() >= 5 for d in entradas), len(entradas)),
        "pico": {"dia_da_semana": pico[0], "hora": pico[1]} if pico else None,
    }

    # 10. Pré-atendimento, resgate e reativação
    com_bot = [l for l in leads if l.bot]
    nao_qualificados = [l for l in leads if not l.alcancou("lead_qualificado") and l.interagiu is not None]
    pre_atendimento = {
        "bot_concluido": _taxa(sum(l.bot == "concluido" for l in com_bot), len(com_bot)),
        "bot_incompleto": _taxa(sum(l.bot == "incompleto" for l in com_bot), len(com_bot)),
        "bot_nao_iniciado": _taxa(sum(l.bot == "nao_iniciado" for l in com_bot), len(com_bot)),
        "qualificacao_por_estado_do_bot": {
            e: _taxa(sum(l.alcancou("lead_qualificado") for l in com_bot if l.bot == e), sum(l.bot == e for l in com_bot))
            for e in ("concluido", "incompleto", "nao_iniciado")
        } if com_bot else {},
        "nao_qualificados_que_interagiram": _taxa(sum(bool(l.interagiu) for l in nao_qualificados), len(nao_qualificados)),
    }
    reativados = [l for l in leads if l.reativado]
    reativacao = {
        "reativados": len(reativados),
        "chegaram_a_agendamento": sum(l.alcancou("agendamento") for l in reativados),
        "vendas": sum(l.vendido() for l in reativados),
        "valor_vendido": sum(l.valor or 0 for l in reativados if l.vendido()),
    }

    # 11. Qualidade dos dados e sinais (regras fixas que registram fato e número; a leitura e a ação são do assessor)
    perdidos = [l for l in leads if l.perdido_em and not l.vendido()]
    qualidade = {
        "leads_duplicados_removidos": leads_duplicados,
        "vendas_duplicadas_removidas": vendas_duplicadas,
        "perdas_marcadas_como_lead_duplicado": duplicados_como_perda,
        "vendas_sem_valor": len(vendidos) - len(com_valor),
        "perdas_sem_motivo": _taxa(perdas_categoria.get("sem_motivo", 0), len(perdidos)),
        "perdas_com_motivo_fora_da_lista": _taxa(perdas_categoria.get("nao_classificado", 0), len(perdidos)),
        "motivos_distintos_fora_da_lista": len(fora_da_lista),
        "leads_nao_rastreados": _taxa(sum((l.canal or NAO_RASTREADO) == NAO_RASTREADO for l in leads), n) if canal_informado else None,
        "leads_sem_responsavel": _taxa(sum(not _pessoa_do_time(l.responsavel, baldes) for l in leads), n),
    }
    sinais = []
    perdidos_antes = [l for l in perdidos if not l.alcancou("lead_qualificado")]
    atendimento_antes = sum(classificar_perda(l, playbook)[0] == "atendimento" for l in perdidos_antes)
    if perdidos_antes and atendimento_antes / len(perdidos_antes) > 0.30:
        sinais.append(f"{atendimento_antes / len(perdidos_antes):.0%} das perdas antes da qualificação são de atendimento "
                      "(não respondeu, demora): resgatar a base antes de aumentar volume e revisar o tempo de primeiro contato")
    if (qualidade["perdas_sem_motivo"] or 0) > 0.20:
        sinais.append("mais de 20% das perdas sem motivo: tornar o motivo obrigatório no Kommo")
    if qualidade["motivos_distintos_fora_da_lista"] >= 8:
        sinais.append(f"{qualidade['motivos_distintos_fora_da_lista']} motivos de perda diferentes fora da lista padrão: "
                      "a lista de motivos não está padronizada")
    if (qualidade["leads_nao_rastreados"] or 0) > 0.20:
        sinais.append("mais de 20% dos leads sem canal: revisar UTMs e campo de origem")
    if (qualidade["leads_sem_responsavel"] or 0) > 0.20:
        sinais.append("mais de 20% dos leads sem responsável")
    if qualidade["vendas_sem_valor"]:
        sinais.append(f"{qualidade['vendas_sem_valor']} venda(s) sem valor no Kommo: o valor vendido e o retorno ficam subestimados")
    if criterio_a_revisar:
        sinais.append(f"{criterio_a_revisar} qualificados perdidos por motivo de lead: revisar o critério de qualificação")
    if parados:
        sinais.append(f"{len(parados)} leads ativos parados há mais de {dias_parado} dias")
    if base_velha >= 10:
        sinais.append(f"{base_velha} leads ativos sem movimentação há mais de {crm.dias_base_velha} dias (base velha)")
    ativos = [l for l in leads if not l.vendido() and not l.perdido_em]
    if len(ativos) >= AMOSTRA_MINIMA:
        etapa_cheia, qtd = Counter(ETAPAS_FUNIL[l.indice()] for l in ativos).most_common(1)[0]
        if qtd / len(ativos) >= 0.40:
            sinais.append(f"{qtd / len(ativos):.0%} dos leads ativos estão em {playbook.rotulo(etapa_cheia)}")
    if len(entradas) >= AMOSTRA_MINIMA and (chegada["fora_do_horario_comercial"] or 0) >= 0.40:
        sinais.append(f"{chegada['fora_do_horario_comercial']:.0%} dos leads chegam fora do horário comercial")
    for nome, v in time.items():
        if v["leads"] >= 10 and v["qualificados"] == 0:
            sinais.append(f"{nome}: {v['leads']} leads e nenhum qualificado")
        if v.get("distribuicao_desbalanceada"):
            sinais.append(f"{nome} recebeu {v['distribuicao']:.1f}× a média de leads do time")
    taxas_q = {k: v["qualificados"] / v["leads"] for k, v in comparaveis.items()}
    if len(taxas_q) >= 2:
        media_q = sum(taxas_q.values()) / len(taxas_q)
        for nome, t in taxas_q.items():
            if 0 < t < media_q / 2:
                sinais.append(f"{nome}: qualificação de {t:.0%}, menos da metade da média do time ({media_q:.0%})")

    return {
        "leads": n,
        "etapas": etapas,
        "primeiro_contato": primeiro_contato,
        "cadencia": cadencia,
        "perdas": perdas,
        "maior_vazamento": vazamentos[0] if vazamentos else None,
        "vazamentos": vazamentos,
        "marketing_entregou": marketing,
        "comercial_converteu": comercial,
        "resultado": resultado,
        "por_responsavel": por_responsavel,
        "por_closer": por_closer,
        "por_canal": por_canal,
        "por_campanha": por_campanha,
        "por_score": por_score,
        "chegada": chegada,
        "parados": parados,
        "pre_atendimento": pre_atendimento,
        "reativacao": reativacao,
        "qualidade_dos_dados": qualidade,
        "sinais": sinais,
    }
