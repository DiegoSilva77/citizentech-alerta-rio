"""
Controller de ERROS: o que a API responde quando algo dá errado.

Regra de segurança: o usuário recebe sempre uma mensagem amigável e
genérica. O detalhe técnico (tipo do erro, código do MySQL) vai só
para o arquivo de log, nunca para a tela. Traceback, caminho de
arquivo e versão de biblioteca são presentes para um atacante.
"""

import logging

from werkzeug.exceptions import HTTPException

from ..core.log import registrar
from ..core.validacao import ErroValidacao
from ..models.conexao import ErroBanco, RegraViolada
from ..views import json_view

MENSAGENS = {
    400: "Requisição inválida.",
    401: "Acesso não autorizado. Informe a chave de operador.",
    404: "Recurso não encontrado.",
    405: "Método não permitido para este endereço.",
    413: "Conteúdo grande demais.",
    415: "Envie os dados no formato JSON (Content-Type: application/json).",
    429: "Muitas requisições em pouco tempo. Aguarde um instante.",
}


def registrar_tratadores(app) -> None:
    """Liga cada tipo de erro à resposta certa."""

    @app.errorhandler(ErroValidacao)
    def dados_invalidos(erro):
        return json_view.erro("Dados inválidos.", 400, erro.erros)

    @app.errorhandler(RegraViolada)
    def regra_violada(_erro):
        return json_view.erro("Os dados não respeitam as regras do cadastro.", 400)

    @app.errorhandler(ErroBanco)
    def banco_fora(_erro):
        # O detalhe já foi para o log dentro de models/conexao.py
        return json_view.erro("Serviço temporariamente indisponível. Tente novamente em instantes.", 503)

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        return json_view.erro(MENSAGENS.get(erro.code, "Não foi possível concluir a requisição."), erro.code)

    @app.errorhandler(Exception)
    def erro_inesperado(erro):
        registrar("API", "ERRO_INESPERADO", "FALHA", type(erro).__name__, logging.ERROR)
        return json_view.erro("Erro interno. A equipe já foi avisada pelo log.", 500)
