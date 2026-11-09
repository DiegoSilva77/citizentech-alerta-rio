"""
Controller de ABRIGOS: CRUD completo em /api/abrigos.

    GET    /api/abrigos         -> lista (use ?ativos=1 para só os ativos)
    GET    /api/abrigos/<id>    -> detalhe            (200 / 404)
    POST   /api/abrigos         -> cadastra   [chave] (201 / 400 / 401 / 415)
    PUT    /api/abrigos/<id>    -> atualiza   [chave] (200 / 400 / 401 / 404)
    DELETE /api/abrigos/<id>    -> exclui     [chave] (204 / 401 / 404)
"""

from flask import Blueprint, abort, request, url_for

from ..core.extensoes import LIMITE_ESCRITA, limiter
from ..core.log import registrar
from ..core.seguranca import requer_operador
from ..core.validacao import validar_abrigo
from ..models import abrigo as abrigo_model
from ..views import json_view
from .base import ler_corpo_json

abrigo_bp = Blueprint("abrigos", __name__, url_prefix="/api/abrigos")


@abrigo_bp.get("")
def listar():
    return json_view.sucesso(abrigo_model.listar(request.args.get("ativos") == "1"))


@abrigo_bp.get("/<int:abrigo_id>")
def obter(abrigo_id):
    abrigo = abrigo_model.buscar(abrigo_id)
    if abrigo is None:
        abort(404)
    return json_view.sucesso(abrigo)


@abrigo_bp.post("")
@requer_operador
@limiter.limit(LIMITE_ESCRITA)
def criar():
    dados = validar_abrigo(ler_corpo_json())
    novo_id = abrigo_model.criar(dados)
    registrar("API", "CRIAR_ABRIGO", "SUCESSO", f"id={novo_id}")
    return json_view.criado(abrigo_model.buscar(novo_id), url_for("abrigos.obter", abrigo_id=novo_id))


@abrigo_bp.put("/<int:abrigo_id>")
@requer_operador
@limiter.limit(LIMITE_ESCRITA)
def atualizar(abrigo_id):
    dados = validar_abrigo(ler_corpo_json())
    if not abrigo_model.atualizar(abrigo_id, dados):
        abort(404)
    registrar("API", "ATUALIZAR_ABRIGO", "SUCESSO", f"id={abrigo_id} ocupacao={dados['ocupacao']}")
    return json_view.sucesso(abrigo_model.buscar(abrigo_id))


@abrigo_bp.delete("/<int:abrigo_id>")
@requer_operador
@limiter.limit(LIMITE_ESCRITA)
def excluir(abrigo_id):
    if not abrigo_model.excluir(abrigo_id):
        abort(404)
    registrar("API", "EXCLUIR_ABRIGO", "SUCESSO", f"id={abrigo_id}")
    return json_view.sem_conteudo()
