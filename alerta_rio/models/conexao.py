"""
Conexão com o MySQL, sem ORM.

Todas as consultas passam por aqui e SEMPRE usam parâmetros (%s).
Nunca montamos SQL juntando texto com f-string ou "+", porque é
exatamente assim que nasce uma SQL Injection.
"""

import logging
from contextlib import contextmanager

import mysql.connector
from mysql.connector import errorcode, pooling

from .. import config
from ..core.log import registrar


class ErroBanco(Exception):
    """Falha ao falar com o banco. A mensagem é genérica de propósito."""


class RegistroDuplicado(ErroBanco):
    """Tentativa de cadastrar algo que já existe (ex.: código de sensor repetido)."""


class RegraViolada(ErroBanco):
    """O banco recusou os dados por uma regra (CHECK), ex.: ocupação maior que a capacidade."""


_pool = None


def _obter_pool() -> pooling.MySQLConnectionPool:
    """Cria o pool de conexões na primeira vez que alguém precisa do banco."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="alerta_rio",
            pool_size=5,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            connection_timeout=5,
            autocommit=False,
        )
    return _pool


@contextmanager
def conexao():
    """
    Entrega uma conexão pronta e cuida do resto:
    confirma (commit) se deu tudo certo, desfaz (rollback) se deu erro
    e devolve a conexão ao pool no final.
    """
    con = None
    try:
        con = _obter_pool().get_connection()
        yield con
        con.commit()
    except mysql.connector.Error as erro:
        if con is not None:
            con.rollback()
        # O detalhe técnico vai só para o log interno, nunca para o usuário
        registrar("DB", "ERRO_BANCO", "FALHA", f"errno={getattr(erro, 'errno', '?')}", logging.ERROR)
        if getattr(erro, "errno", None) == errorcode.ER_DUP_ENTRY:
            raise RegistroDuplicado("Registro duplicado.") from erro
        if getattr(erro, "errno", None) == 3819:  # ER_CHECK_CONSTRAINT_VIOLATED
            raise RegraViolada("Dados não respeitam as regras do cadastro.") from erro
        raise ErroBanco("Não foi possível acessar o banco de dados.") from erro
    except Exception:
        if con is not None:
            con.rollback()
        raise
    finally:
        if con is not None:
            con.close()


def consultar(sql: str, parametros: tuple = ()) -> list[dict]:
    """Executa um SELECT e devolve uma lista de dicionários."""
    with conexao() as con:
        cursor = con.cursor(dictionary=True)
        cursor.execute(sql, parametros)
        linhas = cursor.fetchall()
        cursor.close()
        return linhas


def consultar_um(sql: str, parametros: tuple = ()) -> dict | None:
    """Executa um SELECT que deve trazer no máximo uma linha."""
    linhas = consultar(sql, parametros)
    return linhas[0] if linhas else None


def executar(sql: str, parametros: tuple = ()) -> tuple[int, int]:
    """
    Executa INSERT, UPDATE ou DELETE.
    Devolve (linhas_afetadas, id_gerado).
    """
    with conexao() as con:
        cursor = con.cursor()
        cursor.execute(sql, parametros)
        resultado = (cursor.rowcount, cursor.lastrowid)
        cursor.close()
        return resultado


def banco_disponivel() -> bool:
    """Teste rápido de saúde do banco (usado no /api/status)."""
    try:
        consultar("SELECT 1 AS ok")
        return True
    except ErroBanco:
        return False
