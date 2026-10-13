import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trilha.core.funil import LeadFunil, classificar_perda, raio_x
from trilha.core.perfil import Crm
from trilha.core.playbook import carregar_playbook

FIX = Path(__file__).parent / "fixtures"
T0 = datetime(2026, 9, 1, 9, tzinfo=timezone.utc)


class TestRaioX(unittest.TestCase):
    """Cliente do imobiliário da operação, sem identificação: R$ 7.550 investidos, 425 leads, 4 vendas, R$ 7.084.000 em VGV."""

    @classmethod
    def setUpClass(cls):
        cls.playbook = carregar_playbook("imobiliario")
        leads = [LeadFunil.model_validate(x) for x in json.loads((FIX / "funil_leads.json").read_text())]
        sempre_aberto = Crm(subdominio="x", horario_comercial={"dias": list(range(7)), "inicio": 0, "fim": 24})
        cls.r = raio_x(leads, cls.playbook, investimento=7550, sla_primeiro_contato_min=30, crm=sempre_aberto)

    def test_resultado_e_venda_nao_cpl(self):
        res = self.r["resultado"]
        self.assertEqual((res["vendas"], res["valor_vendido"]), (4, 7_084_000))
        self.assertEqual(res["custo_por_venda"], 1887.5)
        self.assertEqual(res["retorno_sobre_investimento"], 938.3)
        self.assertEqual(res["diagnostico_cpl"], 17.76)

    def test_etapa_por_etapa_com_nomes_do_segmento(self):
        etapas = {e["etapa"]: e for e in self.r["etapas"]}
        self.assertEqual([e["entraram"] for e in self.r["etapas"]], [425, 300, 120, 50, 25, 10, 4])
        self.assertEqual(etapas["comparecimento"]["rotulo"], "Visita realizada")
        self.assertEqual(etapas["em_atendimento"]["conversao_da_anterior"], 0.7059)

    def test_maior_vazamento_e_antes_do_fechamento(self):
        v = self.r["maior_vazamento"]
        self.assertEqual((v["etapa"], v["lado"]), ("comparecimento", "comercial"))
        self.assertAlmostEqual(v["vendas_a_mais"], 1.2)
        self.assertEqual([x["etapa"] for x in self.r["vazamentos"]], ["comparecimento", "em_atendimento", "agendamento"])
        # passagens acima da referência não aparecem como vazamento
        self.assertNotIn("venda", [x["etapa"] for x in self.r["vazamentos"]])

    def test_primeiro_contato_cadencia_e_responsavel(self):
        pc = self.r["primeiro_contato"]
        self.assertEqual((pc["dentro_do_sla"], pc["sem_primeiro_contato"]), (0.5, 125))
        self.assertEqual(pc["mediana_minutos_uteis"], pc["mediana_minutos_corridos"])  # expediente 24 h no teste
        self.assertEqual(self.r["cadencia"]["mediana_tentativas_perdidos_antes_de_qualificar"], 1)
        self.assertEqual(self.r["por_responsavel"]["Ana"]["dentro_do_sla"], 1.0)
        self.assertEqual(self.r["por_responsavel"]["Bruno"]["dentro_do_sla"], 0.0)

    def test_marketing_entregou_e_comercial_converteu(self):
        m, c = self.r["marketing_entregou"], self.r["comercial_converteu"]
        self.assertEqual((m["leads"], m["qualificados"], m["agendamentos"]), (425, 120, 50))
        self.assertEqual(m["custo_por_qualificado"], 62.92)
        self.assertEqual((c["vendas"], c["comparecimento"]), (4, 0.5))
        self.assertGreater(c["perdas_atendimento"], c["perdas_comercial"])

    def test_perdas_explicitas_por_etapa_e_categoria(self):
        p = self.r["perdas"]
        self.assertEqual(sum(p["por_categoria"].values()), 425 - 4)
        self.assertEqual(p["por_categoria"]["sem_motivo"], 20)
        self.assertEqual(p["qualificados_perdidos_por_motivo_de_lead"], 16)

    def test_atribuicao_pela_campanha_do_kommo(self):
        camp = self.r["por_campanha"]
        self.assertEqual(sum(c["vendas"] for c in camp.values()), 4)
        self.assertEqual(sum(c["leads"] for c in camp.values()), 425)


class TestPerdaEAmostra(unittest.TestCase):
    def setUp(self):
        self.playbook = carregar_playbook("imobiliario")

    def test_mesmo_motivo_muda_de_leitura_conforme_a_etapa(self):
        antes = LeadFunil(lead_id=1, etapas={"lead": T0}, perdido_em=T0, motivo_perda="Fora do perfil financeiro")
        depois = LeadFunil(lead_id=2, etapas={"lead_qualificado": T0}, perdido_em=T0, motivo_perda="Fora do perfil financeiro")
        self.assertEqual(classificar_perda(antes, self.playbook), ("lead", "antes_da_qualificacao"))
        self.assertEqual(classificar_perda(depois, self.playbook), ("lead", "depois_da_qualificacao"))
        estranho = LeadFunil(lead_id=3, etapas={"lead": T0}, perdido_em=T0, motivo_perda="Motivo inventado")
        self.assertEqual(classificar_perda(estranho, self.playbook)[0], "nao_classificado")

    def test_etapa_pulada_conta_como_passada(self):
        l = LeadFunil(lead_id=1, etapas={"lead": T0, "venda": T0 + timedelta(days=30)}, valor=100)
        self.assertTrue(l.alcancou("comparecimento"))

    def test_amostra_pequena_nao_gera_vazamento(self):
        leads = [LeadFunil(lead_id=i, etapas={"lead": T0}) for i in range(10)]
        r = raio_x(leads, self.playbook, investimento=100)
        self.assertIsNone(r["maior_vazamento"])

    def test_segmento_sem_playbook_usa_padrao_sem_referencia(self):
        r = raio_x([LeadFunil(lead_id=1, etapas={"lead": T0})], carregar_playbook("educacao"))
        self.assertEqual(r["etapas"][3]["rotulo"], "Reunião agendada")
        self.assertIsNone(r["etapas"][3]["referencia"])


if __name__ == "__main__":
    unittest.main()
