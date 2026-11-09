"""
View JSON: o "rosto" da API.

Toda resposta da API sai por aqui. Assim o formato fica igual em todo
lugar, e os tipos do MySQL (Decimal, datetime, 0/1) viram tipos que o
JSON entende (número, texto de data, true/false).
"""

from datetime import date, datetime
from decimal import Decimal

from flask import jsonify

# Colunas TINYINT(1) do MySQL que, para quem usa a API, são verdadeiro/falso
CAMPOS_BOOLEANOS = {"ativo", "aceita_pets", "acessivel"}


def serializar(dados):
    """Converte recursivamente listas e dicionários vindos das models."""
    if isinstance(dados, list):
        return [serializar(item) for item in dados]
    if isinstance(dados, dict):
        return {
            chave: bool(valor) if chave in CAMPOS_BOOLEANOS and valor is not None else serializar(valor)
            for chave, valor in dados.items()
        }
    if isinstance(dados, Decimal):
        return float(dados)
    if isinstance(dados, (datetime, date)):
        return dados.isoformat(timespec="seconds") if isinstance(dados, datetime) else dados.isoformat()
    return dados


def sucesso(dados, status: int = 200):
    """200 OK (ou outro status de sucesso) com os dados em JSON."""
    return jsonify(serializar(dados)), status


def criado(dados, location: str):
    """201 Created + cabeçalho Location apontando para o novo recurso."""
    resposta = jsonify(serializar(dados))
    resposta.headers["Location"] = location
    return resposta, 201


def sem_conteudo():
    """204 No Content: usado depois de excluir algo."""
    return "", 204


def erro(mensagem: str, status: int, campos: dict | None = None):
    """
    Resposta de erro padronizada.
    A mensagem é sempre amigável e genérica, nunca um detalhe interno do sistema.
    """
    corpo = {"erro": mensagem}
    if campos:
        corpo["campos"] = campos
    return jsonify(corpo), status
