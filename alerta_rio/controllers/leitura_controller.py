"""
Controller de LEITURAS: decide o que fazer com cada pacote que chega
dos sensores pelo socket UDP.

O servidor UDP (sockets_udp/servidor_udp.py) só cuida da rede: recebe
os bytes e devolve o ACK. Toda a decisão fica aqui:
  1. tamanho e formato do pacote
  2. assinatura HMAC (veio mesmo de um sensor nosso?)
  3. horário e repetição (anti-replay)
  4. sensor cadastrado e ativo?
  5. grava a leitura (model) e recalcula o risco
  6. se o risco mudou, grava um alerta novo (model)
"""

import json
import logging

from ..core.log import registrar
from ..core.seguranca import GuardaReplay, assinatura_valida
from ..core.validacao import ErroValidacao, validar_pacote_sensor
from ..models import alerta as alerta_model
from ..models import leitura as leitura_model
from ..models import sensor as sensor_model
from ..models.clima import chuva_prevista_6h
from ..models.risco import calcular_risco, mensagem_alerta

TAMANHO_MAXIMO = 1024  # uma leitura legítima tem menos de 200 bytes


def _recusar(motivo_ack: str, motivo_log: str, resultado: str = "INVALIDO", nivel=logging.INFO) -> dict:
    registrar("UDP", "LEITURA_RECEBIDA", resultado, motivo_log, nivel)
    return {"status": "recusado", "motivo": motivo_ack, "detalhe": motivo_log}


def processar_pacote(dados: bytes, guarda: GuardaReplay) -> dict:
    """
    Trata um pacote e devolve um dicionário com o resultado:
      status       -> 'ok' ou 'recusado'
      motivo       -> texto curto que vai no ACK (sem detalhes internos)
      codigo/nivel_cm/risco/novo_alerta -> usados para mostrar no terminal
    """
    if len(dados) > TAMANHO_MAXIMO:
        return _recusar("pacote inválido", "pacote grande demais")

    # Formato e campos
    try:
        pacote = validar_pacote_sensor(json.loads(dados.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, ErroValidacao):
        return _recusar("pacote inválido", "formato incorreto")

    codigo = pacote["codigo"]

    # Assinatura
    if not assinatura_valida(codigo, pacote["nivel_cm"], pacote["ts"], pacote["assinatura"]):
        return _recusar("não autorizado", f"assinatura inválida codigo={codigo}", "NEGADO", logging.WARNING)

    # Anti-replay
    if not guarda.aceitar(pacote["ts"], pacote["assinatura"]):
        return _recusar("pacote expirado", f"replay/fora da janela codigo={codigo}", "NEGADO", logging.WARNING)

    # Sensor existe e está ativo?
    sensor = sensor_model.buscar_por_codigo(codigo)
    if sensor is None or not sensor["ativo"]:
        return _recusar("sensor não cadastrado", f"sensor desconhecido/inativo codigo={codigo}", "NEGADO")

    leitura_model.registrar(sensor["id"], pacote["nivel_cm"])

    # Risco atual x último alerta registrado
    risco = calcular_risco(pacote["nivel_cm"], sensor["nivel_alerta_cm"],
                           sensor["nivel_critico_cm"], chuva_prevista_6h())
    novo_alerta = None
    ultimo = alerta_model.ultimo_do_sensor(sensor["id"])
    if ultimo is None or ultimo["nivel_risco"] != risco:
        novo_alerta = mensagem_alerta(risco, sensor["nome"], pacote["nivel_cm"], sensor["nivel_critico_cm"])
        alerta_model.criar(sensor["id"], risco, pacote["nivel_cm"], novo_alerta)
        registrar("UDP", "NOVO_ALERTA", risco.upper(), f"codigo={codigo} nivel={pacote['nivel_cm']}")

    registrar("UDP", "LEITURA_RECEBIDA", "SUCESSO", f"codigo={codigo} nivel={pacote['nivel_cm']}")
    return {
        "status": "ok", "motivo": "", "codigo": codigo,
        "nivel_cm": pacote["nivel_cm"], "risco": risco, "novo_alerta": novo_alerta,
    }
