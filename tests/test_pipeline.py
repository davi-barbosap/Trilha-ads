import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from trilha.conversao.hash import hash_email
from trilha.conversao.pipeline import eventos_do_webhook, executar, processar
from trilha.core.perfil import carregar_perfil
from trilha.integracoes.kommo import DadosLead, extrair_dados_lead
from trilha.plataformas.google.conversoes_offline import formatar_data_hora

RAIZ = Path(__file__).resolve().parents[1]
FIX = RAIZ / "tests" / "fixtures"


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.perfil = carregar_perfil(RAIZ / "tests" / "fixtures" / "clientes" / "_exemplo" / "perfil.yaml")
        lead = json.loads((FIX / "kommo_lead.json").read_text())
        contato = json.loads((FIX / "kommo_contato.json").read_text())
        self.dados = extrair_dados_lead(lead, [contato], self.perfil.crm.campos)
        self.webhook = (FIX / "kommo_webhook.txt").read_text()

    def test_lead_qualificado_vai_para_meta_e_google(self):
        envios = executar(processar(self.webhook, self.perfil, lambda _: self.dados), simular=True)
        meta, google = envios
        self.assertEqual((meta.plataforma, meta.evento), ("meta", "lead_qualificado"))
        self.assertTrue(meta.destino.endswith("/000000000000000/events"))
        ev = meta.corpo["data"][0]
        self.assertEqual(ev["event_name"], "LeadQualificado")
        self.assertEqual(ev["event_id"], "kommo-987654-lead_qualificado")
        self.assertEqual(ev["action_source"], "system_generated")
        self.assertEqual(ev["user_data"]["em"], [hash_email("cliente.exemplo@email.com")])
        self.assertEqual(ev["user_data"]["fbc"], "fb.1.1789900000000.IwAR-exemplo")
        self.assertAlmostEqual(ev["custom_data"]["value"], 112.5)  # valor ponderado = CPL qualificado máximo
        self.assertNotIn("access_token", json.dumps(meta.corpo))

        self.assertEqual(google.destino, "https://datamanager.googleapis.com/v1/events:ingest")
        [dest] = google.corpo["destinations"]
        self.assertEqual(dest["operatingAccount"], {"accountType": "GOOGLE_ADS", "accountId": "1234567890"})
        self.assertEqual(dest["loginAccount"]["accountId"], "1112223333")
        self.assertEqual(dest["productDestinationId"], "900000002")
        self.assertEqual(google.corpo["encoding"], "HEX")
        ev = google.corpo["events"][0]
        self.assertEqual(ev["adIdentifiers"], {"gclid": "Cj0KCQjw-exemplo"})
        self.assertEqual(ev["transactionId"], "kommo-987654-lead_qualificado")
        self.assertTrue(ev["eventTimestamp"].endswith("-03:00"))
        self.assertEqual(len(ev["userData"]["userIdentifiers"]), 2)

    def test_venda_usa_receita_da_comissao_e_nao_o_valor_do_imovel(self):
        corpo = "leads[status][0][id]=987654&leads[status][0][status_id]=142&leads[status][0][pipeline_id]=1111"
        self.dados.status_id = 142
        meta, google = processar(corpo, self.perfil, lambda _: self.dados)
        self.assertEqual(meta.corpo["data"][0]["event_name"], "Purchase")
        self.assertAlmostEqual(meta.corpo["data"][0]["custom_data"]["value"], 560000 * 0.05 * 0.5)
        self.assertAlmostEqual(google.corpo["events"][0]["conversionValue"], 14000)

    def test_whatsapp_usa_business_messaging(self):
        dados = DadosLead(lead_id=1, status_id=3333, pipeline_id=1111, ids={"ctwa_clid": "ARAkLk-exemplo"})
        corpo = "leads[status][0][id]=1&leads[status][0][status_id]=3333&leads[status][0][pipeline_id]=1111"
        meta, google = processar(corpo, self.perfil, lambda _: dados)
        ev = meta.corpo["data"][0]
        self.assertEqual(ev["action_source"], "business_messaging")
        self.assertEqual(ev["messaging_channel"], "whatsapp")
        self.assertEqual(ev["user_data"], {"ctwa_clid": "ARAkLk-exemplo", "page_id": "000000000000000"})
        self.assertIsNone(google.corpo)
        self.assertIn("sem gclid", google.pulado)

    def test_eventos_internos_e_etapa_repetida(self):
        perdido = "leads[status][0][id]=1&leads[status][0][status_id]=143&leads[status][0][pipeline_id]=1111"
        self.dados.status_id = 143
        [e] = processar(perdido, self.perfil, lambda _: self.dados)
        self.assertEqual(e.evento, "perdido")
        self.assertIn("uso interno", e.pulado)

        repetido = "leads[status][0][id]=1&leads[status][0][status_id]=3333&leads[status][0][pipeline_id]=1111&leads[status][0][old_status_id]=3333"
        self.assertEqual(eventos_do_webhook(repetido, self.perfil), [])

        desconhecido = "leads[status][0][id]=1&leads[status][0][status_id]=7777&leads[status][0][pipeline_id]=1111"
        self.assertEqual(processar(desconhecido, self.perfil, lambda _: self.dados), [])

    def test_lead_sem_identificador(self):
        corpo = "leads[status][0][id]=1&leads[status][0][status_id]=3333&leads[status][0][pipeline_id]=1111"
        meta, google = processar(corpo, self.perfil, lambda _: DadosLead(lead_id=1, status_id=3333))
        self.assertIn("sem identificador", meta.pulado)
        self.assertIn("sem gclid", google.pulado)

    def test_webhook_forjado_nao_vira_conversao(self):
        # O webhook diz "venda", mas no Kommo o lead está em outra etapa: nada é enviado.
        forjado = "leads[status][0][id]=987654&leads[status][0][status_id]=142&leads[status][0][pipeline_id]=1111"
        [e] = processar(forjado, self.perfil, lambda _: self.dados)  # lead real está na etapa 3333
        self.assertIsNone(e.corpo)
        self.assertIn("etapa não confirmada", e.pulado)

    def test_google_em_envio_real_fica_pendente_e_nao_pulado(self):
        envios = processar(self.webhook, self.perfil, lambda _: self.dados)
        google = [e for e in envios if e.plataforma == "google"][0]
        google_real = executar([google], simular=False)[0]
        self.assertIsNone(google_real.pulado)
        self.assertIn("não implementado", google_real.pendente)

    def test_venda_fora_da_janela_do_google_fica_so_no_relatorio(self):
        corpo = "leads[status][0][id]=987654&leads[status][0][status_id]=142&leads[status][0][pipeline_id]=1111&leads[status][0][updated_at]=1790000000"
        self.dados.status_id = 142
        self.dados.criado_em = 1790000000 - 100 * 86400
        meta, google = processar(corpo, self.perfil, lambda _: self.dados)
        self.assertIsNotNone(meta.corpo)
        self.assertIsNone(google.corpo)
        self.assertIsNone(google.pulado)
        self.assertIn("atribuição do Kommo", google.informativo)

    def test_data_hora_google_exige_fuso(self):
        self.assertEqual(formatar_data_hora(datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)), "2026-10-03T12:00:00+00:00")
        with self.assertRaises(ValueError):
            formatar_data_hora(datetime(2026, 10, 3, 12, 0))


if __name__ == "__main__":
    unittest.main()
