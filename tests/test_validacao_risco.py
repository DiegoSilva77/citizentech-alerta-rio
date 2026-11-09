"""Testes da validação de entrada, do cálculo de risco e da assinatura dos sensores."""

import time

import pytest

from alerta_rio.core.seguranca import GuardaReplay, assinar_leitura, assinatura_valida
from alerta_rio.core.validacao import ErroValidacao, validar_abrigo, validar_pacote_sensor, validar_sensor
from alerta_rio.models.risco import calcular_risco, calcular_tendencia, pior_risco

SENSOR_OK = {
    "codigo": "dl-05", "nome": "Arroio Dilúvio", "bairro": "Azenha",
    "latitude": -30.05, "longitude": -51.21, "nivel_alerta_cm": 200, "nivel_critico_cm": 300,
}


# ---------------- Validação ----------------

def test_sensor_valido_normaliza_codigo():
    assert validar_sensor(SENSOR_OK)["codigo"] == "DL-05"


@pytest.mark.parametrize("campo, valor", [
    ("nome", "<script>alert(1)</script>"),   # tentativa de XSS
    ("nome", "x"),                           # curto demais
    ("bairro", "'; DROP TABLE sensores; --"), # tentativa de SQL injection
    ("latitude", 48.85),                     # Paris, fora do Brasil
    ("nivel_alerta_cm", True),               # booleano disfarçado de número
    ("codigo", "123"),                       # formato errado
])
def test_sensor_recusa_entradas_maliciosas_ou_erradas(campo, valor):
    with pytest.raises(ErroValidacao) as erro:
        validar_sensor({**SENSOR_OK, campo: valor})
    assert campo in erro.value.erros


def test_sensor_recusa_campo_extra():
    with pytest.raises(ErroValidacao) as erro:
        validar_sensor({**SENSOR_OK, "id": 99})
    assert "campos_desconhecidos" in erro.value.erros


def test_nivel_critico_precisa_ser_maior_que_alerta():
    with pytest.raises(ErroValidacao):
        validar_sensor({**SENSOR_OK, "nivel_critico_cm": 150})


def test_abrigo_nao_aceita_ocupacao_maior_que_capacidade():
    abrigo = {"nome": "Ginásio", "endereco": "Rua A, 10", "bairro": "Centro",
              "latitude": -30.0, "longitude": -51.2, "capacidade": 10, "ocupacao": 11}
    with pytest.raises(ErroValidacao):
        validar_abrigo(abrigo)


def test_corpo_que_nao_e_objeto():
    with pytest.raises(ErroValidacao):
        validar_sensor(["lista", "não", "vale"])


# ---------------- Risco ----------------

@pytest.mark.parametrize("nivel, chuva, esperado", [
    (100, 0, "normal"),
    (210, 0, "atencao"),
    (210, 15, "perigo"),   # em alerta + chuva forte = perigo
    (150, 30, "atencao"),  # perto do alerta + muita chuva = atenção
    (310, 0, "perigo"),
    (None, 0, "normal"),
])
def test_calculo_de_risco(nivel, chuva, esperado):
    assert calcular_risco(nivel, 200, 300, chuva) == esperado


def test_tendencia():
    assert calcular_tendencia([130, 128, 120, 110]) == "subindo"
    assert calcular_tendencia([100, 105, 120, 125]) == "descendo"
    assert calcular_tendencia([100, 101, 100, 99]) == "estavel"


def test_pior_risco():
    assert pior_risco(["normal", "perigo", "atencao"]) == "perigo"
    assert pior_risco([]) == "normal"


# ---------------- Assinatura e anti-replay (socket) ----------------

def test_assinatura_valida_e_adulterada():
    ts = int(time.time())
    assinatura = assinar_leitura("DL-01", 150.0, ts)
    assert assinatura_valida("DL-01", 150.0, ts, assinatura)
    assert not assinatura_valida("DL-01", 999.0, ts, assinatura)  # nível trocado no caminho


def test_guarda_replay_recusa_repetido_e_antigo():
    guarda = GuardaReplay(janela_s=30)
    agora = int(time.time())
    assert guarda.aceitar(agora, "a" * 64)
    assert not guarda.aceitar(agora, "a" * 64)          # mesmo pacote de novo
    assert not guarda.aceitar(agora - 120, "b" * 64)    # pacote velho


def test_pacote_udp_mal_formado():
    with pytest.raises(ErroValidacao):
        validar_pacote_sensor({"codigo": "DL-01", "nivel_cm": "alto", "ts": 1, "assinatura": "x"})
