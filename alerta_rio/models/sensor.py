"""
Model de SENSOR: os pontos de medição do nível do rio.

Todas as consultas usam parâmetros (%s). Nenhum valor que vem de fora
é colado dentro do SQL, e é isso que impede a SQL Injection.
"""

from . import leitura, risco
from .conexao import consultar, consultar_um, executar

# Traz o sensor junto com a leitura mais recente dele (subconsultas)
SQL_BASE = """
    SELECT s.id, s.codigo, s.nome, s.bairro, s.latitude, s.longitude,
           s.nivel_alerta_cm, s.nivel_critico_cm, s.ativo, s.criado_em, s.atualizado_em,
           (SELECT l.nivel_cm FROM leituras l WHERE l.sensor_id = s.id
             ORDER BY l.registrado_em DESC, l.id DESC LIMIT 1) AS ultimo_nivel_cm,
           (SELECT l.registrado_em FROM leituras l WHERE l.sensor_id = s.id
             ORDER BY l.registrado_em DESC, l.id DESC LIMIT 1) AS ultima_leitura_em
    FROM sensores s
"""


def listar(somente_ativos: bool = False) -> list[dict]:
    sql = SQL_BASE + (" WHERE s.ativo = 1" if somente_ativos else "") + " ORDER BY s.codigo"
    return consultar(sql)


def buscar(sensor_id: int) -> dict | None:
    return consultar_um(SQL_BASE + " WHERE s.id = %s", (sensor_id,))


def buscar_por_codigo(codigo: str) -> dict | None:
    return consultar_um(SQL_BASE + " WHERE s.codigo = %s", (codigo,))


def criar(d: dict) -> int:
    _, novo_id = executar(
        """INSERT INTO sensores (codigo, nome, bairro, latitude, longitude,
                                 nivel_alerta_cm, nivel_critico_cm, ativo)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (d["codigo"], d["nome"], d["bairro"], d["latitude"], d["longitude"],
         d["nivel_alerta_cm"], d["nivel_critico_cm"], d["ativo"]),
    )
    return novo_id


def atualizar(sensor_id: int, d: dict) -> bool:
    """Atualiza todos os campos (semântica de PUT). Devolve False se o id não existir."""
    if buscar(sensor_id) is None:
        return False
    executar(
        """UPDATE sensores
              SET codigo = %s, nome = %s, bairro = %s, latitude = %s, longitude = %s,
                  nivel_alerta_cm = %s, nivel_critico_cm = %s, ativo = %s
            WHERE id = %s""",
        (d["codigo"], d["nome"], d["bairro"], d["latitude"], d["longitude"],
         d["nivel_alerta_cm"], d["nivel_critico_cm"], d["ativo"], sensor_id),
    )
    return True


def excluir(sensor_id: int) -> bool:
    """As leituras e alertas do sensor somem junto (ON DELETE CASCADE)."""
    linhas, _ = executar("DELETE FROM sensores WHERE id = %s", (sensor_id,))
    return linhas > 0


def listar_com_risco(chuva_6h_mm: float) -> list[dict]:
    """
    Sensores ativos já com o risco e a tendência calculados.
    Aqui a model junta os dados do banco com a regra de negócio (risco.py).
    """
    sensores = listar(somente_ativos=True)
    for s in sensores:
        s["risco"] = risco.calcular_risco(
            s["ultimo_nivel_cm"], s["nivel_alerta_cm"], s["nivel_critico_cm"], chuva_6h_mm
        )
        s["tendencia"] = risco.calcular_tendencia(leitura.niveis_recentes(s["id"]))
    return sensores
