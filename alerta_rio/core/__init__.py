"""
CORE: peças de apoio usadas pelas três camadas do MVC.

Não são Model, View nem Controller. São "ferramentas" transversais:
  - validacao.py -> confere toda entrada antes de chegar na Model
  - seguranca.py -> chave de operador, assinatura HMAC, anti-replay e cabeçalhos HTTP
  - log.py       -> log de auditoria em arquivo
  - extensoes.py -> limite de requisições (rate limiting)
"""
