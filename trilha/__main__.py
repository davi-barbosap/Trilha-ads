"""CLI do Trilha: validar · calcular · raio-x · simular-webhook · servir."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date

from pathlib import Path

from pydantic import ValidationError

from trilha.core.economia import calcular
from trilha.core.oferta import carregar_oferta
from trilha.core.perfil import ETAPAS_FUNIL, avisos_legado, carregar_perfil


def _brl(v: float | None) -> str:
    if v is None:
        return "—"
    casas = 2 if abs(v) < 1000 else 0
    return "R$ " + f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(v: float | None) -> str:
    return "—" if v is None else f"{v:g}".replace(".", ",")


def cmd_validar(args) -> int:
    perfil = carregar_perfil(args.perfil)
    print(f"OK — perfil de '{perfil.cliente.nome}' (versão {perfil.versao}, vigente desde {perfil.vigente_desde})")
    for aviso in avisos_legado(args.perfil):
        print(f"Atenção: {aviso}")
    pasta = Path(args.perfil).resolve().parent.name
    if pasta != perfil.cliente.id:
        print(f"Atenção: cliente.id '{perfil.cliente.id}' difere da pasta '{pasta}' — a trilha-api vai recusar este perfil")
    if perfil.economia.estimados:
        print("Atenção: usando padrões do playbook (estimados) para: " + ", ".join(perfil.economia.estimados))
    if perfil.operacao is None:
        print("Atenção: sem bloco operacao — dossiê, relatório semanal e pacote da reunião não serão agendados")
    print(f"Freio de emergência: {perfil.freio.modo} (gasto sem lead ≥ {perfil.freio.gasto_sem_lead_multiplo:g}× CPL máximo"
          f" ou {perfil.freio.horas_rastreamento_quebrado:g}h sem evento de conversão)")
    if perfil.crm and not perfil.crm.mapa_eventos:
        print("Atenção: crm.mapa_eventos vazio — só as etapas de sistema (142 venda, 143 perdida) serão mapeadas")
    elif perfil.crm:
        mapeadas = {m.evento for m in perfil.crm.mapa_completo()}
        faltando = [e for e in ETAPAS_FUNIL if e not in mapeadas]
        if faltando:
            print("Atenção: etapas do funil sem etapa do Kommo (o raio-x fica incompleto): " + ", ".join(faltando))
    if perfil.crm:
        from trilha.core.playbook import carregar_playbook

        lista = carregar_playbook(perfil.cliente.segmento).motivos_perda
        for m in perfil.crm.mapa_eventos:
            if m.motivo and m.motivo not in lista:
                print(f"Atenção: motivo '{m.motivo}' (etapa {m.status_id}) não está na lista de motivos do playbook")
        if any(f.papel == "nutricao" and f.ganho_significa is None for f in perfil.crm.funis):
            print("Atenção: funil de nutrição sem ganho_significa — o ganho (142) dele não gera evento")
    correcoes = Path(args.perfil).resolve().parent / "correcoes.yaml"
    if correcoes.is_file():
        from trilha.core.correcoes import carregar_correcoes

        c = carregar_correcoes(correcoes)
        print(f"Correções confirmadas: {len(c.excluir)} exclusão(ões), {len(c.data_da_venda)} data(s) de venda corrigida(s)")
    for arquivo in sorted((Path(args.perfil).resolve().parent / "ofertas").glob("*.yaml")):
        oferta = carregar_oferta(arquivo)
        print(f"Oferta '{oferta.oferta.nome}': OK")
        if pendencias := oferta.aderencia.pendencias():
            print("  Diagnóstico de aderência pendente: " + ", ".join(pendencias))
        for sinal in oferta.aderencia.sinais_de_risco():
            print(f"  Sinal de risco: {sinal}")
    return 0


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{v * 100:.1f}%".replace(".", ",")


def cmd_raio_x(args) -> int:
    from trilha.core.correcoes import aplicar_correcoes, carregar_correcoes
    from trilha.core.funil import LeadFunil, raio_x
    from trilha.core.playbook import carregar_playbook

    perfil = carregar_perfil(args.perfil)
    with open(args.leads, encoding="utf-8") as f:
        leads = [LeadFunil.model_validate(x) for x in json.load(f)]
    leads = aplicar_correcoes(leads, carregar_correcoes(Path(args.perfil).parent / "correcoes.yaml"))
    gasto = None
    if args.gasto_por_codigo:
        with open(args.gasto_por_codigo, encoding="utf-8") as f:
            gasto = {str(k): float(v) for k, v in json.load(f).items()}
    playbook = carregar_playbook(perfil.cliente.segmento)
    r = raio_x(leads, playbook, args.investimento, crm=perfil.crm, gasto_por_codigo=gasto)
    if args.retorno:
        from trilha.core.retorno import gravar_retorno, montar_retorno
        destino = gravar_retorno(montar_retorno(r, leads, perfil, playbook, args.inicio, args.fim), args.retorno)
        print(f"✓ retorno para o briefing e a copy: {destino}")
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return 0
    res = r["resultado"]
    print(f"Cliente: {perfil.cliente.nome} · {r['leads']} leads")
    print(f"\nResultado: {res['vendas']} vendas · {_brl(res['valor_vendido'])} vendidos"
          + (f" · retorno de {_num(res['retorno_sobre_investimento'])}× o investimento" if res["retorno_sobre_investimento"] else ""))
    print(f"  custo por {r['etapas'][4]['rotulo'].lower()}: {_brl(res['custo_por_comparecimento'])} · custo por venda: {_brl(res['custo_por_venda'])}"
          f" · CPL (diagnóstico): {_brl(res['diagnostico_cpl'])}")
    print("\nFunil etapa por etapa:")
    for e in r["etapas"]:
        ref = f" (referência {_pct(e['referencia'])})" if e["referencia"] else ""
        tempo = f" · mediana {_num(e['mediana_horas_desde_anterior'])} h desde a anterior" if e["mediana_horas_desde_anterior"] is not None else ""
        conv = f" · {_pct(e['conversao_da_anterior'])} da anterior{ref}" if e["conversao_da_anterior"] is not None else ""
        print(f"  {e['rotulo']:<18} {e['entraram']:>5}{conv}{tempo}")
    pc = r["primeiro_contato"]
    print(f"\nPrimeiro contato: mediana {_num(pc['mediana_minutos_uteis'])} min úteis ({_num(pc['mediana_minutos_corridos'])} corridos)"
          f" · {_pct(pc['dentro_do_sla'])} dentro de {pc['sla_minutos']:g} min úteis · {pc['sem_primeiro_contato']} leads sem primeiro contato")
    cad = r["cadencia"]
    print(f"Cadência: perdidos antes de qualificar tiveram mediana de {_num(cad['mediana_tentativas_perdidos_antes_de_qualificar'])} tentativa(s);"
          f" qualificados, {_num(cad['mediana_tentativas_qualificados'])}")
    if v := r["maior_vazamento"]:
        print(f"\nMaior vazamento: {v['rotulo']} ({v['lado']}) — {_pct(v['observado'])} contra {_pct(v['referencia'])} de referência"
              f" ≈ {_num(v['vendas_a_mais'])} venda(s) a menos" + (f", {_brl(v['valor_a_mais'])}" if v["valor_a_mais"] else ""))
    m, c = r["marketing_entregou"], r["comercial_converteu"]
    print(f"\nMarketing entregou: {m['leads']} leads · {m['qualificados']} qualificados · {m['agendamentos']} agendamentos"
          f" · {_brl(m['custo_por_qualificado'])} por qualificado")
    print(f"Comercial converteu: {_pct(c['primeiro_contato_dentro_do_sla'])} no prazo de primeiro contato · {_pct(c['comparecimento'])} de comparecimento"
          f" · {c['vendas']} vendas · {_pct(c['qualificado_para_venda'])} dos qualificados viraram venda")
    p = r["perdas"]
    print("\nPerdas por categoria: " + " · ".join(f"{k}: {v}" for k, v in sorted(p["por_categoria"].items(), key=lambda x: -x[1])))
    if p["qualificados_perdidos_por_motivo_de_lead"]:
        print(f"  {p['qualificados_perdidos_por_motivo_de_lead']} leads qualificados foram perdidos por motivo de lead: critério de qualificação a revisar")
    if r["sinais"]:
        print("\nSinais:")
        for sinal in r["sinais"]:
            print(f"  • {sinal}")
    q = r["qualidade_dos_dados"]
    if q["leads_duplicados_removidos"] or q["vendas_duplicadas_removidas"]:
        print(f"\nDeduplicação: {q['leads_duplicados_removidos']} lead(s) e {q['vendas_duplicadas_removidas']} venda(s) repetidos removidos")
    if res["custo_por_venda_e_teto_retorno_e_piso"]:
        print(f"Custos sobre {res['leads_de_midia_paga']} leads de mídia paga; {res['vendas_nao_rastreadas']} venda(s) sem rastreio:"
              " custo por venda é teto e retorno é piso")
    print("\nPor responsável:")
    for nome, d in r["por_responsavel"].items():
        print(f"  {nome:<14} {d['leads']:>4} leads · primeiro contato {_num(d['mediana_minutos_uteis_primeiro_contato'])} min úteis ({_pct(d['dentro_do_sla'])} no prazo)"
              f" · {d['vendas']} vendas")
        if "perfil" in d:
            print(f"                 perfil {d['perfil']} (100 = melhor do time no período)")
        elif not d["amostra_suficiente"]:
            print("                 (amostra pequena para comparar)")
    if r["por_criativo"]:
        print("\nPor criativo (código da célula):")
        for nome, d in r["por_criativo"].items():
            custos = (f" · gasto {_brl(d['gasto'])} · CPL {_brl(d['cpl'])} · {_brl(d['custo_por_qualificado'])} por qualificado"
                      f" · {_brl(d['custo_por_venda'])} por venda") if "gasto" in d else ""
            print(f"  {nome:<12} {d['leads']:>4} leads · {d['qualificados']} qualificados ({_pct(d['taxa_qualificacao'])})"
                  f" · {d['vendas']} venda{'' if d['vendas'] == 1 else 's'}{custos}")
    if r["por_closer"]:
        print("\nPor closer:")
        for nome, d in r["por_closer"].items():
            print(f"  {nome:<14} {d['comparecimentos']:>4} comparecimentos · {d['propostas']} propostas · {d['vendas']} vendas"
                  f" ({_pct(d['comparecimento_para_venda'])})")
    return 0


def cmd_calcular(args) -> int:
    perfil = carregar_perfil(args.perfil)
    verba = args.verba or perfil.verba.mensal_planejada
    r = calcular(perfil.economia, verba, perfil.conversao.eventos_semana_aprendizado)
    print(f"Cliente: {perfil.cliente.nome} · modelo de receita: {perfil.economia.modelo_receita}")
    print(f"Receita bruta por venda ....... {_brl(r.receita_bruta)}")
    print(f"CAC máximo .................... {_brl(r.cac_max)}")
    print(f"CPL máximo .................... {_brl(r.cpl_max)}")
    print(f"CPL qualificado máximo ........ {_brl(r.cpl_qualificado_max)}")
    print(f"Custo máximo por agendamento .. {_brl(r.custo_agendamento_max)}")
    print(f"\nVerba mensal para sair do aprendizado ({perfil.conversao.eventos_semana_aprendizado} eventos/semana, 1 conjunto):")
    for degrau, v in r.verba_por_degrau.items():
        marca = "✓" if degrau in r.degraus_viaveis else "✗"
        print(f"  {marca} {degrau:<17} {_brl(v)}")
    print(f"\nVerba planejada: {_brl(verba)} · verba mínima viável: {_brl(r.verba_minima_viavel)}")
    if verba < r.verba_minima_viavel:
        print("→ Abaixo da mínima: concentrar em uma plataforma, uma oferta e uma campanha; leitura de resultado será lenta.")
    elif "lead_qualificado" not in r.degraus_viaveis:
        print("→ Otimizar por lead qualificado é inviável com esta verba: otimizar por lead com atrito qualificador e")
        print("  enviar os eventos de qualidade mesmo assim (núcleo §7.2).")
    if r.estimados:
        print("Estimados (padrão do playbook): " + ", ".join(r.estimados))
    return 0


def cmd_simular_webhook(args) -> int:
    from trilha.conversao.pipeline import executar, processar
    from trilha.integracoes.kommo import extrair_dados_lead

    perfil = carregar_perfil(args.perfil)
    with open(args.webhook, encoding="utf-8") as f:
        corpo = f.read().strip()
    with open(args.lead, encoding="utf-8") as f:
        lead = json.load(f)
    contatos = []
    for caminho in args.contato or []:
        with open(caminho, encoding="utf-8") as f:
            contatos.append(json.load(f))
    dados = extrair_dados_lead(lead, contatos, perfil.crm.campos)
    envios = executar(processar(corpo, perfil, lambda _id: dados), simular=True)
    print(json.dumps([asdict(e) for e in envios], ensure_ascii=False, indent=2))
    return 0


def cmd_servir(args) -> int:
    from trilha.api import servir

    servir(args.host, args.porta)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="trilha", description=__doc__)
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("validar", help="valida um perfil.yaml")
    s.add_argument("perfil")
    s.set_defaults(func=cmd_validar)

    s = sub.add_parser("calcular", help="calculadora de economia unitária e verba por degrau")
    s.add_argument("perfil")
    s.add_argument("--verba", type=float, help="verba mensal (padrão: a do perfil)")
    s.set_defaults(func=cmd_calcular)

    s = sub.add_parser("raio-x", help="raio-x do funil etapa por etapa a partir do histórico de leads")
    s.add_argument("leads", help="JSON com o histórico dos leads do período")
    s.add_argument("--perfil", required=True)
    s.add_argument("--investimento", type=float, help="investimento em mídia no período")
    s.add_argument("--gasto-por-codigo", help='JSON com o gasto de cada código de criativo: {"PT01": 1200}')
    s.add_argument("--json", action="store_true", help="saída completa em JSON")
    s.add_argument("--retorno", metavar="PASTA", help="grava o retorno do período para o briefing (ads/<id>/retornos)")
    s.add_argument("--inicio", type=date.fromisoformat, help="início do período (padrão: o primeiro lead)")
    s.add_argument("--fim", type=date.fromisoformat, help="fim do período (padrão: o último lead)")
    s.set_defaults(func=cmd_raio_x)

    s = sub.add_parser("simular-webhook", help="mostra o que um webhook do Kommo enviaria ao Meta e ao Google")
    s.add_argument("webhook", help="arquivo com o corpo form-urlencoded do webhook")
    s.add_argument("--perfil", required=True)
    s.add_argument("--lead", required=True, help="JSON do lead (API v4)")
    s.add_argument("--contato", action="append", help="JSON de contato (API v4); pode repetir")
    s.set_defaults(func=cmd_simular_webhook)

    s = sub.add_parser("servir", help="sobe a trilha-api (HTTP) usada pelos fluxos do n8n")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--porta", type=int, default=8080)
    s.set_defaults(func=cmd_servir)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except ValidationError as e:
        print(f"Perfil inválido:\n{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
