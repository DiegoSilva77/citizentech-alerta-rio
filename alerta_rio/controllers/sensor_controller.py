"""
Controller de SENSORES: CRUD completo em /api/sensores.

    GET    /api/sensores                 -> lista (use ?ativos=1 para só os ativos)
    GET    /api/sensores/<id>            -> detalhe            (200 / 404)
    POST   /api/sensores                 -> cadastra   [chave] (201 / 400 / 401 / 409 / 415)
    PUT    /api/sensores/<id>            -> atualiza   [chave] (200 / 400 / 401 / 404 / 409)
    DELETE /api/sensores/<id>            -> exclui     [chave] (204 / 401 / 404)
    GET    /api/sensores/<id>/leituras   -> histórico de nível (200 / 400 / 404)
"""

from flask import Blueprint, abort, request, url_for

from ..core.extensoes import LIMITE_ESCRITA, limiter
from ..core.log import registrar
from ..core.seguranca import requer_operador
from ..core.validacao import validar_limite, validar_sensor
from ..models import leitura as leitura_model
from ..models import sensor as sensor_model
from ..models.conexao import RegistroDuplicado
from ..views import json_view
from .base import ler_corpo_json

sensor_bp = Blueprint("sensores", __name__, url_prefix="/api/sensores")


@sensor_bp.get("")
def listar():
    return json_view.sucesso(sensor_model.listar(request.args.get("ativos") == "1"))


@sensor_bp.get("/<int:sensor_id>")
def obter(sensor_id):
    sensor = sensor_model.buscar(sensor_id)
    if sensor is None:
        abort(404)
    return json_view.sucesso(sensor)


@sensor_bp.post("")
@requer_operador
@limiter.limit(LIMITE_ESCRITA)
def criar():
    dados = validar_sensor(ler_corpo_json())
    try:
        novo_id = sensor_model.criar(dados)
    except RegistroDuplicado:
        registrar("API", "CRIAR_SENSOR", "CONFLITO", f"codigo={dados['codigo']}")
        return json_view.erro("Já existe um sensor com esse código.", 409)
    registrar("API", "CRIAR_SENSOR", "SUCESSO", f"id={novo_id} codigo={dados['codigo']}")
    return json_view.criado(sensor_model.buscar(novo_id), url_for("sensores.obter", sensor_id=novo_id))


@sensor_bp.put("/<int:sensor_id>")
@requer_operador
@limiter.limit(LIMITE_ESCRITA)
def atualizar(sensor_id):
    dados = validar_sensor(ler_corpo_json())
    try:
        existe = sensor_model.atualizar(sensor_id, dados)
    except RegistroDuplicado:
        return json_view.erro("Já existe outro sensor com esse código.", 409)
    if not existe:
        abort(404)
    registrar("API", "ATUALIZAR_SENSOR", "SUCESSO", f"id={sensor_id}")
    return json_view.sucesso(sensor_model.buscar(sensor_id))


@sensor_bp.delete("/<int:sensor_id>")
@requer_operador
@limiter.limit(LIMITE_ESCRITA)
def excluir(sensor_id):
    if not sensor_model.excluir(sensor_id):
        abort(404)
    registrar("API", "EXCLUIR_SENSOR", "SUCESSO", f"id={sensor_id}")
    return json_view.sem_conteudo()


@sensor_bp.get("/<int:sensor_id>/leituras")
def leituras(sensor_id):
    if sensor_model.buscar(sensor_id) is None:
        abort(404)
    limite = validar_limite(request.args.get("limite"), padrao=40)
    return json_view.sucesso(leitura_model.listar(sensor_id, limite))
