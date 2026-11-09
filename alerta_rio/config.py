"""
Configurações do Alerta Rio.

Regra de ouro: nada de senha ou chave escrita direto no código.
Tudo que é sensível vem do arquivo .env (que fica fora do GitHub).
O arquivo .env.example mostra quais variáveis precisam existir.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Pasta raiz do projeto (um nível acima deste arquivo)
RAIZ = Path(__file__).resolve().parent.parent

# Carrega o .env da raiz. Se a variável já existir no sistema, ela vence.
load_dotenv(RAIZ / ".env")


def _obrigatoria(nome: str) -> str:
    """Lê uma variável que o sistema não consegue funcionar sem."""
    valor = os.getenv(nome, "").strip()
    if not valor:
        # Falhar logo na largada é melhor do que falhar no meio de uma requisição
        raise RuntimeError(
            f"A variável {nome} não foi definida. Copie o .env.example para .env e preencha."
        )
    return valor


def _numero(nome: str, padrao: float) -> float:
    """Lê uma variável numérica, voltando ao padrão se vier algo estranho."""
    try:
        return float(os.getenv(nome, padrao))
    except ValueError:
        return padrao


# --- Banco de dados (MySQL) ---------------------------------------------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(_numero("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "alerta_rio")
DB_USER = os.getenv("DB_USER", "alerta_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# --- Segurança ---------------------------------------------------------
# Chave que o operador da Defesa Civil usa para cadastrar/editar/excluir
API_KEY_OPERADOR = os.getenv("API_KEY_OPERADOR", "")
# Segredo compartilhado com os sensores para assinar cada leitura (HMAC)
SENSOR_HMAC_SECRET = os.getenv("SENSOR_HMAC_SECRET", "")

# --- Servidor de sensores (UDP) ------------------------------------------
UDP_HOST = os.getenv("UDP_HOST", "127.0.0.1")
UDP_PORT = int(_numero("UDP_PORT", 5005))

# --- Cidade monitorada (usada na previsão do tempo) ---------------------
CIDADE_NOME = os.getenv("CIDADE_NOME", "Porto Alegre - RS")
CIDADE_LAT = _numero("CIDADE_LAT", -30.0346)
CIDADE_LON = _numero("CIDADE_LON", -51.2177)

# --- Aplicação -----------------------------------------------------------
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(_numero("FLASK_PORT", 5000))
LOG_ARQUIVO = RAIZ / os.getenv("LOG_ARQUIVO", "logs/alerta_rio.log")


def validar_configuracao() -> None:
    """Confere as variáveis obrigatórias antes de subir a API ou o servidor UDP."""
    for nome in ("DB_PASSWORD", "API_KEY_OPERADOR", "SENSOR_HMAC_SECRET"):
        _obrigatoria(nome)
    if len(API_KEY_OPERADOR) < 16 or len(SENSOR_HMAC_SECRET) < 16:
        raise RuntimeError("API_KEY_OPERADOR e SENSOR_HMAC_SECRET precisam ter pelo menos 16 caracteres.")
