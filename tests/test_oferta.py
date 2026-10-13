import unittest
from pathlib import Path

from pydantic import ValidationError

from trilha.core.oferta import Aderencia, Oferta, carregar_oferta
from trilha.core.playbook import Playbook, carregar_playbook

RAIZ = Path(__file__).resolve().parents[1]


class TestOferta(unittest.TestCase):
    def test_exemplo_valido_e_completo(self):
        o = carregar_oferta(RAIZ / "tests" / "fixtures" / "clientes" / "_exemplo" / "ofertas" / "residencial-exemplo.yaml")
        self.assertEqual(o.aderencia.pendencias(), [])
        self.assertEqual(o.aderencia.sinais_de_risco(), [])

    def test_aderencia_em_branco_lista_pendencias(self):
        self.assertEqual(len(Aderencia().pendencias()), 6)

    def test_pendencias_seguem_o_playbook_do_segmento(self):
        # finalidade (uso próprio ou investimento) é pergunta de imóvel: num curso não vira pendência
        escola = carregar_oferta(RAIZ / "clientes" / "_exemplo" / "ofertas" / "conversacao-adultos.yaml")
        self.assertEqual(escola.aderencia.pendencias(carregar_playbook("educacao").exige_na_aderencia()), [])
        self.assertIn("finalidade (uso próprio ou investimento)", Aderencia().pendencias(
            carregar_playbook("imobiliario").exige_na_aderencia()))
        self.assertNotIn("finalidade (uso próprio ou investimento)", Aderencia().pendencias(
            carregar_playbook("padrao").exige_na_aderencia()))

    def test_playbook_recusa_item_de_aderencia_que_nao_existe(self):
        with self.assertRaises(ValidationError):
            Playbook.model_validate({"segmento": "x", "aderencia_exige": ["perfil_comprador"]})

    def test_sinais_de_risco(self):
        a = Aderencia.model_validate({"vendas_fora_do_digital": {"avaliacao": "fraca"}, "aderencia_digital": "baixa",
                                      "reputacao": "obstaculo"})
        sinais = " ".join(a.sinais_de_risco())
        self.assertIn("nutrição mais longa", sinais)
        self.assertIn("baixa", sinais)
        self.assertIn("obstáculo", sinais)

    def test_campos_rigidos(self):
        with self.assertRaises(ValidationError):
            Oferta.model_validate({"oferta": {"nome": "x", "tipo": "curso"}, "aderencia": {"finalidade": "talvez"}})
        with self.assertRaises(ValidationError):
            Oferta.model_validate({"oferta": {"nome": "x", "tipo": "curso"}, "campo_novo": 1})


class TestPlaybook(unittest.TestCase):
    def test_imobiliario_sobrescreve_o_padrao(self):
        p = carregar_playbook("imobiliario")
        self.assertEqual(p.rotulo("agendamento"), "Visita agendada")
        self.assertEqual(p.rotulo("proposta"), "Proposta enviada")  # herdado do padrão
        self.assertEqual(p.motivos_perda["Contato inválido"], "lead")  # herdado
        self.assertEqual(p.motivos_perda["Financiamento negado"], "externo")  # próprio
        produto = 1.0
        for taxa in p.taxas_referencia.values():
            produto *= taxa
        self.assertAlmostEqual(produto, 0.0113, places=4)  # ~1%, coerente com a taxa de fechamento padrão

    def test_segmento_com_caminho_cai_no_padrao(self):
        self.assertEqual(carregar_playbook("../imobiliario").segmento, "padrao")


if __name__ == "__main__":
    unittest.main()
