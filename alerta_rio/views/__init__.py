"""
V de MVC: VIEWS (Visões / Apresentação)

Tudo que tem a ver com COMO a informação aparece para quem usa:
  - templates/index.html e static/ -> a página do painel (HTML, CSS, JS, ícones)
  - pagina_view.py                 -> monta a página HTML com os dados da cidade
  - json_view.py                   -> formata as respostas da API em JSON

A view não consulta o banco nem decide regras: ela só recebe os dados
prontos do Controller e os apresenta.
"""
