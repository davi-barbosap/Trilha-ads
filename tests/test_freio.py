import copy
import unittest
from pathlib import Path

import yaml

from trilha.core.freio import MetricaCampanha, avaliar
from trilha.core.perfil import Perfil

EXEMPLO = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "clientes" / "_exemplo" / "perfil.yaml"


class TestFreio(unittest.TestCase):
    def setUp(self):
        self.bruto = yaml.safe_load(EXEMPLO.read_text(encoding="utf-8"))
        self.perfil = Perfil.model_validate(self.bruto)  # CPL máximo = R$ 28,125 → limite 3× = R$ 84,375

    def test_gasto_sem_lead(self):
        acoes = avaliar(self.perfil, [
            MetricaCampanha(plataforma="meta", campanha_id="c1", nome="Conversão", gasto_desde_ultimo_lead=90),
            MetricaCampanha(plataforma="meta", campanha_id="c2", nome="Teste", gasto_desde_ultimo_lead=80),
            MetricaCampanha(plataforma="meta", campanha_id="c3", nome="Pausada", ativa=False, gasto_desde_ultimo_lead=500),
        ])
        self.assertEqual([(a.campanha_id, a.acao, a.gatilho) for a in acoes], [("c1", "pausar", "gasto_sem_lead")])
        self.assertIn("R$ 84,38", acoes[0].motivo)

    def test_rastreamento_quebrado(self):
        acoes = avaliar(self.perfil, [
            MetricaCampanha(plataforma="google", campanha_id="g1", horas_sem_evento_conversao=8, gasto_ultimas_horas=40),
            MetricaCampanha(plataforma="google", campanha_id="g2", horas_sem_evento_conversao=8, gasto_ultimas_horas=0),  # parada: nada a proteger
            MetricaCampanha(plataforma="google", campanha_id="g3", horas_sem_evento_conversao=3, gasto_ultimas_horas=40),
            MetricaCampanha(plataforma="google", campanha_id="g4", horas_sem_evento_conversao=None, gasto_ultimas_horas=40),
        ])
        self.assertEqual([(a.campanha_id, a.gatilho) for a in acoes], [("g1", "rastreamento_quebrado")])

    def test_opcao_b_so_avisa_e_ordem_por_valor(self):
        bruto = copy.deepcopy(self.bruto)
        bruto["freio"]["modo"] = "avisar"
        acoes = avaliar(Perfil.model_validate(bruto), [
            MetricaCampanha(plataforma="meta", campanha_id="pequena", gasto_desde_ultimo_lead=100),
            MetricaCampanha(plataforma="meta", campanha_id="grande", gasto_desde_ultimo_lead=400),
        ])
        self.assertEqual([a.campanha_id for a in acoes], ["grande", "pequena"])
        self.assertTrue(all(a.acao == "avisar" for a in acoes))


class TestMetricaCampanha(unittest.TestCase):
    def test_tipos_rigidos(self):
        from pydantic import ValidationError
        for ruim in ({"ativa": "false"}, {"gasto_desde_ultimo_lead": None}, {"gasto_desde_ultimo_lead": -1},
                     {"plataforma": "tiktok"}, {"campo_extra": 1}):
            with self.assertRaises(ValidationError):
                MetricaCampanha.model_validate({"plataforma": "meta", "campanha_id": "c", **ruim})
        self.assertEqual(MetricaCampanha.model_validate(
            {"plataforma": "meta", "campanha_id": "c", "gasto_desde_ultimo_lead": "200"}).gasto_desde_ultimo_lead, 200)


if __name__ == "__main__":
    unittest.main()
