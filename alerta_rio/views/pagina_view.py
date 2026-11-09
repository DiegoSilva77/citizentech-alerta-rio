"""
View HTML: entrega a página do painel.

O HTML em si está em templates/index.html, e o visual em static/css/style.css.
O JavaScript (static/js/app.js) busca os dados na API depois que a página abre.
"""

from flask import render_template

from .. import config


def renderizar_painel():
    """Monta a página principal com o nome e as coordenadas da cidade monitorada."""
    return render_template(
        "index.html",
        cidade=config.CIDADE_NOME,
        lat=config.CIDADE_LAT,
        lon=config.CIDADE_LON,
    )
