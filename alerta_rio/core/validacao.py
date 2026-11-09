"""
Validação de tudo que entra no sistema.

A ideia é simples: desconfiar de qualquer dado que vem de fora.
Cada campo tem tipo, tamanho e formato conferidos, e campos
que não conhecemos são recusados (isso evita alguém "enfiar"
um campo como 'id' ou 'ativo' que não deveria mexer).
"""

import re

# Letras (com acento), números, espaço e uma pontuação básica.
# Sinais como < > { } ; ficam de fora: não têm motivo para aparecer
# no nome de um abrigo e são os preferidos de quem tenta XSS/injeção.
PADRAO_TEXTO = re.compile(r"^[\w\s.,'ºª°/()\-]+$", re.UNICODE)
PADRAO_CODIGO = re.compile(r"^[A-Z]{2}-\d{2,4}$")  # ex.: DL-01

# Limites do território brasileiro (aproximados). Coordenada fora
# disso quase sempre é erro de digitação (lat/lon trocadas, sinal faltando).
LAT_MIN, LAT_MAX = -34.0, 6.0
LON_MIN, LON_MAX = -74.0, -34.0


class ErroValidacao(Exception):
    """Carrega um dicionário {campo: mensagem} para devolver ao cliente."""

    def __init__(self, erros: dict):
        super().__init__("Dados inválidos")
        self.erros = erros


# ---------------------------------------------------------------------------
# Validadores de campo (pequenos e reaproveitáveis)
# ---------------------------------------------------------------------------

def _texto(dados, campo, erros, minimo=2, maximo=80, padrao=PADRAO_TEXTO):
    valor = dados.get(campo)
    if not isinstance(valor, str):
        erros[campo] = "Campo obrigatório (texto)."
        return None
    valor = " ".join(valor.split())  # tira espaços duplicados e nas pontas
    if not (minimo <= len(valor) <= maximo):
        erros[campo] = f"Deve ter entre {minimo} e {maximo} caracteres."
        return None
    if not padrao.match(valor):
        erros[campo] = "Contém caracteres não permitidos."
        return None
    return valor


def _numero(dados, campo, erros, minimo, maximo, inteiro=False):
    valor = dados.get(campo)
    # bool é subclasse de int no Python, então precisa ser barrado à parte
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        erros[campo] = "Campo obrigatório (número)."
        return None
    if inteiro and not float(valor).is_integer():
        erros[campo] = "Deve ser um número inteiro."
        return None
    if not (minimo <= valor <= maximo):
        erros[campo] = f"Deve estar entre {minimo} e {maximo}."
        return None
    return int(valor) if inteiro else round(float(valor), 6)


def _booleano(dados, campo, erros, padrao=None):
    if campo not in dados and padrao is not None:
        return padrao
    valor = dados.get(campo)
    if not isinstance(valor, bool):
        erros[campo] = "Deve ser verdadeiro ou falso."
        return None
    return valor


def _recusar_campos_extras(dados, permitidos, erros):
    extras = set(dados) - set(permitidos)
    if extras:
        erros["campos_desconhecidos"] = f"Campos não aceitos: {', '.join(sorted(extras))}."


def _exigir_dicionario(dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"corpo": "Envie um objeto JSON."})


# ---------------------------------------------------------------------------
# Validadores de entidade
# ---------------------------------------------------------------------------

CAMPOS_SENSOR = (
    "codigo", "nome", "bairro", "latitude", "longitude",
    "nivel_alerta_cm", "nivel_critico_cm", "ativo",
)


def validar_sensor(dados) -> dict:
    """Valida o corpo de POST/PUT de um sensor e devolve os dados limpos."""
    _exigir_dicionario(dados)
    erros = {}
    _recusar_campos_extras(dados, CAMPOS_SENSOR, erros)

    codigo = dados.get("codigo")
    if isinstance(codigo, str):
        codigo = codigo.strip().upper()
    limpo = {
        "codigo": codigo if isinstance(codigo, str) and PADRAO_CODIGO.match(codigo) else None,
        "nome": _texto(dados, "nome", erros, 3, 80),
        "bairro": _texto(dados, "bairro", erros, 2, 60),
        "latitude": _numero(dados, "latitude", erros, LAT_MIN, LAT_MAX),
        "longitude": _numero(dados, "longitude", erros, LON_MIN, LON_MAX),
        "nivel_alerta_cm": _numero(dados, "nivel_alerta_cm", erros, 10, 2000, inteiro=True),
        "nivel_critico_cm": _numero(dados, "nivel_critico_cm", erros, 10, 2000, inteiro=True),
        "ativo": _booleano(dados, "ativo", erros, padrao=True),
    }
    if limpo["codigo"] is None:
        erros["codigo"] = "Use o formato AA-00 (duas letras, hífen e 2 a 4 números)."

    # Regra de negócio: o nível crítico tem que ser maior que o de alerta
    if (
        limpo["nivel_alerta_cm"] is not None
        and limpo["nivel_critico_cm"] is not None
        and limpo["nivel_critico_cm"] <= limpo["nivel_alerta_cm"]
    ):
        erros["nivel_critico_cm"] = "O nível crítico precisa ser maior que o nível de alerta."

    if erros:
        raise ErroValidacao(erros)
    return limpo


CAMPOS_ABRIGO = (
    "nome", "endereco", "bairro", "latitude", "longitude",
    "capacidade", "ocupacao", "aceita_pets", "acessivel", "ativo",
)


def validar_abrigo(dados) -> dict:
    """Valida o corpo de POST/PUT de um abrigo e devolve os dados limpos."""
    _exigir_dicionario(dados)
    erros = {}
    _recusar_campos_extras(dados, CAMPOS_ABRIGO, erros)

    limpo = {
        "nome": _texto(dados, "nome", erros, 3, 80),
        "endereco": _texto(dados, "endereco", erros, 5, 120),
        "bairro": _texto(dados, "bairro", erros, 2, 60),
        "latitude": _numero(dados, "latitude", erros, LAT_MIN, LAT_MAX),
        "longitude": _numero(dados, "longitude", erros, LON_MIN, LON_MAX),
        "capacidade": _numero(dados, "capacidade", erros, 1, 5000, inteiro=True),
        "ocupacao": _numero(dados, "ocupacao", erros, 0, 5000, inteiro=True) if "ocupacao" in dados else 0,
        "aceita_pets": _booleano(dados, "aceita_pets", erros, padrao=False),
        "acessivel": _booleano(dados, "acessivel", erros, padrao=False),
        "ativo": _booleano(dados, "ativo", erros, padrao=True),
    }

    if (
        limpo["capacidade"] is not None
        and limpo["ocupacao"] is not None
        and limpo["ocupacao"] > limpo["capacidade"]
    ):
        erros["ocupacao"] = "A ocupação não pode passar da capacidade do abrigo."

    if erros:
        raise ErroValidacao(erros)
    return limpo


def validar_limite(valor, padrao=30, maximo=200) -> int:
    """Valida o parâmetro ?limite= das listagens (evita alguém pedir 1 milhão de linhas)."""
    if valor is None or valor == "":
        return padrao
    if not str(valor).isdigit():
        raise ErroValidacao({"limite": "Deve ser um número inteiro positivo."})
    return max(1, min(int(valor), maximo))


def validar_pacote_sensor(pacote) -> dict:
    """
    Valida a leitura que chega pelo socket UDP.
    Formato esperado: {"codigo": "DL-01", "nivel_cm": 123.4, "ts": 1700000000, "assinatura": "<hex>"}
    """
    _exigir_dicionario(pacote)
    erros = {}
    _recusar_campos_extras(pacote, ("codigo", "nivel_cm", "ts", "assinatura"), erros)

    codigo = pacote.get("codigo")
    if not (isinstance(codigo, str) and PADRAO_CODIGO.match(codigo)):
        erros["codigo"] = "Código inválido."
    nivel = _numero(pacote, "nivel_cm", erros, 0, 3000)
    ts = _numero(pacote, "ts", erros, 0, 10**11, inteiro=True)
    assinatura = pacote.get("assinatura")
    if not (isinstance(assinatura, str) and re.fullmatch(r"[0-9a-f]{64}", assinatura)):
        erros["assinatura"] = "Assinatura ausente ou mal formada."

    if erros:
        raise ErroValidacao(erros)
    return {"codigo": codigo, "nivel_cm": round(nivel, 1), "ts": ts, "assinatura": assinatura}
