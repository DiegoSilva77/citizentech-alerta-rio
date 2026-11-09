"""
Prepara o banco do zero, num comando só:

    python -m scripts.setup_banco

O que ele faz:
  1. Conecta como root (a senha é pedida na tela, não fica salva em lugar nenhum)
  2. Cria o banco e as tabelas (database/schema.sql)
  3. Cria o usuário da aplicação com o MÍNIMO de permissões
     (SELECT, INSERT, UPDATE, DELETE só no banco alerta_rio)
  4. Cadastra sensores e abrigos FICTÍCIOS e um histórico de leituras

Pode rodar de novo sem medo: ele apaga os dados de exemplo e recria.
"""

import argparse
import getpass
import os
import random
import sys
from datetime import datetime, timedelta

import mysql.connector

from alerta_rio import config
from alerta_rio.core.log import registrar

# ---------------------------------------------------------------------------
# Dados 100% fictícios. Os bairros existem em Porto Alegre (cidade atingida
# pela enchente de 2024), mas nomes de pontos, endereços e níveis são inventados.
# ---------------------------------------------------------------------------
SENSORES = [
    # codigo, nome, bairro, lat, lon, alerta, critico, nível "normal" de partida
    ("DL-01", "Arroio Dilúvio - Ponte da Ipiranga", "Azenha", -30.0508, -51.2141, 220, 300, 120),
    ("GB-01", "Lago Guaíba - Cais", "Centro Histórico", -30.0270, -51.2310, 300, 360, 180),
    ("AF-01", "Arroio Feijó - Passarela", "Sarandi", -29.9925, -51.1288, 180, 250, 95),
    ("RG-01", "Rio Gravataí - Vila Ribeirinha", "Humaitá", -29.9790, -51.1930, 260, 330, 150),
    ("AC-01", "Arroio Cavalhada - Rua da Escola", "Cavalhada", -30.0985, -51.2295, 160, 220, 70),
]

ABRIGOS = [
    # nome, endereço, bairro, lat, lon, capacidade, ocupação, pets, acessível
    ("Ginásio Comunitário Esperança", "Rua das Palmeiras, 210", "Partenon", -30.0612, -51.1820, 180, 42, True, True),
    ("Escola Estadual Horizonte", "Av. dos Ipês, 1500", "Petrópolis", -30.0375, -51.1885, 120, 15, False, True),
    ("Centro Social Vila Nova Aurora", "Rua Girassol, 88", "Jardim Botânico", -30.0525, -51.1740, 90, 70, True, False),
    ("Paróquia Bom Pastor - Salão", "Rua do Sino, 45", "Santana", -30.0470, -51.2010, 60, 8, False, False),
    ("Clube Recreativo Morro Alto", "Estrada da Colina, 3200", "Morro Santana", -30.0425, -51.1300, 250, 0, True, True),
]


def conectar_root(senha: str):
    return mysql.connector.connect(
        host=config.DB_HOST, port=config.DB_PORT, user="root", password=senha, charset="utf8mb4"
    )


def executar_schema(cursor) -> None:
    """Roda o schema.sql comando por comando."""
    caminho = config.RAIZ / "database" / "schema.sql"
    texto = caminho.read_text(encoding="utf-8")
    # Remove comentários de linha inteira e separa pelos ';'
    linhas = [l for l in texto.splitlines() if not l.strip().startswith("--")]
    for comando in "\n".join(linhas).split(";"):
        if comando.strip():
            cursor.execute(comando)


def criar_usuario_app(cursor) -> None:
    """Usuário da aplicação: só mexe em dados, nunca na estrutura do banco."""
    if not config.DB_PASSWORD:
        sys.exit("Defina DB_PASSWORD no .env antes de rodar o setup.")
    # Identificadores (nome de usuário) não aceitam %s, então validamos antes
    if not config.DB_USER.replace("_", "").isalnum():
        sys.exit("DB_USER só pode ter letras, números e _.")
    cursor.execute(f"CREATE USER IF NOT EXISTS '{config.DB_USER}'@'localhost' IDENTIFIED BY %s",
                   (config.DB_PASSWORD,))
    cursor.execute(f"ALTER USER '{config.DB_USER}'@'localhost' IDENTIFIED BY %s", (config.DB_PASSWORD,))
    cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON alerta_rio.* TO '{config.DB_USER}'@'localhost'")
    cursor.execute("FLUSH PRIVILEGES")


def popular_dados(cursor) -> None:
    """Limpa os dados antigos e cadastra o cenário de demonstração."""
    for tabela in ("alertas", "leituras", "sensores", "abrigos"):
        cursor.execute(f"DELETE FROM {tabela}")  # nomes fixos no código, não vêm do usuário
        cursor.execute(f"ALTER TABLE {tabela} AUTO_INCREMENT = 1")

    cursor.executemany(
        """INSERT INTO sensores (codigo, nome, bairro, latitude, longitude, nivel_alerta_cm, nivel_critico_cm)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        [s[:7] for s in SENSORES],
    )
    cursor.executemany(
        """INSERT INTO abrigos (nome, endereco, bairro, latitude, longitude, capacidade, ocupacao,
                                aceita_pets, acessivel)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        ABRIGOS,
    )

    # Histórico: 40 leituras por sensor nos últimos ~40 minutos (passeio aleatório suave)
    agora = datetime.now().replace(microsecond=0)
    leituras = []
    for sensor_id, s in enumerate(SENSORES, start=1):
        nivel = float(s[7])
        for i in range(40, 0, -1):
            nivel = max(10.0, nivel + random.uniform(-2.5, 3.0))
            leituras.append((sensor_id, round(nivel, 1), agora - timedelta(minutes=i)))
    cursor.executemany(
        "INSERT INTO leituras (sensor_id, nivel_cm, registrado_em) VALUES (%s, %s, %s)", leituras
    )

    # Um alerta inicial "normal" para cada ponto, só para a linha do tempo não nascer vazia
    cursor.executemany(
        "INSERT INTO alertas (sensor_id, nivel_risco, nivel_cm, mensagem, criado_em) VALUES (%s, 'normal', %s, %s, %s)",
        [(i, s[7], f"Monitoramento iniciado em {s[1]}.", agora - timedelta(minutes=41))
         for i, s in enumerate(SENSORES, start=1)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria o banco do Alerta Rio com dados fictícios.")
    parser.add_argument("--sem-dados", action="store_true", help="cria só a estrutura, sem dados de exemplo")
    args = parser.parse_args()

    # A senha do root pode vir da variável MYSQL_ROOT_PASSWORD (útil em automação)
    # ou ser digitada na hora, sem aparecer na tela.
    senha_root = os.getenv("MYSQL_ROOT_PASSWORD") or getpass.getpass("Senha do root do MySQL: ")

    try:
        con = conectar_root(senha_root)
    except mysql.connector.Error:
        sys.exit("Não consegui conectar como root. Confira se o MySQL está rodando e a senha.")

    try:
        cursor = con.cursor()
        print("-> Criando banco e tabelas...")
        executar_schema(cursor)
        print(f"-> Criando usuário da aplicação '{config.DB_USER}' (privilégio mínimo)...")
        criar_usuario_app(cursor)
        if not args.sem_dados:
            print("-> Cadastrando sensores, abrigos e leituras fictícias...")
            popular_dados(cursor)
        con.commit()
        registrar("SETUP", "CRIAR_BANCO", "SUCESSO", "schema + usuario + dados ficticios")
        print("Pronto! Banco alerta_rio preparado.")
    except mysql.connector.Error as erro:
        con.rollback()
        registrar("SETUP", "CRIAR_BANCO", "FALHA", f"errno={erro.errno}")
        sys.exit(f"Falha ao preparar o banco (código {erro.errno}). Veja o README.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
