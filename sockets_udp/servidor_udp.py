"""
Servidor UDP que recebe as leituras dos sensores de nível do rio.

    python -m sockets_udp.servidor_udp

Este arquivo cuida SÓ da parte de rede: abrir o socket, receber os
bytes e devolver a confirmação (ACK) ao sensor. A decisão sobre cada
pacote (é válido? está assinado? gera alerta?) fica no controller:
alerta_rio/controllers/leitura_controller.py. É o MVC também aqui.
"""

import json
import logging
import socket

from rich.console import Console

from alerta_rio import config
from alerta_rio.controllers.leitura_controller import processar_pacote
from alerta_rio.core.log import registrar
from alerta_rio.core.seguranca import GuardaReplay
from alerta_rio.models.conexao import ErroBanco

console = Console()
CORES_RISCO = {"normal": "green", "atencao": "yellow", "perigo": "bold red"}


def responder(sock: socket.socket, destino, status: str, motivo: str = "") -> None:
    """Manda o ACK de volta para o sensor (sem revelar detalhes internos)."""
    resposta = {"status": status}
    if motivo:
        resposta["motivo"] = motivo
    try:
        sock.sendto(json.dumps(resposta).encode(), destino)
    except OSError:
        pass  # se o sensor já foi embora, não tem o que fazer


def mostrar_no_terminal(resultado: dict) -> None:
    """Saída colorida para acompanhar a demonstração ao vivo."""
    if resultado["status"] != "ok":
        console.print(f"[red]✖ Pacote recusado: {resultado['detalhe']}[/red]")
        return
    cor = CORES_RISCO[resultado["risco"]]
    if resultado["novo_alerta"]:
        console.print(f"[{cor}]⚑ ALERTA {resultado['risco'].upper()}: {resultado['novo_alerta']}[/{cor}]")
    console.print(
        f"[cyan]↓[/cyan] {resultado['codigo']:<6} [bold]{resultado['nivel_cm']:>6.1f} cm[/bold]  "
        f"[{cor}]● {resultado['risco']}[/{cor}]"
    )


def iniciar_servidor() -> None:
    config.validar_configuracao()
    guarda = GuardaReplay()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((config.UDP_HOST, config.UDP_PORT))
    registrar("UDP", "INICIAR_SERVIDOR", "SUCESSO", f"{config.UDP_HOST}:{config.UDP_PORT}")

    console.rule("[bold blue]Alerta Rio · Servidor de Sensores (UDP)[/bold blue]")
    console.print(f"Escutando em [bold]{config.UDP_HOST}:{config.UDP_PORT}[/bold]. Ctrl+C para parar.\n")

    try:
        while True:
            try:
                dados, origem = sock.recvfrom(4096)
            except ConnectionResetError:
                # Particularidade do Windows: se um sensor fechou antes de receber o ACK,
                # o sistema avisa "conexão resetada" na próxima leitura. Em UDP isso é inofensivo.
                continue

            try:
                resultado = processar_pacote(dados, guarda)
                mostrar_no_terminal(resultado)
                responder(sock, origem, resultado["status"], resultado["motivo"])
            except ErroBanco:
                # Banco fora do ar: avisamos o sensor para ele tentar de novo
                console.print("[red]Banco indisponível no momento.[/red]")
                responder(sock, origem, "erro", "tente novamente")
            except Exception as erro:  # nunca deixar o servidor cair por causa de um pacote
                registrar("UDP", "ERRO_INESPERADO", "FALHA", type(erro).__name__, logging.ERROR)
                responder(sock, origem, "erro", "tente novamente")
    except KeyboardInterrupt:
        console.print("\n[yellow]Servidor encerrado pelo usuário.[/yellow]")
    finally:
        sock.close()
        registrar("UDP", "PARAR_SERVIDOR", "SUCESSO", "")


if __name__ == "__main__":
    iniciar_servidor()
