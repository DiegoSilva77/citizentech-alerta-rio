"""
Log de auditoria em arquivo.

Cada linha registra: data e hora, origem, ação e resultado.
Exemplo:
    2026-11-09 16:20:01 | INFO  | API    | CRIAR_SENSOR        | SUCESSO | id=6

Cuidado com a LGPD: aqui NUNCA entram senhas, chaves ou dados pessoais.
Nem o IP de quem acessa a gente guarda, porque não precisamos dele.
"""

import logging
from logging.handlers import RotatingFileHandler

from .. import config

_logger = None


def obter_logger() -> logging.Logger:
    """Cria o logger uma vez só e reaproveita nas chamadas seguintes."""
    global _logger
    if _logger is not None:
        return _logger

    config.LOG_ARQUIVO.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("alerta_rio")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Arquivo com rotação: quando passa de 1 MB, guarda até 5 arquivos antigos
    arquivo = RotatingFileHandler(
        config.LOG_ARQUIVO, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    arquivo.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(arquivo)

    _logger = logger
    return logger


def registrar(origem: str, acao: str, resultado: str, detalhe: str = "", nivel: int = logging.INFO) -> None:
    """
    Escreve uma linha de auditoria.

    origem    -> quem gerou o evento (API, UDP, CLIMA, SETUP...)
    acao      -> o que foi tentado (CRIAR_SENSOR, LEITURA_RECEBIDA...)
    resultado -> SUCESSO, FALHA, NEGADO, INVALIDO...
    detalhe   -> informação curta e segura (ids, códigos), nunca dados sensíveis
    """
    # Tira quebras de linha para ninguém conseguir "forjar" linhas falsas no log
    detalhe_limpo = str(detalhe).replace("\n", " ").replace("\r", " ")[:300]
    obter_logger().log(nivel, f"{origem:<6} | {acao:<22} | {resultado:<8} | {detalhe_limpo}")
