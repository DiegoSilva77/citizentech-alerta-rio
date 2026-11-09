"""
Configuração dos testes.

Os testes NÃO precisam do MySQL rodando: trocamos as funções do
repositório por versões falsas (monkeypatch). Assim dá para testar
a API, a validação e a segurança em qualquer máquina.
"""

import os
import sys
from pathlib import Path

# Valores fixos só para teste (nunca usados em produção)
os.environ.setdefault("DB_PASSWORD", "senha-de-teste")
os.environ["API_KEY_OPERADOR"] = "chave-de-teste-1234567890"
os.environ["SENSOR_HMAC_SECRET"] = "segredo-de-teste-1234567890"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from alerta_rio import config  # noqa: E402

# Garante que o config use os valores de teste mesmo que exista um .env
config.API_KEY_OPERADOR = os.environ["API_KEY_OPERADOR"]
config.SENSOR_HMAC_SECRET = os.environ["SENSOR_HMAC_SECRET"]
config.LOG_ARQUIVO = Path(__file__).resolve().parent / "teste.log"

CHAVE = {"X-API-Key": config.API_KEY_OPERADOR}

SENSOR_EXEMPLO = {
    "id": 1, "codigo": "DL-01", "nome": "Arroio Teste", "bairro": "Centro",
    "latitude": -30.05, "longitude": -51.21, "nivel_alerta_cm": 200, "nivel_critico_cm": 300,
    "ativo": True, "ultimo_nivel_cm": 120.0, "ultima_leitura_em": "2026-11-09T10:00:00",
}


@pytest.fixture
def cliente(monkeypatch):
    """
    Cliente de teste do Flask com o banco 'de mentira'.

    Graças ao MVC, basta trocar a MODEL de sensor: o controller e a view
    continuam exatamente iguais, sem saber que o banco é falso.
    """
    from alerta_rio import criar_app
    from alerta_rio.core.extensoes import limiter
    from alerta_rio.models import sensor as sensor_model

    banco = {1: dict(SENSOR_EXEMPLO)}

    monkeypatch.setattr(sensor_model, "buscar", lambda i: banco.get(i))
    monkeypatch.setattr(sensor_model, "listar", lambda somente_ativos=False: list(banco.values()))
    monkeypatch.setattr(sensor_model, "criar", lambda d: banco.setdefault(2, {**d, "id": 2}) and 2)
    monkeypatch.setattr(sensor_model, "excluir", lambda i: banco.pop(i, None) is not None)

    def atualizar(i, d):
        if i not in banco:
            return False
        banco[i].update(d)
        return True

    monkeypatch.setattr(sensor_model, "atualizar", atualizar)

    limiter.enabled = False  # nos testes não queremos esbarrar no limite de requisições
    app = criar_app()
    app.config["TESTING"] = True
    return app.test_client()
