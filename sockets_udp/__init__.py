"""
Módulo de sockets do Alerta Rio.

Por que UDP e não TCP? Sensores de campo costumam ser aparelhos simples,
com bateria e internet ruim. UDP é leve: o sensor manda a leitura e
pronto, sem abrir e manter conexão. Se um pacote se perde, o próximo
chega alguns segundos depois. Mesmo assim, devolvemos uma confirmação
(ACK) para o sensor saber que foi recebido.
"""
