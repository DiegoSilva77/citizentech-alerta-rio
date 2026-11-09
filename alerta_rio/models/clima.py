"""
Integração com a API externa Open-Meteo (https://open-meteo.com).

Por que a Open-Meteo? É gratuita, aberta, não pede cadastro nem chave
e usa dados de institutos meteorológicos oficiais. Perfeito para um
projeto cidadão.

Guardamos a resposta em cache por 10 minutos: a previsão não muda a
cada segundo, e assim não sobrecarregamos um serviço gratuito.
"""

import logging
import threading
import time
from datetime import datetime

import requests

from .. import config
from ..core.log import registrar

URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
TEMPO_CACHE_S = 600
TIMEOUT_S = 6


class ClimaIndisponivel(Exception):
    """A API de clima não respondeu ou respondeu algo que não entendemos."""


_cache = {"dados": None, "quando": 0.0}
_trava = threading.Lock()

# Tradução dos códigos WMO que a Open-Meteo usa para descrever o tempo
DESCRICAO_TEMPO = {
    0: ("Céu limpo", "sun"), 1: ("Poucas nuvens", "cloud-sun"), 2: ("Parcialmente nublado", "cloud-sun"),
    3: ("Nublado", "cloud"), 45: ("Neblina", "cloud-fog"), 48: ("Neblina", "cloud-fog"),
    51: ("Garoa fraca", "cloud-drizzle"), 53: ("Garoa", "cloud-drizzle"), 55: ("Garoa forte", "cloud-drizzle"),
    61: ("Chuva fraca", "cloud-rain"), 63: ("Chuva moderada", "cloud-rain"), 65: ("Chuva forte", "cloud-rain-wind"),
    80: ("Pancadas fracas", "cloud-rain"), 81: ("Pancadas de chuva", "cloud-rain"),
    82: ("Pancadas fortes", "cloud-rain-wind"), 95: ("Tempestade", "cloud-lightning"),
    96: ("Tempestade com granizo", "cloud-lightning"), 99: ("Tempestade com granizo", "cloud-lightning"),
}


def _buscar_na_api() -> dict:
    """Faz a chamada HTTP de verdade e devolve o JSON cru."""
    parametros = {
        "latitude": config.CIDADE_LAT,
        "longitude": config.CIDADE_LON,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
        "hourly": "precipitation,precipitation_probability",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 2,
    }
    try:
        resposta = requests.get(URL_OPEN_METEO, params=parametros, timeout=TIMEOUT_S)
        resposta.raise_for_status()
        return resposta.json()
    except (requests.RequestException, ValueError) as erro:
        registrar("CLIMA", "CONSULTAR_OPEN_METEO", "FALHA", type(erro).__name__, logging.WARNING)
        raise ClimaIndisponivel("Previsão do tempo indisponível no momento.") from erro


def _organizar(bruto: dict) -> dict:
    """
    Transforma o JSON da Open-Meteo no formato que o nosso painel usa.
    Se algum campo esperado não vier, tratamos como resposta inválida.
    """
    try:
        atual = bruto["current"]
        horas = bruto["hourly"]["time"]
        chuva = bruto["hourly"]["precipitation"]
        probabilidade = bruto["hourly"]["precipitation_probability"]

        # Acha a posição da hora atual dentro da lista de horas da previsão
        hora_atual = atual["time"][:13]  # "2026-11-09T16"
        inicio = next((i for i, h in enumerate(horas) if h.startswith(hora_atual)), 0)
        fim = inicio + 24

        proximas = [
            {"hora": horas[i][11:16], "chuva_mm": float(chuva[i] or 0), "probabilidade": int(probabilidade[i] or 0)}
            for i in range(inicio, min(fim, len(horas)))
        ]
        descricao, icone = DESCRICAO_TEMPO.get(int(atual.get("weather_code", 3)), ("Tempo instável", "cloud"))

        return {
            "cidade": config.CIDADE_NOME,
            "atual": {
                "temperatura_c": float(atual["temperature_2m"]),
                "umidade_pct": int(atual["relative_humidity_2m"]),
                "chuva_mm": float(atual["precipitation"]),
                "descricao": descricao,
                "icone": icone,
            },
            "chuva_6h_mm": round(sum(h["chuva_mm"] for h in proximas[:6]), 1),
            "chuva_24h_mm": round(sum(h["chuva_mm"] for h in proximas), 1),
            "proximas_horas": proximas,
            "fonte": "Open-Meteo",
            "consultado_em": datetime.now().isoformat(timespec="seconds"),
        }
    except (KeyError, TypeError, ValueError, IndexError) as erro:
        registrar("CLIMA", "LER_RESPOSTA", "INVALIDO", type(erro).__name__, logging.WARNING)
        raise ClimaIndisponivel("Resposta inesperada do serviço de clima.") from erro


def obter_previsao() -> dict:
    """Devolve a previsão da cidade, usando o cache sempre que possível."""
    with _trava:
        if _cache["dados"] and time.time() - _cache["quando"] < TEMPO_CACHE_S:
            return _cache["dados"]

    dados = _organizar(_buscar_na_api())

    with _trava:
        _cache["dados"] = dados
        _cache["quando"] = time.time()
    registrar("CLIMA", "CONSULTAR_OPEN_METEO", "SUCESSO", f"chuva_6h={dados['chuva_6h_mm']}mm")
    return dados


def chuva_prevista_6h() -> float:
    """Atalho tolerante a falhas: se a API cair, consideramos 0 mm (e o rio continua mandando)."""
    try:
        return obter_previsao()["chuva_6h_mm"]
    except ClimaIndisponivel:
        return 0.0
