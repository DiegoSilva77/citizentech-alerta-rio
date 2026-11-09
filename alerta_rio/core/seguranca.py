"""
Peças de segurança usadas pela API e pelos sensores.

1) Chave de operador: só quem tem a chave (Defesa Civil / líder
   comunitário) consegue cadastrar, editar ou excluir dados.
2) Assinatura HMAC-SHA256: cada leitura de sensor vem assinada
   com um segredo compartilhado. Sem a assinatura certa, o pacote
   é descartado. Isso impede alguém de mandar um "nível falso" e
   causar pânico (ou, pior, esconder uma enchente real).
3) Anti-replay: um pacote verdadeiro capturado e reenviado depois
   também é recusado (janela de tempo + memória de assinaturas).
"""

import hashlib
import hmac
import logging
import threading
import time
from functools import wraps

from flask import abort, request

from .. import config
from .log import registrar

JANELA_REPLAY_S = 30

# Política de segurança de conteúdo: o navegador só carrega scripts do
# próprio site, e imagens só do próprio site e do servidor de mapas.
CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https://tile.openstreetmap.org; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def aplicar_cabecalhos(resposta):
    """Cabeçalhos de segurança colocados em TODA resposta (HTML ou JSON)."""
    resposta.headers["Content-Security-Policy"] = CSP
    resposta.headers["X-Content-Type-Options"] = "nosniff"       # não "adivinhar" tipo de arquivo
    resposta.headers["X-Frame-Options"] = "DENY"                 # ninguém embute o painel num iframe
    resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resposta.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return resposta


# ---------------------------------------------------------------------------
# 1) Chave de operador para rotas de escrita
# ---------------------------------------------------------------------------

def requer_operador(funcao):
    """Decorator: exige o cabeçalho X-API-Key com a chave correta."""

    @wraps(funcao)
    def protegida(*args, **kwargs):
        chave = request.headers.get("X-API-Key", "")
        # compare_digest compara em tempo constante: não "vaza" pistas pelo tempo de resposta
        if not chave or not hmac.compare_digest(chave.encode(), config.API_KEY_OPERADOR.encode()):
            registrar("API", f"{request.method} {request.path}"[:22], "NEGADO",
                      "chave de operador ausente/inválida", logging.WARNING)
            abort(401)
        return funcao(*args, **kwargs)

    return protegida


# ---------------------------------------------------------------------------
# 2) Assinatura das leituras dos sensores
# ---------------------------------------------------------------------------

def _mensagem_canonica(codigo: str, nivel_cm: float, ts: int) -> bytes:
    """O texto exato que é assinado. Sensor e servidor precisam montar igualzinho."""
    return f"{codigo}|{nivel_cm:.1f}|{ts}".encode()


def assinar_leitura(codigo: str, nivel_cm: float, ts: int, segredo: str | None = None) -> str:
    segredo = (segredo or config.SENSOR_HMAC_SECRET).encode()
    return hmac.new(segredo, _mensagem_canonica(codigo, nivel_cm, ts), hashlib.sha256).hexdigest()


def assinatura_valida(codigo: str, nivel_cm: float, ts: int, assinatura: str) -> bool:
    esperada = assinar_leitura(codigo, nivel_cm, ts)
    return hmac.compare_digest(esperada, assinatura)


# ---------------------------------------------------------------------------
# 3) Proteção contra reenvio (replay)
# ---------------------------------------------------------------------------

class GuardaReplay:
    """Lembra as assinaturas recentes e recusa pacotes velhos ou repetidos."""

    def __init__(self, janela_s: int = JANELA_REPLAY_S):
        self.janela_s = janela_s
        self._vistas: dict[str, float] = {}
        self._trava = threading.Lock()

    def aceitar(self, ts: int, assinatura: str) -> bool:
        agora = time.time()
        if abs(agora - ts) > self.janela_s:
            return False  # pacote muito antigo (ou relógio do sensor muito adiantado)
        with self._trava:
            # Faxina: esquece o que já saiu da janela
            for assin, quando in list(self._vistas.items()):
                if agora - quando > self.janela_s:
                    del self._vistas[assin]
            if assinatura in self._vistas:
                return False  # já recebemos exatamente este pacote
            self._vistas[assinatura] = agora
            return True
