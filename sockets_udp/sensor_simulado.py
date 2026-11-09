"""
Simulador de sensores de nível do rio.

Na vida real, seria um aparelhinho (ex.: ESP32 + sensor ultrassônico)
preso numa ponte. Aqui, simulamos vários deles mandando leituras por UDP.

    python -m sockets_udp.sensor_simulado                       # tempo normal
    python -m sockets_udp.sensor_simulado --cenario chuva       # rio subindo devagar
    python -m sockets_udp.sensor_simulado --cenario enchente    # rio subindo rápido (demonstração!)
    python -m sockets_udp.sensor_simulado --cenario baixando    # a água baixando depois da cheia
    python -m sockets_udp.sensor_simulado --invasor             # testa assinatura falsa e replay

O simulador pergunta à API o último nível de cada ponto antes de começar,
para continuar a "história" de onde parou (use --do-zero para ignorar).
"""

import argparse
import json
import random
import socket
import time

import requests
from rich.console import Console

from alerta_rio import config
from alerta_rio.core.seguranca import assinar_leitura

console = Console()

# Nível inicial e "personalidade" de cada ponto (mesmos códigos do setup do banco)
SENSORES = {
    "DL-01": {"nivel": 125.0, "sensibilidade": 1.0},
    "GB-01": {"nivel": 185.0, "sensibilidade": 0.6},  # o lago sobe mais devagar
    "AF-01": {"nivel": 100.0, "sensibilidade": 1.4},  # arroio pequeno enche rápido
    "RG-01": {"nivel": 155.0, "sensibilidade": 0.9},
    "AC-01": {"nivel": 75.0, "sensibilidade": 1.2},
}

# Quanto o rio tende a subir (ou descer) por leitura em cada cenário (cm)
DERIVA = {"normal": 0.0, "chuva": 2.5, "enchente": 9.0, "baixando": -8.0}


def sincronizar_niveis() -> None:
    """
    Continua de onde o rio parou: pergunta à API o último nível de cada ponto.
    Também "adota" sensores novos cadastrados pela tela de Gestão.
    Se a API não responder, seguimos com os níveis iniciais. Não é crítico.
    """
    try:
        resposta = requests.get(f"http://127.0.0.1:{config.FLASK_PORT}/api/sensores?ativos=1", timeout=3)
        resposta.raise_for_status()
        for s in resposta.json():
            estado = SENSORES.setdefault(s["codigo"], {"nivel": s["nivel_alerta_cm"] * 0.5, "sensibilidade": 1.0})
            if s.get("ultimo_nivel_cm") is not None:
                estado["nivel"] = float(s["ultimo_nivel_cm"])
        console.print("[dim]Níveis sincronizados com a API.[/dim]")
    except (requests.RequestException, ValueError, KeyError, TypeError):
        console.print("[dim]API fora do ar: começando dos níveis padrão.[/dim]")


def proxima_leitura(estado: dict, cenario: str) -> float:
    """Passeio aleatório: um pouquinho de ruído + a tendência do cenário."""
    variacao = random.uniform(-2.0, 2.0) + DERIVA[cenario] * estado["sensibilidade"]
    estado["nivel"] = max(10.0, round(estado["nivel"] + variacao, 1))
    return estado["nivel"]


def montar_pacote(codigo: str, nivel: float, segredo: str | None = None) -> bytes:
    ts = int(time.time())
    pacote = {
        "codigo": codigo,
        "nivel_cm": nivel,
        "ts": ts,
        "assinatura": assinar_leitura(codigo, nivel, ts, segredo),
    }
    return json.dumps(pacote).encode()


def enviar(sock: socket.socket, dados: bytes) -> dict | None:
    """Envia e espera o ACK do servidor por até 2 segundos."""
    sock.sendto(dados, (config.UDP_HOST, config.UDP_PORT))
    try:
        resposta, _ = sock.recvfrom(1024)
        return json.loads(resposta.decode())
    except (socket.timeout, ConnectionResetError, json.JSONDecodeError):
        return None


def modo_invasor(sock: socket.socket) -> None:
    """Demonstração de segurança: um atacante tenta mandar um nível falso."""
    console.rule("[bold red]Simulando ataque: leitura com assinatura falsa[/bold red]")
    falso = montar_pacote("DL-01", 999.0, segredo="segredo-que-o-atacante-chutou")
    resposta = enviar(sock, falso)
    console.print(f"Resposta do servidor: [bold]{resposta}[/bold]")

    console.rule("[bold red]Simulando ataque: reenvio (replay) de um pacote legítimo[/bold red]")
    legitimo = montar_pacote("DL-01", SENSORES["DL-01"]["nivel"])
    console.print(f"1º envio:  {enviar(sock, legitimo)}")
    console.print(f"2º envio (mesmo pacote): [bold]{enviar(sock, legitimo)}[/bold]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador de sensores do Alerta Rio")
    parser.add_argument("--cenario", choices=DERIVA.keys(), default="normal")
    parser.add_argument("--intervalo", type=float, default=3.0, help="segundos entre rodadas")
    parser.add_argument("--rodadas", type=int, default=0, help="0 = infinito")
    parser.add_argument("--invasor", action="store_true", help="testa as defesas do servidor")
    parser.add_argument("--do-zero", action="store_true", help="ignora a API e começa dos níveis padrão")
    args = parser.parse_args()

    if not config.SENSOR_HMAC_SECRET:
        raise SystemExit("Defina SENSOR_HMAC_SECRET no .env (o mesmo do servidor).")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    if not args.do_zero:
        sincronizar_niveis()

    if args.invasor:
        modo_invasor(sock)
        return

    console.rule(f"[bold blue]Sensores simulados · cenário: {args.cenario}[/bold blue]")
    rodada = 0
    try:
        while args.rodadas == 0 or rodada < args.rodadas:
            rodada += 1
            for codigo, estado in SENSORES.items():
                nivel = proxima_leitura(estado, args.cenario)
                resposta = enviar(sock, montar_pacote(codigo, nivel))
                if resposta is None:
                    console.print(f"[yellow]… {codigo} sem resposta (servidor UDP está rodando?)[/yellow]")
                elif resposta.get("status") == "ok":
                    console.print(f"[green]↑[/green] {codigo:<6} {nivel:>6.1f} cm  [dim]ACK ok[/dim]")
                else:
                    console.print(f"[red]↑ {codigo:<6} {nivel:>6.1f} cm  recusado: {resposta.get('motivo')}[/red]")
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        console.print("\n[yellow]Simulação encerrada.[/yellow]")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
