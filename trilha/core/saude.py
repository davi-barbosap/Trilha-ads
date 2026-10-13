"""Saúde das contas de anúncio (portado do painel de saúde da carteira).

Contas pré-pagas param de entregar quando o saldo acaba, sem que a campanha tenha
qualquer problema. O sistema projeta quantos dias de saldo restam pela queima dos
últimos 7 dias e sugere a recarga para 30 dias. P1 = resolver hoje; P2 = esta semana.

Alertas de conta (saldo, status, anúncios com problema) vão para o assessor do cliente.
Alertas técnicos (credencial recusada, conta que sumiu do acesso, gasto ilegível) vão para
o responsável técnico. Credencial recusada é um alerta só, nunca um "conta não encontrada"
por cliente: o painel agrupa alertas pela `chave`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# account_status da Graph API do Meta (201 e 202 são agregados usados em filtros)
STATUS_CONTA_META = {
    1: "ativa",
    2: "desativada",
    3: "com pagamento pendente",
    7: "em análise de risco",
    8: "com acerto de pagamento pendente",
    9: "em período de carência",
    100: "com encerramento pendente",
    101: "encerrada",
    201: "ativa",
    202: "encerrada",
}
STATUS_ATIVOS = {1, 201}
STATUS_DE_PAGAMENTO = {3, 8, 9}
DIAS_CRITICO = 5
DIAS_ATENCAO = 10


class ContaAnuncio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str
    id: str | None = None  # act_… no Meta, customer_id no Google
    plataforma: str = "meta"
    status: int = 1
    # Saldo pré-pago (Meta: is_prepay_account e funding_source_details.display_string "R$ 1.234,56").
    # None = conta pós-paga ou saldo ilegível; o campo `balance` do Meta é valor devido, não saldo.
    saldo: float | None = Field(default=None, ge=0)
    gasto_7d: float | None = Field(default=0, ge=0)  # None = a leitura falhou
    anuncios_com_problema: int = Field(default=0, ge=0)  # effective_status WITH_ISSUES nos anúncios ativos
    anuncios_reprovados: int = Field(default=0, ge=0)  # effective_status DISAPPROVED


def _alerta(nivel, titulo, acao, responsavel, chave):
    return {"nivel": nivel, "titulo": titulo, "acao": acao, "responsavel": responsavel, "chave": chave}


def avaliar_conta(conta: ContaAnuncio, responsavel: str, responsavel_tecnico: str = "responsável técnico") -> dict:
    queima = conta.gasto_7d / 7 if conta.gasto_7d else None
    dias = int(conta.saldo / queima) if conta.saldo is not None and queima else None
    recarga = round(queima * 30, 2) if queima else None
    alertas = []
    chave = conta.id or conta.nome

    def alerta(nivel, titulo, acao, quem=responsavel, tipo="conta"):
        alertas.append(_alerta(nivel, f"{conta.nome}: {titulo}", acao, quem, f"{tipo}:{chave}"))

    if conta.status not in STATUS_ATIVOS:
        rotulo = STATUS_CONTA_META.get(conta.status, f"status {conta.status}")
        acao = ("Regularizar o pagamento no Gerenciador de Negócios hoje." if conta.status in STATUS_DE_PAGAMENTO
                else "Investigar no Gerenciador de Negócios (limite de gasto, revisão ou suspensão) hoje.")
        alerta("P1", f"conta {rotulo}", acao)
    elif conta.saldo == 0:
        alerta("P1", "saldo zerado — entrega parada",
               f"Recarga urgente{f' (~R$ {recarga:,.0f} para 30 dias)' if recarga else ''}.".replace(",", "."))
    elif dias is not None and dias < DIAS_CRITICO:
        alerta("P1", f"saldo para {dias} dia(s)", f"Recarga esta semana: ~R$ {recarga:,.0f} para 30 dias.".replace(",", "."))
    elif dias is not None and dias < DIAS_ATENCAO:
        alerta("P2", f"saldo para ~{dias} dias", f"Avisar o cliente sobre a recarga: ~R$ {recarga:,.0f} para 30 dias.".replace(",", "."))
    if conta.anuncios_reprovados:
        alerta("P2", f"{conta.anuncios_reprovados} anúncio(s) reprovado(s)", "Ver o motivo da reprovação e corrigir.", tipo="anuncios")
    if conta.anuncios_com_problema:
        alerta("P2", f"{conta.anuncios_com_problema} anúncio(s) com problema de entrega",
               "Ver o aviso de cada anúncio no Gerenciador.", tipo="anuncios")
    if conta.gasto_7d is None:
        alerta("P2", "gasto dos últimos 7 dias ilegível", "Conferir a coleta: sem o gasto, os dias de saldo não são calculados.",
               responsavel_tecnico, "coleta")
    return {
        "conta": conta.nome,
        "status": STATUS_CONTA_META.get(conta.status, str(conta.status)),
        "queima_diaria": round(queima, 2) if queima else None,
        "dias_de_saldo": dias,
        "recarga_30_dias": recarga,
        "alertas": alertas,
    }


def saude_do_cliente(
    contas: list[ContaAnuncio],
    responsavel: str,
    responsavel_tecnico: str = "responsável técnico",
    contas_esperadas: list[str] | None = None,
    credencial_ok: bool = True,
    plataforma: str = "meta",
) -> dict:
    """Semáforo do cliente. Com a credencial recusada não há dado: o resultado é "sem dado", não verde."""
    if not credencial_ok:
        alerta = _alerta("P1", f"credencial do {plataforma.capitalize()} recusada — nenhuma conta lida",
                         "Renovar o token e conferir o acesso no Gerenciador de Negócios.", responsavel_tecnico,
                         f"credencial:{plataforma}")
        return {"saude": "sem_dado", "contas": [], "alertas": [alerta]}
    avaliadas = [avaliar_conta(c, responsavel, responsavel_tecnico) for c in contas]
    alertas = [a for c in avaliadas for a in c["alertas"]]
    lidas = {c.id for c in contas if c.id}
    for conta_id in contas_esperadas or []:
        if conta_id not in lidas:
            alertas.append(_alerta("P2", f"conta {conta_id} não encontrada no acesso",
                                   "Conferir se a conta continua compartilhada com o Gerenciador da Trilha.",
                                   responsavel_tecnico, f"acesso:{conta_id}"))
    cor = "vermelho" if any(a["nivel"] == "P1" for a in alertas) else "amarelo" if alertas else "verde"
    return {"saude": cor, "contas": avaliadas, "alertas": alertas}
