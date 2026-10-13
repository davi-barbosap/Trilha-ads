"""Raio-x por criativo: o código da célula da grade (Trilha-briefing) que chega ao lead no utm_content."""

import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from trilha.__main__ import main
from trilha.api import TrilhaApi
from trilha.core.atribuicao import SEM_CODIGO, codigo_criativo, limpar_utm
from trilha.core.funil import LeadFunil, raio_x
from trilha.core.perfil import Crm
from trilha.core.playbook import carregar_playbook

T0 = datetime(2026, 9, 1, 9, tzinfo=timezone.utc)
PB = carregar_playbook("padrao")
RAIZ = Path(__file__).resolve().parents[1]
FIX = RAIZ / "tests" / "fixtures"
PERFIL = RAIZ / "tests" / "fixtures" / "clientes" / "_exemplo" / "perfil.yaml"


def lead(i, criativo=None, qualificado=False, venda=False, canal="Meta Ads"):
    etapas = {"lead": T0}
    if qualificado or venda:
        etapas["lead_qualificado"] = T0
    if venda:
        etapas["venda"] = T0
    return LeadFunil(lead_id=i, etapas=etapas, criativo=criativo, canal=canal, pessoa=f"p{i}", valor=1000.0 if venda else None)


class TestCodigo(unittest.TestCase):
    def test_regua_das_utms(self):
        self.assertEqual(limpar_utm("PT01+%7C+Ana".replace("%7C", "|")), "PT01 | Ana")
        for vazio in (None, "", "—", "{{ad.name}}", "(not set)"):
            self.assertIsNone(limpar_utm(vazio), vazio)

    def test_codigo_antes_da_barra_e_no_padrao(self):
        casos = {"PT01": "PT01", "VD01 | Ana": "VD01", "GB01+|+busca": "GB01", "{{ad.name}}": None, "v0": None,
                 "pt01": None, "PT01-v2": None, None: None}
        for entrada, esperado in casos.items():
            self.assertEqual(codigo_criativo(entrada), esperado, entrada)
        self.assertEqual(codigo_criativo("v3", r"v[0-9]+"), "v3")

    def test_padrao_do_cliente_precisa_ser_valido(self):
        self.assertEqual(Crm(subdominio="x").padrao_codigo, "[A-Z0-9]{2,8}")
        with self.assertRaises(ValidationError):
            Crm(subdominio="x", padrao_codigo="[A-Z")


class TestRaioXPorCriativo(unittest.TestCase):
    def setUp(self):
        self.leads = [lead(1, "PT01", venda=True), lead(2, "PT01", qualificado=True), lead(3, "PT01"),
                      lead(4, "PT02 | v2"), lead(5, "PT02"), lead(6, "{{ad.name}}"), lead(7, None)]

    def test_volumes_e_taxas_por_codigo(self):
        r = raio_x(self.leads, PB)
        c = r["por_criativo"]
        self.assertEqual(list(c), ["PT01", "PT02", SEM_CODIGO])  # sem código por último
        self.assertEqual((c["PT01"]["leads"], c["PT01"]["qualificados"], c["PT01"]["vendas"]), (3, 2, 1))
        self.assertAlmostEqual(c["PT01"]["taxa_qualificacao"], 0.6667)
        self.assertEqual(c["PT02"]["leads"], 2)
        self.assertEqual(c[SEM_CODIGO]["leads"], 2)
        self.assertNotIn("gasto", c["PT01"])

    def test_custos_com_gasto_e_codigo_que_gastou_sem_trazer_ninguem(self):
        c = raio_x(self.leads, PB, gasto_por_codigo={"PT01": 300.0, "PT03": 150.0})["por_criativo"]
        self.assertEqual((c["PT01"]["cpl"], c["PT01"]["custo_por_qualificado"], c["PT01"]["custo_por_venda"]), (100.0, 150.0, 300.0))
        self.assertEqual((c["PT03"]["leads"], c["PT03"]["gasto"], c["PT03"]["cpl"]), (0, 150.0, None))
        self.assertNotIn("gasto", c["PT02"])

    def test_sinal_quando_falta_codigo(self):
        r = raio_x(self.leads, PB)
        self.assertAlmostEqual(r["qualidade_dos_dados"]["leads_pagos_sem_codigo_criativo"], 2 / 7, places=3)
        self.assertTrue(any("sem código de criativo" in s for s in r["sinais"]))
        r = raio_x(self.leads[:5], PB)
        self.assertFalse(any("sem código de criativo" in s for s in r["sinais"]))

    def test_sem_utm_content_nao_mostra_o_bloco(self):
        self.assertEqual(raio_x([lead(1), lead(2)], PB)["por_criativo"], {})

    def test_padrao_do_cliente(self):
        crm = Crm(subdominio="x", padrao_codigo=r"v[0-9]+")
        c = raio_x([lead(1, "v0"), lead(2, "v1 | Ana"), lead(3, "PT01")], PB, crm=crm)["por_criativo"]
        self.assertEqual(list(c), ["v0", "v1", SEM_CODIGO])


class TestRetorno(unittest.TestCase):
    """O que volta para o briefing: resultado por código e motivos de perda (contrato retorno)."""

    def test_monta_por_codigo_e_motivos(self):
        from datetime import date

        from trilha.core.perfil import carregar_perfil
        from trilha.core.retorno import VERSAO_RETORNO, montar_retorno
        perdidos = [lead(i, "PT02") for i in (8, 9, 10)]
        motivos = ["Fora do perfil financeiro", "Fora do perfil financeiro", "Não respondeu às tentativas de contato"]
        for l, m in zip(perdidos, motivos):
            l.perdido_em, l.motivo_perda = T0, m
        leads = [lead(1, "PT01", venda=True), lead(2, "PT01", qualificado=True), *perdidos]
        r = raio_x(leads, PB, gasto_por_codigo={"PT01": 200.0, "PT02": 300.0})
        ret = montar_retorno(r, leads, carregar_perfil(PERFIL), PB, fim=date(2026, 9, 30))
        self.assertEqual(ret["retorno"], VERSAO_RETORNO)
        self.assertEqual(ret["periodo"], {"inicio": date(2026, 9, 1), "fim": date(2026, 9, 30)})
        self.assertEqual((ret["por_codigo"]["PT01"]["vendas"], ret["por_codigo"]["PT01"]["cpl"]), (1, 100.0))
        self.assertIn("agendamentos", ret["por_codigo"]["PT02"])
        self.assertEqual(ret["motivos_perda"][0], {"motivo": "Fora do perfil financeiro", "categoria": "lead", "leads": 2})
        self.assertEqual(ret["motivos_perda"][1]["categoria"], "atendimento")

    def test_cli_grava_o_retorno(self):
        import yaml
        with tempfile.TemporaryDirectory() as tmp:
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                rc = main(["raio-x", str(FIX / "funil_leads.json"), "--perfil", str(PERFIL), "--retorno", tmp])
            self.assertEqual(rc, 0)
            [arquivo] = list(Path(tmp).glob("*.yaml"))
            dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
        self.assertIn("✓ retorno para o briefing", saida.getvalue())
        self.assertEqual(dados["cliente"], "_exemplo")
        self.assertIn("v0", dados["por_codigo"])
        self.assertTrue(dados["motivos_perda"])


class TestCliEApi(unittest.TestCase):
    def test_cli_com_gasto_por_codigo(self):
        with tempfile.TemporaryDirectory() as tmp:
            gasto = Path(tmp) / "gasto.json"
            gasto.write_text(json.dumps({"v0": 1800, "v1": 2100}), encoding="utf-8")
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                rc = main(["raio-x", str(FIX / "funil_leads.json"), "--perfil", str(PERFIL), "--investimento", "7550",
                           "--gasto-por-codigo", str(gasto)])
        self.assertEqual(rc, 0)
        texto = saida.getvalue()
        self.assertIn("Por criativo (código da célula):", texto)
        self.assertIn("v0            107 leads · 30 qualificados (28,0%) · 1 venda · gasto R$ 1.800", texto)

    def test_api_aceita_gasto_por_codigo_e_recusa_formato_errado(self):
        from test_api import chamar
        app = TrilhaApi(token="segredo", clientes_dir=RAIZ / "tests" / "fixtures" / "clientes")
        leads = json.loads((FIX / "funil_leads.json").read_text(encoding="utf-8"))
        status, r = chamar(app, "POST", "/funil/raio-x", {"cliente_id": "_exemplo", "leads": leads, "investimento": 7550,
                                                          "gasto_por_codigo": {"v0": 1800}})
        self.assertEqual(status, 200)
        self.assertEqual(r["por_criativo"]["v0"]["gasto"], 1800.0)
        status, _ = chamar(app, "POST", "/funil/raio-x", {"cliente_id": "_exemplo", "leads": leads, "gasto_por_codigo": [1, 2]})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
