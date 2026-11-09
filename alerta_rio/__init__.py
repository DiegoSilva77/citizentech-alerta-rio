"""
Alerta Rio - monitoramento comunitário de enchentes.

O projeto segue o padrão MVC (Model - View - Controller):

    alerta_rio/
    ├── models/       M -> dados e regras de negócio (MySQL, Open-Meteo, cálculo de risco)
    ├── views/        V -> apresentação (página HTML, CSS, JS e respostas JSON)
    ├── controllers/  C -> recebem os pedidos, chamam as models e escolhem a view
    └── core/         apoio para todas as camadas (validação, segurança, log)

Este arquivo tem a "fábrica" da aplicação Flask: ela junta as peças.
"""

__version__ = "2.0.0"


def criar_app():
    """
    Monta a aplicação Flask.

    Os imports ficam aqui dentro de propósito: assim, scripts que só precisam
    do config (como o setup do banco e o simulador) não carregam o Flask inteiro.
    """
    import logging

    from flask import Flask

    from . import config
    from .controllers import erro_controller
    from .controllers.abrigo_controller import abrigo_bp
    from .controllers.painel_controller import painel_bp
    from .controllers.sensor_controller import sensor_bp
    from .core.extensoes import limiter
    from .core.log import registrar
    from .core.seguranca import aplicar_cabecalhos

    config.validar_configuracao()

    # A View (HTML e arquivos estáticos) mora dentro de alerta_rio/views/
    app = Flask(
        __name__,
        template_folder="views/templates",
        static_folder="views/static",
    )
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # 16 KB é muito mais que suficiente
    app.json.ensure_ascii = False  # acentos aparecem normais no JSON
    app.json.sort_keys = False

    # Limite de requisições por IP (core/extensoes.py)
    limiter.init_app(app)

    # Controllers: cada Blueprint é um grupo de rotas
    app.register_blueprint(painel_bp)
    app.register_blueprint(sensor_bp)
    app.register_blueprint(abrigo_bp)

    # O que responder quando algo dá errado
    erro_controller.registrar_tratadores(app)

    # Cabeçalhos de segurança em toda resposta
    app.after_request(aplicar_cabecalhos)

    registrar("API", "INICIAR_SERVIDOR", "SUCESSO", f"porta={config.FLASK_PORT}", logging.INFO)
    return app
