"""Modelos de fluxo do n8n (n8n/modelos/): estrutura íntegra antes de qualquer importação."""

import json
import unittest
from pathlib import Path

MODELOS = Path(__file__).resolve().parents[1] / "n8n" / "modelos"


def _carregar(nome):
    return json.loads((MODELOS / nome).read_text(encoding="utf-8"))


class TestVersao(unittest.TestCase):
    def test_versao_unica(self):
        # a /saude informa trilha.__version__; o pacote instalado usa o pyproject
        import re
        import trilha
        pyproject = (MODELOS.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1), trilha.__version__)


class TestModelos(unittest.TestCase):
    def test_todos_os_modelos_sao_integros(self):
        arquivos = sorted(MODELOS.glob("*.json"))
        self.assertTrue(arquivos)
        for arq in arquivos:
            with self.subTest(arq.name):
                w = json.loads(arq.read_text(encoding="utf-8"))
                nomes = [n["name"] for n in w["nodes"]]
                self.assertEqual(len(nomes), len(set(nomes)), "nomes de nó repetidos")
                self.assertEqual(len({n["id"] for n in w["nodes"]}), len(nomes), "ids de nó repetidos")
                for origem, saidas in w["connections"].items():
                    self.assertIn(origem, nomes, f"conexão sai de nó inexistente: {origem}")
                    for ramo in saidas["main"]:
                        for destino in ramo:
                            self.assertIn(destino["node"], nomes, f"conexão para nó inexistente: {destino['node']}")
                for n in w["nodes"]:
                    for chave in ("id", "name", "type", "typeVersion", "position", "parameters"):
                        self.assertIn(chave, n, f"{n.get('name')}: falta {chave}")
                    # segredo nunca vai no modelo: token da trilha-api fica em credencial, Slack em variável
                    texto = json.dumps(n["parameters"])
                    self.assertNotIn("Bearer ", texto)
                    self.assertNotIn("hooks.slack.com/services/T", texto)

    def test_espera_entre_tentativas_cabe_no_limite_do_n8n(self):
        # o n8n limita waitBetweenTries a 5000 ms e ignora valores maiores sem avisar
        for arq in MODELOS.glob("*.json"):
            for n in json.loads(arq.read_text(encoding="utf-8"))["nodes"]:
                with self.subTest(arq.name, no=n["name"]):
                    self.assertLessEqual(n.get("waitBetweenTries", 0), 5000)
                    self.assertLessEqual(n.get("maxTries", 1), 5)

    def test_w01_filtra_antes_de_chamar_a_api(self):
        w = _carregar("w01-conversao-real.json")
        con = w["connections"]
        self.assertEqual(con["Responder 200 ao Kommo"]["main"][0][0]["node"], "Lead novo ou mudança de etapa?")
        self.assertEqual(con["Lead novo ou mudança de etapa?"]["main"][0][0]["node"], "trilha-api /conversao")
        self.assertEqual(con["Lead novo ou mudança de etapa?"]["main"][1], [])  # 'lead alterado' termina aqui
        api = next(n for n in w["nodes"] if n["name"] == "trilha-api /conversao")
        self.assertIn("$env.TRILHA_API_URL", api["parameters"]["url"])
        self.assertEqual(api["parameters"]["genericAuthType"], "httpHeaderAuth")

    def test_w01_resposta_imediata_ao_kommo(self):
        # o Kommo desativa webhooks que demoram a responder: o 200 sai antes de qualquer processamento
        w = _carregar("w01-conversao-real.json")
        self.assertEqual(w["connections"]["Webhook Kommo"]["main"][0][0]["node"], "Responder 200 ao Kommo")
        webhook = next(n for n in w["nodes"] if n["name"] == "Webhook Kommo")
        self.assertEqual(webhook["parameters"]["responseMode"], "responseNode")
        self.assertEqual(webhook["webhookId"], "trilha-w01-kommo")  # faz parte da URL: /webhook/trilha-w01-kommo/kommo/<cliente>

    def test_producao_nao_guarda_execucoes_bem_sucedidas(self):
        # LGPD: o corpo do webhook e o segredo na URL não ficam no histórico. Quem decide é o ambiente
        # (produção = none); o modelo não pode forçar o contrário.
        self.assertNotEqual(_carregar("w01-conversao-real.json")["settings"].get("saveDataSuccessExecution"), "all")
        compose = (MODELOS.parents[1] / "infra" / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("EXECUTIONS_DATA_SAVE_ON_SUCCESS: none", compose)

    def test_w01_slack_so_com_slack_configurado(self):
        w = _carregar("w01-conversao-real.json")
        se = next(n for n in w["nodes"] if n["name"] == "Algo foi pulado?")
        expressoes = [c["leftValue"] for c in se["parameters"]["conditions"]["conditions"]]
        self.assertTrue(any("SLACK_WEBHOOK_URL" in e for e in expressoes))

    def test_w10_nao_falha_sem_slack(self):
        con = _carregar("w10-vigia-de-falhas.json")["connections"]
        self.assertEqual(con["Quando um fluxo falhar"]["main"][0][0]["node"], "Slack configurado?")


if __name__ == "__main__":
    unittest.main()
