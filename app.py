"""
Alerta Rio - ponto de entrada da API Flask e do painel web.

Para rodar:
    python app.py
Depois abra http://127.0.0.1:5000 no navegador.

A aplicação em si é montada em alerta_rio/__init__.py (criar_app),
seguindo o padrão MVC: models/, views/ e controllers/.
"""

from alerta_rio import config, criar_app

if __name__ == "__main__":
    aplicacao = criar_app()
    # host 127.0.0.1: só a própria máquina acessa (ótimo para a demonstração)
    aplicacao.run(host="127.0.0.1", port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
