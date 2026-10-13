"""Regras canônicas da Trilha extraídas dos repositórios de mensuração da operação."""

import unittest
from datetime import datetime, timedelta, timezone

from trilha.core.atribuicao import GOOGLE, META, NAO_RASTREADO, normalizar_canal
from trilha.core.funil import LeadFunil, raio_x, semana_do_mes
from trilha.core.perfil import Crm
from trilha.core.playbook import carregar_playbook

T0 = datetime(2026, 9, 1, 9, tzinfo=timezone.utc)
PB = carregar_playbook("imobiliario")


def lead(i, **kw):
    return LeadFunil(lead_id=i, etapas=kw.pop("etapas", {"lead": T0}), **kw)


class TestCanal(unittest.TestCase):
    def test_valores_reais_do_campo_origem(self):
        casos = {"Meta+Ads": META, "Facebook": META, "instagram": META, "google": GOOGLE, "Google": GOOGLE,
                 "Fonte: Busca Paga | google": GOOGLE, "unknown": NAO_RASTREADO, "": NAO_RASTREADO,
                 None: NAO_RASTREADO, "2026-06-17": NAO_RASTREADO, "(referral)": "Outro site", "Recomendação": "Indicação",
                 "chatgpt.com": "chatgpt.com", "TikTok": "TikTok", "podcast": "Podcast"}
        for origem, esperado in casos.items():
            self.assertEqual(normalizar_canal(origem), esperado, origem)


class TestVariosFunis(unittest.TestCase):
    def setUp(self):
        self.crm = Crm.model_validate({"subdominio": "x", "funis": [
            {"pipeline_id": 1, "nome": "SDR", "papel": "entrada", "ganho_significa": "comparecimento"},
            {"pipeline_id": 2, "nome": "Closer", "papel": "fechamento"},
            {"pipeline_id": 3, "nome": "Base RD", "papel": "base"},
            {"pipeline_id": 4, "nome": "Teste", "papel": "ignorar"},
        ], "mapa_eventos": [{"pipeline_id": 1, "status_id": 10, "evento": "lead_qualificado"}]})

    def test_ganho_muda_de_sentido_conforme_o_funil(self):
        self.assertEqual(self.crm.evento_para(142, 1), "comparecimento")  # SDR: reunião realizada
        self.assertEqual(self.crm.evento_para(142, 2), "venda")  # Closer: venda de verdade
        self.assertEqual(self.crm.evento_para(143, 2), "perdido")
        self.assertEqual(self.crm.evento_para(10, 1), "lead_qualificado")

    def test_base_teste_e_funil_desconhecido_nao_geram_evento(self):
        self.assertIsNone(self.crm.evento_para(142, 3))
        self.assertIsNone(self.crm.evento_para(142, 4))
        self.assertIsNone(self.crm.evento_para(142, 99))

    def test_funil_de_entrada_sem_significado_do_ganho_nao_conta_venda(self):
        crm = Crm.model_validate({"subdominio": "x", "funis": [{"pipeline_id": 1, "papel": "entrada"}]})
        self.assertIsNone(crm.evento_para(142, 1))
        self.assertEqual(crm.evento_para(143, 1), "perdido")


class TestReguaDoRaioX(unittest.TestCase):
    def test_mesma_pessoa_conta_uma_vez_por_mes(self):
        leads = [lead(1, pessoa="p1"), lead(2, pessoa="p1", etapas={"lead": T0 + timedelta(days=3)}),
                 lead(3, pessoa="p1", etapas={"lead": T0 + timedelta(days=40)})]  # volta no mês seguinte
        r = raio_x(leads, PB)
        self.assertEqual(r["leads"], 2)
        self.assertEqual(r["qualidade_dos_dados"]["leads_duplicados_removidos"], 1)

    def test_venda_duplicada_e_duas_unidades(self):
        v = {"lead": T0, "venda": T0 + timedelta(days=30)}
        dup = [lead(1, pessoa="p", etapas=dict(v), valor=500_000, produto="A"),
               lead(2, pessoa="p", etapas={"lead": T0 + timedelta(days=31), "venda": T0 + timedelta(days=30)}, valor=500_000, produto="A")]
        self.assertEqual(raio_x(dup, PB)["resultado"]["vendas"], 1)
        duas = [lead(1, pessoa="p", etapas=dict(v), valor=500_000, produto="A"),
                lead(2, pessoa="p", etapas={"lead": T0 + timedelta(days=31), "venda": T0 + timedelta(days=30)}, valor=500_000, produto="B")]
        self.assertEqual(raio_x(duas, PB)["resultado"]["vendas"], 2)

    def test_custos_so_sobre_midia_paga_cac_teto_roas_piso(self):
        venda = {"lead": T0, "venda": T0 + timedelta(days=20)}
        leads = ([lead(i, canal=META) for i in range(8)] + [lead(10, canal=META, etapas=dict(venda), valor=1_000_000)]
                 + [lead(20 + i, canal=NAO_RASTREADO) for i in range(10)]
                 + [lead(40, canal=NAO_RASTREADO, etapas=dict(venda), valor=2_000_000)])
        res = raio_x(leads, PB, investimento=900)["resultado"]
        self.assertEqual(res["leads_de_midia_paga"], 9)
        self.assertEqual(res["diagnostico_cpl"], 100.0)  # 900 ÷ 9 pagos, não ÷ 20
        self.assertEqual(res["custo_por_venda"], 900.0)  # teto: a venda não rastreada fica de fora
        self.assertEqual(res["vendas_nao_rastreadas"], 1)
        self.assertEqual(res["valor_vendido"], 3_000_000)
        self.assertAlmostEqual(res["retorno_sobre_investimento"], 1111.1)  # piso: só a venda paga

    def test_closer_parados_e_baldes_do_sistema(self):
        comp = {"lead": T0, "comparecimento": T0 + timedelta(days=5)}
        leads = [lead(1, responsavel="Ana", closer="Rui", etapas=dict(comp)),
                 lead(2, responsavel="DESCARTE"),
                 lead(3, responsavel="Ana", ultima_movimentacao=T0)]
        r = raio_x(leads, PB, agora=T0 + timedelta(days=20))
        self.assertNotIn("DESCARTE", r["por_responsavel"])
        self.assertFalse(r["por_responsavel"]["Ana"]["amostra_suficiente"])
        self.assertEqual(r["por_closer"]["Rui"]["comparecimentos"], 1)
        self.assertIn(3, [p["lead_id"] for p in r["parados"]])
        self.assertTrue(any("parados" in s for s in r["sinais"]))

    def test_sinal_de_resgate_antes_de_aumentar_volume(self):
        perdidos = [lead(i, perdido_em=T0, motivo_perda="Não respondeu às tentativas de contato") for i in range(4)]
        perdidos += [lead(10, perdido_em=T0, motivo_perda="Contato inválido")]
        r = raio_x(perdidos, PB)
        self.assertTrue(any("resgatar a base" in s for s in r["sinais"]))

    def test_semanas_da_trilha(self):
        dias = {1: "w1", 7: "w1", 8: "w2", 14: "w2", 15: "w3", 21: "w3", 22: "w4", 31: "w4"}
        for dia, w in dias.items():
            self.assertEqual(semana_do_mes(datetime(2026, 8, dia)), w)


if __name__ == "__main__":
    unittest.main()
