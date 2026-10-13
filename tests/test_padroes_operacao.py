"""Padrões da leitura completa dos repositórios da operação (mensuração, atendimento, painéis e páginas)."""

import unittest
from datetime import date, datetime, timedelta, timezone

from trilha.core.atribuicao import META, normalizar_canal
from trilha.core.correcoes import Correcoes, aplicar_correcoes
from trilha.core.funil import LeadFunil, minutos_primeiro_contato, minutos_uteis, raio_x
from trilha.core.perfil import Crm, HorarioComercial, Meta
from trilha.core.periodo import janela_anterior, mes_corrente_anterior, variacao
from trilha.core.playbook import carregar_playbook
from trilha.core.saude import ContaAnuncio, avaliar_conta, saude_do_cliente

T0 = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)  # terça, 9h em Brasília
PB = carregar_playbook("padrao")
SEMPRE = Crm(subdominio="x", horario_comercial={"dias": list(range(7)), "inicio": 0, "fim": 24})


def lead(i, **kw):
    return LeadFunil(lead_id=i, etapas=kw.pop("etapas", {"lead": T0}), **kw)


class TestTagsDoKommo(unittest.TestCase):
    def test_tags_reais_sem_acento_e_variantes(self):
        leads = [lead(1, tags=["bot-nao-iniciado"]), lead(2, tags=["bot-concluído", "Interagiu"]),
                 lead(3, tags=["lead reativado | follow-up"]), lead(4, tags=["lead frio"])]
        r = raio_x(leads, PB, crm=SEMPRE)
        self.assertEqual(r["pre_atendimento"]["bot_nao_iniciado"], 0.6667)  # lead sem tag de bot fica fora da base
        self.assertEqual(r["reativacao"]["reativados"], 1)
        self.assertAlmostEqual(r["pre_atendimento"]["nao_qualificados_que_interagiram"], 0.25)  # sem a tag = não interagiu

    def test_reuniao_realizada_pela_tag_quando_o_card_sai_do_ganho(self):
        r = raio_x([lead(1, tags=["reunião-realizada"])], PB, crm=SEMPRE)
        self.assertEqual(r["etapas"][4]["entraram"], 1)  # comparecimento, sem data inventada
        self.assertIsNone(r["etapas"][4]["mediana_horas_desde_anterior"])

    def test_nao_cadastrou_e_perda_de_lead_e_nao_lead_parado(self):
        r = raio_x([lead(1, tags=["não-cadastrou"])], PB, crm=SEMPRE, agora=T0 + timedelta(days=40))
        self.assertEqual(r["perdas"]["por_categoria"], {"lead": 1})
        self.assertEqual(r["parados"], [])

    def test_etapa_de_saida_que_nao_e_143(self):
        crm = Crm.model_validate({"subdominio": "x", "mapa_eventos": [
            {"status_id": 77, "evento": "perdido", "motivo": "Contato inválido"}]})
        self.assertEqual((crm.evento_para(77, None), crm.motivo_para(77, None)), ("perdido", "Contato inválido"))


class TestPrimeiroContato(unittest.TestCase):
    def test_mensagem_humana_vale_mais_que_a_etapa_do_bot(self):
        l = lead(1, etapas={"lead": T0, "em_atendimento": T0 + timedelta(minutes=1)},
                 primeiro_contato_humano=T0 + timedelta(minutes=45))
        self.assertEqual(minutos_primeiro_contato(l), 45)

    def test_sem_atendimento_usa_a_qualificacao_e_descarta_absurdos(self):
        self.assertEqual(minutos_primeiro_contato(lead(1, etapas={"lead": T0, "lead_qualificado": T0 + timedelta(hours=2)})), 120)
        self.assertIsNone(minutos_primeiro_contato(lead(2, etapas={"lead": T0, "em_atendimento": T0 - timedelta(hours=1)})))
        self.assertIsNone(minutos_primeiro_contato(lead(3, etapas={"lead": T0, "em_atendimento": T0 + timedelta(days=40)})))

    def test_minutos_de_expediente(self):
        h = HorarioComercial()  # seg–sex, 8–18h, UTC−3
        noite = datetime(2026, 9, 1, 2, tzinfo=timezone.utc)  # segunda 23h em Brasília
        self.assertEqual(minutos_uteis(noite, datetime(2026, 9, 1, 11, 5, tzinfo=timezone.utc), h), 5)  # terça 8h05
        sexta = datetime(2026, 9, 4, 20, 30, tzinfo=timezone.utc)  # sexta 17h30
        self.assertEqual(minutos_uteis(sexta, datetime(2026, 9, 7, 11, 30, tzinfo=timezone.utc), h), 60)  # segunda 8h30


class TestResultado(unittest.TestCase):
    def test_ticket_ignora_venda_sem_valor_e_custo_por_reuniao_e_piso(self):
        v = {"lead": T0, "comparecimento": T0 + timedelta(days=3), "venda": T0 + timedelta(days=9)}
        leads = [lead(1, canal=META, etapas=dict(v), valor=100), lead(2, canal="Indicação", etapas=dict(v), valor=None),
                 lead(3, canal="Indicação", etapas={"lead": T0, "comparecimento": T0 + timedelta(days=2)})]
        r = raio_x(leads, PB, investimento=300, crm=SEMPRE)
        self.assertEqual(r["resultado"]["ticket_medio"], 100)
        self.assertEqual(r["qualidade_dos_dados"]["vendas_sem_valor"], 1)
        self.assertEqual(r["resultado"]["custo_por_comparecimento"], 100)  # 300 ÷ 3 reuniões (piso)
        self.assertEqual(r["resultado"]["custo_por_comparecimento_de_midia_paga"], 300)
        self.assertEqual(r["comercial_converteu"]["ciclo_de_vendas_mediana_dias"], 9)

    def test_score_vazio_aparece_e_duplicado_nao_e_perda(self):
        leads = [lead(1, score="A"), lead(2), lead(3, perdido_em=T0, motivo_perda="Lead duplicado")]
        r = raio_x(leads, PB, crm=SEMPRE)
        self.assertIn("sem score", r["por_score"])
        self.assertEqual(r["perdas"]["por_categoria"], {})
        self.assertEqual(r["qualidade_dos_dados"]["perdas_marcadas_como_lead_duplicado"], 1)


class TestTimeDoCliente(unittest.TestCase):
    def test_baldes_do_cliente_distribuicao_e_perfil(self):
        crm = Crm(subdominio="x", baldes=["Imobiliária X"], horario_comercial=SEMPRE.horario_comercial)
        leads = ([lead(i, responsavel="Ana") for i in range(30)] + [lead(100 + i, responsavel="Bia") for i in range(6)]
                 + [lead(200 + i, responsavel="Caio") for i in range(24)] + [lead(300, responsavel="Imobiliária X")])
        r = raio_x(leads, PB, crm=crm)
        self.assertNotIn("Imobiliária X", r["por_responsavel"])
        self.assertTrue(r["por_responsavel"]["Bia"]["distribuicao_desbalanceada"])  # 6 contra média 20
        self.assertIn("perfil", r["por_responsavel"]["Ana"])
        self.assertNotIn("perfil", r["por_responsavel"]["Bia"])  # amostra pequena
        self.assertTrue(any("Ana: 30 leads e nenhum qualificado" in s for s in r["sinais"]))

    def test_chegada_fora_do_horario(self):
        noite = datetime(2026, 9, 1, 1, tzinfo=timezone.utc)  # 22h em Brasília
        r = raio_x([lead(i, etapas={"lead": noite}) for i in range(25)], PB)
        self.assertEqual(r["chegada"]["fora_do_horario_comercial"], 1.0)
        self.assertEqual(r["chegada"]["pico"], {"dia_da_semana": 0, "hora": 22})
        self.assertTrue(any("fora do horário comercial" in s for s in r["sinais"]))


class TestCanalContasECorrecoes(unittest.TestCase):
    def test_referral_e_outro_site_e_apelido_do_cliente(self):
        self.assertEqual(normalizar_canal("(referral)"), "Outro site")
        self.assertEqual(normalizar_canal("Recomendação"), "Indicação")
        self.assertEqual(normalizar_canal("trilha-performance", {"trilha-performance": META}), META)

    def test_varias_contas_e_nutricao_sem_significado(self):
        self.assertEqual(Meta(ad_account_id="act_1", ad_account_ids=["act_2", "act_1"]).contas(), ["act_1", "act_2"])
        crm = Crm.model_validate({"subdominio": "x", "funis": [{"pipeline_id": 5, "papel": "nutricao"}]})
        self.assertIsNone(crm.evento_para(142, 5))

    def test_credencial_recusada_e_um_alerta_so(self):
        r = saude_do_cliente([], "Ana", "Bia", contas_esperadas=["act_1", "act_2"], credencial_ok=False)
        self.assertEqual((r["saude"], len(r["alertas"]), r["alertas"][0]["responsavel"]), ("sem_dado", 1, "Bia"))
        r = saude_do_cliente([ContaAnuncio(nome="a", id="act_1", saldo=5000, gasto_7d=700)], "Ana", "Bia",
                             contas_esperadas=["act_1", "act_2"])
        self.assertEqual([a["chave"] for a in r["alertas"]], ["acesso:act_2"])

    def test_pagamento_pendente_e_anuncio_com_problema(self):
        a = avaliar_conta(ContaAnuncio(nome="x", status=3, saldo=100, gasto_7d=70, anuncios_com_problema=2), "Ana")["alertas"]
        self.assertIn("pagamento", a[0]["acao"])
        self.assertEqual([x["nivel"] for x in a], ["P1", "P2"])

    def test_correcoes_confirmadas(self):
        v = lead(2, etapas={"lead": T0, "venda": datetime(2026, 10, 1, 15, tzinfo=timezone.utc)})
        c = Correcoes.model_validate({"excluir": [{"lead_id": 1, "motivo": "duplicado", "confirmado_por": "CRM"}],
                                      "data_da_venda": [{"lead_id": 2, "data": "2026-09-30", "motivo": "x", "confirmado_por": "CRM"}]})
        saida = aplicar_correcoes([lead(1), v], c)
        self.assertEqual([l.lead_id for l in saida], [2])
        self.assertEqual(saida[0].etapas["venda"].date(), date(2026, 9, 30))


class TestPeriodo(unittest.TestCase):
    def test_janela_anterior_tem_o_mesmo_tamanho(self):
        self.assertEqual(janela_anterior(date(2026, 9, 8), date(2026, 9, 14)), (date(2026, 9, 1), date(2026, 9, 7)))

    def test_mes_corrente_alinhado_ao_calendario(self):
        self.assertEqual(mes_corrente_anterior(date(2026, 3, 31)), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(mes_corrente_anterior(date(2026, 1, 10)), (date(2025, 12, 1), date(2025, 12, 10)))

    def test_taxa_em_pp_volume_em_pct(self):
        self.assertEqual(variacao(0.30, 0.25, taxa=True), {"valor": 5.0, "unidade": "pp", "leitura": "subiu"})
        self.assertEqual(variacao(90, 100)["valor"], -10.0)
        self.assertEqual(variacao(100.2, 100)["leitura"], "estável")
        self.assertEqual(variacao(5, 0)["leitura"], "sem base")


if __name__ == "__main__":
    unittest.main()
