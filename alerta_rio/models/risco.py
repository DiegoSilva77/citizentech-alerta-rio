"""
Cálculo do risco de enchente.

A lógica foi pensada para ser explicável para qualquer morador,
sem "caixa-preta":

  1. O nível do rio passou do CRÍTICO?            -> PERIGO
  2. Passou do nível de ALERTA?                   -> ATENÇÃO
     ...e vem chuva forte nas próximas 6 horas?   -> sobe para PERIGO
  3. Está abaixo do alerta, mas já perto (70%)
     e a previsão é de muita chuva?               -> ATENÇÃO
  4. Caso contrário                               -> NORMAL
"""

NORMAL = "normal"
ATENCAO = "atencao"
PERIGO = "perigo"

# Ordem de gravidade, usada para descobrir o "pior" risco da cidade
GRAVIDADE = {NORMAL: 0, ATENCAO: 1, PERIGO: 2}

CHUVA_FORTE_6H_MM = 10.0   # chuva que já agrava um rio em alerta
CHUVA_MUITO_FORTE_6H_MM = 25.0  # chuva que preocupa mesmo com o rio mais baixo
PROXIMIDADE_ALERTA = 0.7


def calcular_risco(nivel_cm, nivel_alerta_cm, nivel_critico_cm, chuva_6h_mm=0.0) -> str:
    """Devolve 'normal', 'atencao' ou 'perigo'."""
    if nivel_cm is None:
        return NORMAL  # sem leitura ainda: não inventamos alarme

    nivel = float(nivel_cm)
    alerta = float(nivel_alerta_cm)
    critico = float(nivel_critico_cm)
    chuva = float(chuva_6h_mm or 0)

    if nivel >= critico:
        return PERIGO
    if nivel >= alerta:
        return PERIGO if chuva >= CHUVA_FORTE_6H_MM else ATENCAO
    if nivel >= alerta * PROXIMIDADE_ALERTA and chuva >= CHUVA_MUITO_FORTE_6H_MM:
        return ATENCAO
    return NORMAL


def calcular_tendencia(niveis_recentes: list) -> str:
    """
    Compara a média das leituras mais novas com as mais antigas.
    'niveis_recentes' vem do mais NOVO para o mais ANTIGO.
    """
    niveis = [float(n) for n in niveis_recentes if n is not None]
    if len(niveis) < 4:
        return "estavel"
    metade = len(niveis) // 2
    recentes = sum(niveis[:metade]) / metade
    antigas = sum(niveis[metade:]) / (len(niveis) - metade)
    diferenca = recentes - antigas
    if diferenca > 3:
        return "subindo"
    if diferenca < -3:
        return "descendo"
    return "estavel"


def pior_risco(riscos: list) -> str:
    """Entre vários riscos, devolve o mais grave (o que manda no painel geral)."""
    if not riscos:
        return NORMAL
    return max(riscos, key=lambda r: GRAVIDADE.get(r, 0))


def mensagem_alerta(risco: str, nome_ponto: str, nivel_cm: float, critico_cm: int) -> str:
    """Texto curto e direto, do jeito que um morador precisa ler numa emergência."""
    if risco == PERIGO:
        return (f"PERIGO em {nome_ponto}: rio a {nivel_cm:.0f} cm (crítico {critico_cm} cm). "
                f"Procure o abrigo mais próximo.")
    if risco == ATENCAO:
        return f"Atenção em {nome_ponto}: rio a {nivel_cm:.0f} cm e subindo. Prepare documentos e remédios."
    return f"Nível normalizado em {nome_ponto}: {nivel_cm:.0f} cm."
