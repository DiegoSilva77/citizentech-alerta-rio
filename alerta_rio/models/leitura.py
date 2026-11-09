"""
Model de LEITURA: cada medição de nível que chega dos sensores pelo socket UDP.
"""

from .conexao import consultar, executar


def registrar(sensor_id: int, nivel_cm: float) -> int:
    _, novo_id = executar(
        "INSERT INTO leituras (sensor_id, nivel_cm) VALUES (%s, %s)", (sensor_id, nivel_cm)
    )
    return novo_id


def listar(sensor_id: int, limite: int = 40) -> list[dict]:
    """Últimas leituras de um sensor, da mais antiga para a mais nova (bom para gráfico)."""
    linhas = consultar(
        """SELECT nivel_cm, registrado_em FROM leituras
            WHERE sensor_id = %s
            ORDER BY registrado_em DESC, id DESC
            LIMIT %s""",
        (sensor_id, limite),
    )
    return list(reversed(linhas))


def niveis_recentes(sensor_id: int, quantidade: int = 8) -> list[float]:
    """Usado para calcular a tendência (mais novo primeiro)."""
    linhas = consultar(
        "SELECT nivel_cm FROM leituras WHERE sensor_id = %s ORDER BY registrado_em DESC, id DESC LIMIT %s",
        (sensor_id, quantidade),
    )
    return [float(l["nivel_cm"]) for l in linhas]
