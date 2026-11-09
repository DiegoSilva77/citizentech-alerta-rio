"""Pequenas ajudas usadas por mais de um controller."""

from flask import abort, request

from ..core.validacao import ErroValidacao


def ler_corpo_json() -> dict:
    """Garante que a requisição trouxe JSON de verdade (senão: 415 ou 400)."""
    if not request.is_json:
        abort(415)
    dados = request.get_json(silent=True)
    if dados is None:
        raise ErroValidacao({"corpo": "JSON mal formado."})
    return dados
