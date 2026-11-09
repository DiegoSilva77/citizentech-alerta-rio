"""
Model de ABRIGO: locais seguros para onde as famílias podem ir.
Guarda também se o abrigo aceita animais e se é acessível, porque
na prática muita gente só sai de casa se puder levar o bicho junto.
"""

from .conexao import consultar, consultar_um, executar

SQL_BASE = """
    SELECT id, nome, endereco, bairro, latitude, longitude, capacidade, ocupacao,
           aceita_pets, acessivel, ativo, criado_em, atualizado_em
      FROM abrigos
"""


def listar(somente_ativos: bool = False) -> list[dict]:
    sql = SQL_BASE + (" WHERE ativo = 1" if somente_ativos else "") + " ORDER BY nome"
    return consultar(sql)


def buscar(abrigo_id: int) -> dict | None:
    return consultar_um(SQL_BASE + " WHERE id = %s", (abrigo_id,))


def criar(d: dict) -> int:
    _, novo_id = executar(
        """INSERT INTO abrigos (nome, endereco, bairro, latitude, longitude, capacidade,
                                ocupacao, aceita_pets, acessivel, ativo)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (d["nome"], d["endereco"], d["bairro"], d["latitude"], d["longitude"], d["capacidade"],
         d["ocupacao"], d["aceita_pets"], d["acessivel"], d["ativo"]),
    )
    return novo_id


def atualizar(abrigo_id: int, d: dict) -> bool:
    if buscar(abrigo_id) is None:
        return False
    executar(
        """UPDATE abrigos
              SET nome = %s, endereco = %s, bairro = %s, latitude = %s, longitude = %s,
                  capacidade = %s, ocupacao = %s, aceita_pets = %s, acessivel = %s, ativo = %s
            WHERE id = %s""",
        (d["nome"], d["endereco"], d["bairro"], d["latitude"], d["longitude"], d["capacidade"],
         d["ocupacao"], d["aceita_pets"], d["acessivel"], d["ativo"], abrigo_id),
    )
    return True


def excluir(abrigo_id: int) -> bool:
    linhas, _ = executar("DELETE FROM abrigos WHERE id = %s", (abrigo_id,))
    return linhas > 0


def vagas_livres(abrigos: list[dict]) -> int:
    """Soma das vagas livres de uma lista de abrigos."""
    return sum(int(a["capacidade"]) - int(a["ocupacao"]) for a in abrigos)
