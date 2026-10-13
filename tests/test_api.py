import io
import json
import unittest
from pathlib import Path

from trilha.api import TrilhaApi
from trilha.integracoes.kommo import extrair_dados_lead

RAIZ = Path(__file__).resolve().parents[1]
FIX = RAIZ / "tests" / "fixtures"


def chamar(app, metodo, caminho, corpo=None, token="segredo"):
    bruto = json.dumps(corpo).encode() if corpo is not None else b""
    environ = {
        "REQUEST_METHOD": metodo, "PATH_INFO": caminho,
        "CONTENT_LENGTH": str(len(bruto)), "wsgi.input": io.BytesIO(bruto),
    }
    if token:
        environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    capturado = {}
    resposta = b"".join(app(environ, lambda status, _h: capturado.setdefault("status", int(status.split()[0]))))
    return capturado["status"], json.loads(resposta)


class TestApi(unittest.TestCase):
    def setUp(self):
        lead = json.loads((FIX / "kommo_lead.json").read_text())
        contato = json.loads((FIX / "kommo_contato.json").read_text())
        self.buscas = []

        def obter(perfil, lead_id):
            self.buscas.append(lead_id)
            return extrair_dados_lead(lead, [contato], perfil.crm.campos)

        self.app = TrilhaApi(token="segredo", clientes_dir=RAIZ / "tests" / "fixtures" / "clientes", obter_dados=obter,
                             envio_real_permitido=False, segredos_webhook={"_exemplo": "wh-exemplo"})

    def test_saude_sem_token_e_autenticacao(self):
        self.assertEqual(chamar(self.app, "GET", "/saude", token=None)[0], 200)
        self.assertEqual(chamar(self.app, "POST", "/calcular", {"cliente_id": "_exemplo"}, token=None)[0], 401)
        self.assertEqual(chamar(self.app, "POST", "/calcular", {"cliente_id": "_exemplo"}, token="errado")[0], 401)
        self.assertEqual(chamar(TrilhaApi(token=""), "POST", "/calcular", {})[0], 500)

    def test_cliente_id_seguro(self):
        self.assertEqual(chamar(self.app, "POST", "/validar", {"cliente_id": "../etc"})[0], 400)
        self.assertEqual(chamar(self.app, "POST", "/validar", {"cliente_id": "nao-existe"})[0], 404)
        status, r = chamar(self.app, "POST", "/validar", {"cliente_id": "_exemplo"})
        self.assertEqual((status, r["ok"]), (200, True))

    def test_perfil_invalido_volta_422(self):
        status, r = chamar(self.app, "POST", "/validar", {"perfil": {"versao": 1}})
        self.assertEqual(status, 422)
        self.assertTrue(r["detalhes"])

    def test_calcular(self):
        status, r = chamar(self.app, "POST", "/calcular", {"cliente_id": "_exemplo", "verba": 30000})
        self.assertEqual(status, 200)
        self.assertAlmostEqual(r["cpl_max"], 28.125)
        self.assertEqual(r["degraus_viaveis"], ["lead", "lead_qualificado"])

    def test_conversao_com_corpo_interpretado_pelo_n8n(self):
        corpo = {"leads": {"status": [{"id": "987654", "status_id": "3333", "pipeline_id": "1111", "old_status_id": "2222"}]}}
        status, r = chamar(self.app, "POST", "/conversao",
                           {"cliente_id": "_exemplo", "webhook_token": "wh-exemplo", "corpo": corpo, "simular": False})
        self.assertEqual(status, 200)
        self.assertTrue(r["simulado"])  # ambiente não permite envio real: a requisição não consegue forçar
        self.assertEqual(r["resumo"]["simulados"], 2)
        self.assertEqual(self.buscas, [987654])
        texto = json.dumps(r)
        self.assertNotIn("98765-4321", texto)  # telefone em claro nunca volta para o n8n
        self.assertNotIn("Email.com", texto)

    def test_conversao_com_corpo_original(self):
        corpo = (FIX / "kommo_webhook.txt").read_text()
        status, r = chamar(self.app, "POST", "/conversao", {"cliente_id": "_exemplo", "webhook_token": "wh-exemplo", "corpo": corpo})
        self.assertEqual((status, len(r["envios"])), (200, 2))

    def test_isolamento_entre_clientes(self):
        corpo = (FIX / "kommo_webhook.txt").read_text()  # vem da conta imobiliaria-exemplo
        base = {"cliente_id": "_exemplo", "corpo": corpo}
        # segredo de outro cliente (ou o antigo segredo global) não serve
        self.assertEqual(chamar(self.app, "POST", "/conversao", {**base, "webhook_token": "wh-outro"})[0], 403)
        self.assertEqual(chamar(self.app, "POST", "/conversao", base)[0], 403)
        # conta Kommo do corpo diferente da do perfil
        alheio = corpo.replace("imobiliaria-exemplo", "conta-de-outro-cliente")
        status, r = chamar(self.app, "POST", "/conversao", {**base, "corpo": alheio, "webhook_token": "wh-exemplo"})
        self.assertEqual(status, 403)
        self.assertIn("conta Kommo", r["erro"])
        # perfil inline não é aceito em /conversao (só cliente_id do repositório)
        self.assertEqual(chamar(self.app, "POST", "/conversao", {"perfil": {}, "corpo": corpo, "webhook_token": "x"})[0], 400)
        self.assertEqual(self.buscas, [])  # nenhuma leitura no Kommo em tentativa recusada

    def test_freio(self):
        status, r = chamar(self.app, "POST", "/freio/avaliar", {"cliente_id": "_exemplo", "campanhas": [
            {"plataforma": "meta", "campanha_id": "c1", "gasto_desde_ultimo_lead": 200},
        ]})
        self.assertEqual(status, 200)
        self.assertEqual(r["acoes"][0]["acao"], "pausar")
        self.assertEqual(chamar(self.app, "POST", "/freio/avaliar", {"cliente_id": "_exemplo", "campanhas": [{"x": 1}]})[0], 400)
        status, r = chamar(self.app, "POST", "/freio/avaliar", {"cliente_id": "_exemplo", "campanhas": [
            {"plataforma": "meta", "campanha_id": "c1", "ativa": "false", "gasto_desde_ultimo_lead": 200}]})
        self.assertEqual(status, 400)  # "false" em texto não vira verdadeiro

    def test_clientes_ignora_exemplo_e_lista_invalidos(self):
        import shutil, tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(RAIZ / "tests" / "fixtures" / "clientes" / "_exemplo", tmp / "_exemplo")
            shutil.copytree(RAIZ / "tests" / "fixtures" / "clientes" / "_exemplo", tmp / "imob-a")
            perfil_a = tmp / "imob-a" / "perfil.yaml"
            perfil_a.write_text(perfil_a.read_text().replace("id: _exemplo", "id: imob-a"))
            shutil.copytree(RAIZ / "tests" / "fixtures" / "clientes" / "_exemplo", tmp / "copiado-sem-ajustar")  # cliente.id errado
            (tmp / "quebrado").mkdir()
            (tmp / "quebrado" / "perfil.yaml").write_text("versao: 1\n")
            (tmp / "yaml-invalido").mkdir()
            (tmp / "yaml-invalido" / "perfil.yaml").write_text("versao: [1\n  sem: fechar")
            app = TrilhaApi(token="segredo", clientes_dir=tmp)
            status, r = chamar(app, "GET", "/clientes")
            self.assertEqual(status, 200)
            self.assertEqual([c["cliente_id"] for c in r["clientes"]], ["imob-a"])
            self.assertEqual(r["clientes"][0]["operacao"]["dia_otimizacao"], "segunda")
            self.assertEqual([i["cliente_id"] for i in r["invalidos"]], ["copiado-sem-ajustar", "quebrado", "yaml-invalido"])
            self.assertEqual(chamar(app, "POST", "/validar", {"cliente_id": "copiado-sem-ajustar"})[0], 422)
            self.assertEqual(chamar(app, "POST", "/validar", {"cliente_id": "yaml-invalido"})[0], 422)
        finally:
            shutil.rmtree(tmp)

    def test_raio_x_e_validar_com_ofertas(self):
        leads = json.loads((FIX / "funil_leads.json").read_text())
        status, r = chamar(self.app, "POST", "/funil/raio-x", {"cliente_id": "_exemplo", "leads": leads, "investimento": 7550})
        self.assertEqual(status, 200)
        self.assertEqual(r["maior_vazamento"]["etapa"], "comparecimento")
        self.assertEqual(r["resultado"]["valor_vendido"], 7084000)
        self.assertEqual(chamar(self.app, "POST", "/funil/raio-x", {"cliente_id": "_exemplo", "leads": [{"x": 1}]})[0], 400)
        status, r = chamar(self.app, "POST", "/validar", {"cliente_id": "_exemplo"})
        self.assertEqual(r["ofertas"][0]["aderencia_pendente"], [])

    def test_saude_das_contas(self):
        status, r = chamar(self.app, "POST", "/contas/saude", {"cliente_id": "_exemplo", "contas": [
            {"nome": "Conta principal", "saldo": 280, "gasto_7d": 700}]})
        self.assertEqual((status, r["saude"]), (200, "vermelho"))
        self.assertEqual(r["alertas"][0]["responsavel"], "Assessor responsável")
        self.assertEqual(chamar(self.app, "POST", "/contas/saude", {"cliente_id": "_exemplo", "contas": [{"saldo": -1}]})[0], 400)

    def test_rota_inexistente(self):
        self.assertEqual(chamar(self.app, "GET", "/nada")[0], 404)


if __name__ == "__main__":
    unittest.main()
