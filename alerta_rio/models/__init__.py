"""
M de MVC: MODELS (Modelos)

Aqui mora tudo que diz respeito aos DADOS e às REGRAS DO NEGÓCIO:
  - conexao.py -> conversa com o MySQL (pool + consultas parametrizadas)
  - sensor.py, leitura.py, alerta.py, abrigo.py -> uma "model" por tabela (CRUD em SQL puro)
  - clima.py   -> dados externos da Open-Meteo (também é uma fonte de dados)
  - risco.py   -> regra de negócio: quando o rio está normal, em atenção ou em perigo

A model não sabe nada de HTTP, HTML ou JSON. Ela só recebe e devolve dados
Python (dicionários, listas, números). Quem decide o que mostrar é a View,
e quem decide o que fazer com cada pedido é o Controller.
"""
