"""
Model de ALERTA: guarda cada vez que o risco de um ponto muda
(normal -> atenção -> perigo, e a volta ao normal).
"""

from .conexao import consultar, consultar_um, executar


def ultimo_do_sensor(sensor_id: int) -> dict | None:
    return consultar_um(
        "SELECT id, nivel_risco, criado_em FROM alertas WHERE sensor_id = %s ORDER BY id DESC LIMIT 1",
        (sensor_id,),
    )


def criar(sensor_id: int, nivel_risco: str, nivel_cm: float, mensagem: str) -> int:
    _, novo_id = executar(
        "INSERT INTO alertas (sensor_id, nivel_risco, nivel_cm, mensagem) VALUES (%s, %s, %s, %s)",
        (sensor_id, nivel_risco, nivel_cm, mensagem),
    )
    return novo_id


def listar(limite: int = 20) -> list[dict]:
    return consultar(
        """SELECT a.id, a.nivel_risco, a.nivel_cm, a.mensagem, a.criado_em,
                  s.codigo AS sensor_codigo, s.bairro
             FROM alertas a JOIN sensores s ON s.id = a.sensor_id
            ORDER BY a.id DESC
            LIMIT %s""",
        (limite,),
    )
