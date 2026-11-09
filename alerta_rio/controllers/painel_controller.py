"""
Controller do PAINEL: a página principal e as rotas de consulta geral.

    GET /                        -> página HTML do painel
    GET /api/status              -> API e banco estão de pé?
    GET /api/resumo              -> tudo que o painel precisa numa chamada só
    GET /api/clima               -> previsão da Open-Meteo
    GET /api/alertas             -> linha do tempo de alertas
    GET /api/operador/verificar  -> confere a chave de operador (tela de Gestão)
"""

from flask import Blueprint, request

from ..core.extensoes import limiter
from ..core.log import registrar
from ..core.seguranca import requer_operador
from ..core.validacao import validar_limite
from ..models import abrigo as abrigo_model
from ..models import alerta as alerta_model
from ..models import clima as clima_model
from ..models import sensor as sensor_model
from ..models.conexao import banco_disponivel
from ..models.risco import pior_risco
from ..views import json_view, pagina_view

painel_bp = Blueprint("painel", __name__)


@painel_bp.get("/")
def pagina_inicial():
    return pagina_view.renderizar_painel()


@painel_bp.get("/api/status")
def status():
    banco_ok = banco_disponivel()
    return json_view.sucesso(
        {"api": "ok", "banco": "ok" if banco_ok else "indisponivel"},
        200 if banco_ok else 503,
    )


@painel_bp.get("/api/resumo")
def resumo():
    # Sem previsão do tempo o painel continua funcionando: o rio é quem manda
    try:
        chuva_6h = clima_model.obter_previsao()["chuva_6h_mm"]
        clima_ok = True
    except clima_model.ClimaIndisponivel:
        chuva_6h, clima_ok = 0.0, False

    sensores = sensor_model.listar_com_risco(chuva_6h)
    abrigos = abrigo_model.listar(somente_ativos=True)

    return json_view.sucesso({
        "risco_geral": pior_risco([s["risco"] for s in sensores]),
        "sensores": sensores,
        "totais": {
            "sensores_ativos": len(sensores),
            "em_atencao": sum(1 for s in sensores if s["risco"] == "atencao"),
            "em_perigo": sum(1 for s in sensores if s["risco"] == "perigo"),
            "abrigos": len(abrigos),
            "vagas_livres": abrigo_model.vagas_livres(abrigos),
        },
        "clima_disponivel": clima_ok,
        "chuva_6h_mm": chuva_6h,
    })


@painel_bp.get("/api/clima")
def clima():
    try:
        return json_view.sucesso(clima_model.obter_previsao())
    except clima_model.ClimaIndisponivel:
        return json_view.erro("Previsão do tempo indisponível no momento. Tente novamente em instantes.", 503)


@painel_bp.get("/api/alertas")
def alertas():
    limite = validar_limite(request.args.get("limite"), padrao=20, maximo=100)
    return json_view.sucesso(alerta_model.listar(limite))


@painel_bp.get("/api/operador/verificar")
@requer_operador
@limiter.limit("10 per minute")  # dificulta ficar "chutando" chaves
def verificar_operador():
    registrar("API", "LOGIN_OPERADOR", "SUCESSO", "")
    return json_view.sucesso({"operador": True})
