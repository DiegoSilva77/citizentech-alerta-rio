"""
C de MVC: CONTROLLERS (Controladores)

O controller é o "meio de campo". Para cada pedido ele:
  1. recebe a entrada (requisição HTTP ou pacote UDP do sensor)
  2. valida o que chegou (core/validacao.py)
  3. chama a Model certa para ler ou gravar dados
  4. escolhe a View que vai apresentar o resultado (página HTML ou JSON)

Controllers deste projeto:
  - painel_controller.py  -> página principal, resumo, clima, alertas, status
  - sensor_controller.py  -> CRUD de sensores (/api/sensores)
  - abrigo_controller.py  -> CRUD de abrigos (/api/abrigos)
  - leitura_controller.py -> leituras que chegam pelo socket UDP
  - erro_controller.py    -> o que responder quando algo dá errado
"""
