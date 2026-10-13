"""trilha-api: núcleo testado exposto por HTTP para o n8n (ADR-002).

Regra de divisão: o que custa dinheiro ou envolve dado pessoal é decidido aqui;
o n8n agenda, conecta e entrega. Dados pessoais de leads nunca passam pelo n8n:
a API busca o lead no Kommo e devolve só payloads com hash.

Rotas (todas exigem Authorization: Bearer <TRILHA_API_TOKEN>, exceto /saude):
  GET  /saude
  GET  /clientes       carteira com a agenda de cada cliente (para os fluxos em laço do n8n)
  POST /validar        {"cliente_id"} ou {"perfil": {...}}
  POST /calcular       {"cliente_id", "verba"?} ou {"perfil": {...}, "verba"?}
  POST /conversao      {"cliente_id", "webhook_token", "corpo": <webhook do Kommo, texto ou objeto>, "simular"?}
  POST /freio/avaliar  {"cliente_id", "campanhas": [{plataforma, campanha_id, nome, ativa,
                        gasto_desde_ultimo_lead, horas_sem_evento_conversao, gasto_ultimas_horas}]}
  POST /funil/raio-x   {"cliente_id", "leads": [LeadFunil], "investimento"?, "investimento_captacao"?, "gasto_por_codigo"?}
  POST /contas/saude   {"cliente_id", "contas": [{nome, id, status, saldo, gasto_7d, anuncios_com_problema…}],
                        "credencial_ok"?, "conferir_acesso"?}

Isolamento entre clientes em /conversao: cada cliente tem o próprio segredo de webhook
(KOMMO_WEBHOOK_TOKEN_<CLIENTE>), a conta Kommo do corpo precisa ser a do perfil, e a etapa
do lead é confirmada na leitura do Kommo — o webhook só diz qual lead olhar.
"""

from __future__ import annotations

import hmac
import json
import yaml
import os
import re
from dataclasses import asdict
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Callable
from wsgiref.simple_server import WSGIServer, make_server

from pydantic import ValidationError

from trilha import __version__
from trilha.conversao.pipeline import executar, processar
from trilha.core.economia import calcular
from trilha.core.freio import MetricaCampanha, avaliar
from trilha.core.correcoes import aplicar_correcoes, carregar_correcoes
from trilha.core.funil import LeadFunil, raio_x
from trilha.core.oferta import carregar_oferta
from trilha.core.playbook import carregar_playbook
from trilha.core.saude import ContaAnuncio, saude_do_cliente
from trilha.core.perfil import Perfil, carregar_perfil
from trilha.integracoes.kommo import DadosLead, KommoClient, subdominio_do_webhook

_CLIENTE_ID = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,63}$")

ObterDados = Callable[[Perfil, int], DadosLead]


class ErroHttp(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status


def _var_cliente(prefixo: str, cliente_id: str) -> str:
    return prefixo + cliente_id.upper().replace("-", "_")


def _kommo_padrao(perfil: Perfil, lead_id: int) -> DadosLead:
    var = _var_cliente("KOMMO_TOKEN_", perfil.cliente.id)
    token = os.environ.get(var)
    if not token:
        raise ErroHttp(500, f"variável {var} não configurada")
    return KommoClient(perfil.crm.subdominio, token).dados_lead(lead_id, perfil.crm.campos)


class TrilhaApi:
    def __init__(
        self,
        token: str | None = None,
        clientes_dir: str | Path | None = None,
        obter_dados: ObterDados = _kommo_padrao,
        envio_real_permitido: bool | None = None,
        segredos_webhook: dict[str, str] | None = None,
    ):
        self.token = token if token is not None else os.environ.get("TRILHA_API_TOKEN", "")
        self.clientes_dir = Path(clientes_dir or os.environ.get("TRILHA_CLIENTES_DIR", "clientes"))
        self.obter_dados = obter_dados
        self.segredos_webhook = segredos_webhook  # None = ler KOMMO_WEBHOOK_TOKEN_<CLIENTE> do ambiente
        # Envio real só quando o ambiente permite explicitamente; a requisição não pode forçar.
        self.envio_real_permitido = (
            envio_real_permitido if envio_real_permitido is not None else os.environ.get("TRILHA_SIMULAR", "1") == "0"
        )
        self.rotas = {
            ("GET", "/saude"): self.saude,
            ("GET", "/clientes"): self.clientes,
            ("POST", "/validar"): self.validar,
            ("POST", "/calcular"): self.calcular,
            ("POST", "/conversao"): self.conversao,
            ("POST", "/freio/avaliar"): self.freio,
            ("POST", "/funil/raio-x"): self.raio_x,
            ("POST", "/contas/saude"): self.saude_contas,
        }

    def __call__(self, environ, start_response):
        metodo, caminho = environ["REQUEST_METHOD"], environ.get("PATH_INFO", "/").rstrip("/") or "/"
        try:
            rota = self.rotas.get((metodo, caminho))
            if rota is None:
                raise ErroHttp(404, "rota inexistente")
            if caminho != "/saude":
                self._autenticar(environ)
            status, corpo = 200, rota(self._ler_json(environ) if metodo == "POST" else {})
        except ErroHttp as e:
            status, corpo = e.status, {"erro": str(e)}
        except ValidationError as e:
            status, corpo = 422, {"erro": "perfil inválido", "detalhes": json.loads(e.json())}
        except Exception as e:  # noqa: BLE001 — o n8n precisa de resposta, não de conexão caída
            status, corpo = 500, {"erro": f"{type(e).__name__}: {e}"}
        dados = json.dumps(corpo, ensure_ascii=False, default=str).encode("utf-8")
        frases = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 422: "Unprocessable Entity", 500: "Internal Server Error"}
        start_response(f"{status} {frases.get(status, 'Error')}", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(dados)))])
        return [dados]

    def _autenticar(self, environ):
        if not self.token:
            raise ErroHttp(500, "TRILHA_API_TOKEN não configurado")
        enviado = environ.get("HTTP_AUTHORIZATION", "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(enviado, self.token):
            raise ErroHttp(401, "token inválido")

    @staticmethod
    def _ler_json(environ) -> dict:
        tamanho = int(environ.get("CONTENT_LENGTH") or 0)
        bruto = environ["wsgi.input"].read(tamanho) if tamanho else b"{}"
        try:
            dados = json.loads(bruto or b"{}")
        except json.JSONDecodeError as e:
            raise ErroHttp(400, f"JSON inválido: {e}") from e
        if not isinstance(dados, dict):
            raise ErroHttp(400, "esperado um objeto JSON")
        return dados

    def _perfil(self, dados: dict, aceita_inline: bool = False) -> Perfil:
        if "perfil" in dados:
            if not aceita_inline:
                raise ErroHttp(400, "esta rota só aceita cliente_id (perfil carregado do repositório de clientes)")
            return Perfil.model_validate(dados["perfil"])
        cliente_id = str(dados.get("cliente_id", ""))
        if not _CLIENTE_ID.match(cliente_id):
            raise ErroHttp(400, "cliente_id ausente ou inválido")
        caminho = self.clientes_dir / cliente_id / "perfil.yaml"
        if not caminho.is_file():
            raise ErroHttp(404, f"perfil de '{cliente_id}' não encontrado")
        try:
            perfil = carregar_perfil(caminho)
        except yaml.YAMLError as e:
            raise ErroHttp(422, f"perfil de '{cliente_id}' com YAML inválido: {e}") from e
        if perfil.cliente.id != cliente_id:
            raise ErroHttp(422, f"cliente.id '{perfil.cliente.id}' diferente da pasta '{cliente_id}'")
        return perfil

    def _conferir_webhook(self, perfil: Perfil, dados: dict) -> None:
        cliente_id = perfil.cliente.id
        if self.segredos_webhook is not None:
            esperado = self.segredos_webhook.get(cliente_id, "")
        else:
            esperado = os.environ.get(_var_cliente("KOMMO_WEBHOOK_TOKEN_", cliente_id), "")
        if not esperado:
            raise ErroHttp(500, f"segredo de webhook de '{cliente_id}' não configurado")
        if not hmac.compare_digest(str(dados.get("webhook_token", "")), esperado):
            raise ErroHttp(403, "segredo de webhook inválido para este cliente")
        conta = subdominio_do_webhook(dados["corpo"])
        if conta is not None and conta != perfil.crm.subdominio:
            raise ErroHttp(403, f"webhook da conta Kommo '{conta}', esperado '{perfil.crm.subdominio}'")

    def saude(self, _dados):
        return {"ok": True, "versao": __version__, "envio_real_permitido": self.envio_real_permitido}

    def clientes(self, _dados):
        carteira, invalidos = [], []
        for caminho in sorted(self.clientes_dir.glob("*/perfil.yaml")):
            pasta = caminho.parent.name
            if pasta.startswith("_") or not _CLIENTE_ID.match(pasta):
                continue
            try:
                p = carregar_perfil(caminho)
                if p.cliente.id != pasta:
                    raise ValueError(f"cliente.id '{p.cliente.id}' diferente da pasta '{pasta}'")
            except (ValidationError, OSError, ValueError, yaml.YAMLError) as e:
                invalidos.append({"cliente_id": pasta, "erro": str(e).splitlines()[0]})
                continue
            carteira.append({
                "cliente_id": pasta, "nome": p.cliente.nome, "versao_perfil": p.versao,
                "operacao": p.operacao.model_dump() if p.operacao else None, "freio": p.freio.modo,
            })
        return {"clientes": carteira, "invalidos": invalidos}

    def validar(self, dados):
        p = self._perfil(dados, aceita_inline=True)
        ofertas = []
        if "cliente_id" in dados and "perfil" not in dados:
            exige = carregar_playbook(p.cliente.segmento).exige_na_aderencia()
            for arquivo in sorted((self.clientes_dir / p.cliente.id / "ofertas").glob("*.yaml")):
                try:
                    o = carregar_oferta(arquivo)
                except (ValidationError, yaml.YAMLError) as e:
                    raise ErroHttp(422, f"oferta {arquivo.name} inválida: {e}") from e
                ofertas.append({"oferta": o.oferta.nome, "aderencia_pendente": o.aderencia.pendencias(exige),
                                "sinais_de_risco": o.aderencia.sinais_de_risco()})
        return {"ok": True, "cliente": p.cliente.id, "versao": p.versao, "estimados": p.economia.estimados,
                "ofertas": ofertas}

    def calcular(self, dados):
        p = self._perfil(dados, aceita_inline=True)
        verba = float(dados.get("verba") or p.verba.mensal_planejada)
        r = calcular(p.economia, verba, p.conversao.eventos_semana_aprendizado)
        return {"cliente": p.cliente.id, "verba": verba, **asdict(r)}

    def conversao(self, dados):
        p = self._perfil(dados)
        if p.crm is None:
            raise ErroHttp(400, "perfil sem bloco crm")
        if "corpo" not in dados:
            raise ErroHttp(400, "campo 'corpo' (webhook do Kommo) ausente")
        self._conferir_webhook(p, dados)
        simular = bool(dados.get("simular", True)) or not self.envio_real_permitido
        envios = processar(dados["corpo"], p, lambda lead_id: self.obter_dados(p, lead_id))
        executar(envios, simular=simular)
        return {
            "cliente": p.cliente.id,
            "simulado": simular,
            "envios": [asdict(e) for e in envios],
            "resumo": {
                "enviados": sum(1 for e in envios if e.corpo and not e.pendente and not simular),
                "simulados": sum(1 for e in envios if e.corpo and simular),
                "pulados": [f"{e.plataforma}/{e.evento}: {e.pulado}" for e in envios if e.pulado],
                "pendentes": [f"{e.plataforma}/{e.evento}: {e.pendente}" for e in envios if e.pendente],
                "informativos": [f"{e.plataforma}/{e.evento}: {e.informativo}" for e in envios if e.informativo],
            },
        }

    def freio(self, dados):
        p = self._perfil(dados)
        try:
            campanhas = [MetricaCampanha.model_validate(c) for c in dados.get("campanhas", [])]
        except ValidationError as e:
            raise ErroHttp(400, f"métricas de campanha inválidas: {e.errors(include_url=False)}") from e
        return {"cliente": p.cliente.id, "modo": p.freio.modo, "acoes": [asdict(a) for a in avaliar(p, campanhas)]}

    def saude_contas(self, dados):
        p = self._perfil(dados)
        try:
            contas = [ContaAnuncio.model_validate(c) for c in dados.get("contas", [])]
        except ValidationError as e:
            raise ErroHttp(400, f"contas inválidas: {e.errors(include_url=False)}") from e
        responsavel = p.operacao.responsavel if p.operacao else "assessor"
        esperadas = p.plataformas.meta.contas() if p.plataformas.meta else []
        return {"cliente": p.cliente.id, **saude_do_cliente(
            contas, responsavel, os.environ.get("TRILHA_RESPONSAVEL_TECNICO", "responsável técnico"),
            contas_esperadas=esperadas if dados.get("conferir_acesso") else None,
            credencial_ok=dados.get("credencial_ok", True) is not False)}

    def raio_x(self, dados):
        p = self._perfil(dados)
        try:
            leads = [LeadFunil.model_validate(x) for x in dados.get("leads", [])]
        except ValidationError as e:
            raise ErroHttp(400, f"histórico de leads inválido: {e.errors(include_url=False)}") from e
        try:
            correcoes = carregar_correcoes(self.clientes_dir / p.cliente.id / "correcoes.yaml")
        except (ValidationError, yaml.YAMLError) as e:
            raise ErroHttp(422, f"correcoes.yaml de '{p.cliente.id}' inválido: {e}") from e
        leads = aplicar_correcoes(leads, correcoes)
        investimento, captacao = dados.get("investimento"), dados.get("investimento_captacao")
        gasto = dados.get("gasto_por_codigo")
        if gasto is not None and not (isinstance(gasto, dict) and all(isinstance(v, (int, float)) for v in gasto.values())):
            raise ErroHttp(400, "gasto_por_codigo precisa ser um objeto {código: gasto}")
        return {"cliente": p.cliente.id,
                **raio_x(leads, carregar_playbook(p.cliente.segmento), float(investimento) if investimento else None, crm=p.crm,
                         investimento_captacao=float(captacao) if captacao is not None else None,
                         gasto_por_codigo={str(k): float(v) for k, v in gasto.items()} if gasto else None)}


class _ServidorThreads(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def servir(host: str = "0.0.0.0", porta: int = 8080) -> None:
    with make_server(host, porta, TrilhaApi(), server_class=_ServidorThreads) as srv:
        print(f"trilha-api {__version__} em http://{host}:{porta}")
        srv.serve_forever()
