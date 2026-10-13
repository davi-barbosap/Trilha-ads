"""Kommo no padrão da Trilha (`kommo preparar`/`conferir`) e leitura do .env."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from trilha.ambiente import carregar_env, var_cliente
from trilha.core.playbook import carregar_playbook
from trilha.core.perfil import Crm
from trilha.integracoes.kommo_padrao import CAMPOS_TEXTO, ETAPAS_DO_FUNIL, EstadoConta, mapa_eventos, planejar

PADRAO = carregar_playbook("padrao")
IMOB = carregar_playbook("imobiliario")


class TestPlanejar(unittest.TestCase):
    def test_conta_vazia_pede_tudo(self):
        plano = planejar(EstadoConta(motivos_perda=[]), PADRAO, "Trilha – X")
        etapas = [s["name"] for s in plano.funil["_embedded"]["statuses"]]
        self.assertEqual(etapas, [PADRAO.rotulo(e) for e in ETAPAS_DO_FUNIL])
        self.assertEqual({c["name"] for c in plano.campos}, {*CAMPOS_TEXTO, "origem"})
        self.assertEqual([m["name"] for m in plano.motivos_perda], list(PADRAO.motivos_perda))

    def test_rodar_de_novo_nao_duplica(self):
        estado = EstadoConta(
            funis=[{"name": "Trilha – X"}],
            campos=[{"name": n} for n in (*CAMPOS_TEXTO, "origem")],
            motivos_perda=[{"name": m} for m in PADRAO.motivos_perda],
        )
        self.assertTrue(planejar(estado, PADRAO, "Trilha – X").vazio)

    def test_campos_existentes_casam_sem_diferenca_de_caixa(self):
        estado = EstadoConta(campos=[{"name": "UTM_Source"}, {"name": " gclid "}], motivos_perda=[])
        nomes = {c["name"] for c in planejar(estado, PADRAO, "F").campos}
        self.assertNotIn("utm_source", nomes)
        self.assertNotIn("gclid", nomes)

    def test_segmento_muda_rotulos_e_motivos(self):
        plano = planejar(EstadoConta(motivos_perda=[]), IMOB, "F")
        etapas = [s["name"] for s in plano.funil["_embedded"]["statuses"]]
        self.assertIn("Visita agendada", etapas)
        self.assertIn("Financiamento negado", [m["name"] for m in plano.motivos_perda])

    def test_motivos_indisponiveis_na_api(self):
        plano = planejar(EstadoConta(motivos_perda=None), PADRAO, "F")
        self.assertTrue(plano.motivos_indisponiveis)
        self.assertEqual(plano.motivos_perda, [])

    def test_ttclid_e_origem_tiktok(self):
        # o site da Trilha vende TikTok Ads: o clique precisa de campo próprio no Kommo
        plano = planejar(EstadoConta(motivos_perda=[]), PADRAO, "F")
        self.assertIn("ttclid", {c["name"] for c in plano.campos})
        origem = next(c for c in plano.campos if c["name"] == "origem")
        self.assertIn("tiktok", [e["value"] for e in origem["enums"]])


class TestMapaEventos(unittest.TestCase):
    def test_mapa_do_funil_criado(self):
        statuses = [{"id": 1, "name": "Incoming leads"}] + [
            {"id": 10 + i, "name": PADRAO.rotulo(e)} for i, e in enumerate(ETAPAS_DO_FUNIL)
        ] + [{"id": 142, "name": "Ganho"}, {"id": 143, "name": "Perdido"}]
        mapa = mapa_eventos({"id": 99, "_embedded": {"statuses": statuses}}, PADRAO)
        self.assertEqual([m["evento"] for m in mapa], ["lead", *ETAPAS_DO_FUNIL])
        self.assertTrue(all(m["pipeline_id"] == 99 for m in mapa))
        self.assertNotIn(142, [m["status_id"] for m in mapa])

    def test_etapa_desconhecida_no_meio_fica_fora(self):
        statuses = [{"id": 1, "name": PADRAO.rotulo("lead")}, {"id": 2, "name": "Etapa criada pelo cliente"},
                    {"id": 3, "name": PADRAO.rotulo("proposta")}]
        eventos = [m["evento"] for m in mapa_eventos({"id": 5, "_embedded": {"statuses": statuses}}, PADRAO)]
        self.assertEqual(eventos, ["lead", "proposta"])


class TestSubdominio(unittest.TestCase):
    def test_recusa_endereco_inteiro(self):
        for ruim in ("https://empresa.kommo.com", "empresa.kommo.com", "Empresa", ""):
            with self.assertRaises(ValueError, msg=ruim):
                Crm(subdominio=ruim)

    def test_aceita_subdominio(self):
        self.assertEqual(Crm(subdominio=" empresa-2 ").subdominio, "empresa-2")


class TestAmbiente(unittest.TestCase):
    def test_var_cliente(self):
        self.assertEqual(var_cliente("KOMMO_TOKEN_", "imob-a"), "KOMMO_TOKEN_IMOB_A")

    def test_carregar_env(self):
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text(
                "# comentário\n"
                "A_T1=valor   # comentário no fim\n"
                "export A_T2='com # dentro'\n"
                "A_T3=\n"
                "A_T4=do arquivo\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"A_T4": "do ambiente"}, clear=False):
                lidas = carregar_env(env)
                self.assertEqual(os.environ["A_T1"], "valor")
                self.assertEqual(os.environ["A_T2"], "com # dentro")
                self.assertNotIn("A_T3", os.environ)
                self.assertEqual(os.environ["A_T4"], "do ambiente")  # o ambiente vence o arquivo
                self.assertEqual(sorted(lidas), ["A_T1", "A_T2"])
                for k in lidas:
                    os.environ.pop(k)

    def test_arquivo_ausente(self):
        self.assertEqual(carregar_env("/nao/existe/.env"), [])


if __name__ == "__main__":
    unittest.main()
