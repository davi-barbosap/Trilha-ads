import copy
import unittest
from pathlib import Path

import yaml
from pydantic import ValidationError

from trilha.core.perfil import Perfil, carregar_perfil

EXEMPLO = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "clientes" / "_exemplo" / "perfil.yaml"


class TestPerfil(unittest.TestCase):
    def setUp(self):
        self.bruto = yaml.safe_load(EXEMPLO.read_text(encoding="utf-8"))

    def test_exemplo_valido(self):
        p = carregar_perfil(EXEMPLO)
        self.assertEqual(p.cliente.segmento, "imobiliario")
        self.assertEqual(p.freio.modo, "pausar")
        self.assertEqual(p.operacao.dia_otimizacao, "segunda")

    def test_mapa_inclui_etapas_de_sistema_do_kommo(self):
        crm = carregar_perfil(EXEMPLO).crm
        self.assertEqual(crm.evento_para(3333, 1111), "lead_qualificado")
        self.assertIsNone(crm.evento_para(3333, 9999))  # outro funil
        self.assertEqual(crm.evento_para(142, 1111), "venda")  # funil de fechamento
        self.assertEqual(crm.evento_para(143, 1111), "perdido")
        self.assertIsNone(crm.evento_para(142, 9999))  # funil não cadastrado não gera evento

    def test_freio_padrao_e_opcao_a_e_aceita_opcao_b(self):
        bruto = copy.deepcopy(self.bruto)
        del bruto["freio"]
        self.assertEqual(Perfil.model_validate(bruto).freio.modo, "pausar")
        bruto["freio"] = {"modo": "avisar"}
        self.assertEqual(Perfil.model_validate(bruto).freio.modo, "avisar")
        bruto["freio"] = {"modo": "otimizar_sozinho"}
        with self.assertRaises(ValidationError):
            Perfil.model_validate(bruto)

    def test_bloco_autonomia_antigo_e_ignorado_sem_quebrar(self):
        bruto = copy.deepcopy(self.bruto)
        bruto["autonomia"] = {"negativas_obvias": "L1"}
        self.assertEqual(Perfil.model_validate(bruto).freio.modo, "pausar")

    def test_cliente_id_no_formato_de_pasta(self):
        bruto = copy.deepcopy(self.bruto)
        bruto["cliente"]["id"] = "../outro"
        with self.assertRaises(ValidationError):
            Perfil.model_validate(bruto)

    def test_operacao_valida_dias_e_semana(self):
        bruto = copy.deepcopy(self.bruto)
        bruto["operacao"]["dia_otimizacao"] = "domingo"
        with self.assertRaises(ValidationError):
            Perfil.model_validate(bruto)
        bruto = copy.deepcopy(self.bruto)
        bruto["operacao"]["semana_reuniao"] = 5
        with self.assertRaises(ValidationError):
            Perfil.model_validate(bruto)

    def test_campo_desconhecido_e_rejeitado(self):
        bruto = copy.deepcopy(self.bruto)
        bruto["verba"]["mensal_planejda"] = 1
        with self.assertRaises(ValidationError):
            Perfil.model_validate(bruto)

    def test_evento_invalido_no_mapa(self):
        bruto = copy.deepcopy(self.bruto)
        bruto["crm"]["mapa_eventos"][0]["evento"] = "visita"
        with self.assertRaises(ValidationError):
            Perfil.model_validate(bruto)


if __name__ == "__main__":
    unittest.main()
