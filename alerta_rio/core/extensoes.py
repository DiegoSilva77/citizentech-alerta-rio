"""
Extensões do Flask que precisam existir antes do app ser criado.

O Limiter conta quantas requisições cada IP fez por minuto. Passou
do limite, a API responde 429. Isso atrapalha robôs, ataques de força
bruta na chave de operador e excesso de chamadas por engano.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    default_limits=["300 per minute"],
    storage_uri="memory://",
)

# Limite mais apertado para as rotas que alteram dados
LIMITE_ESCRITA = "30 per minute"
