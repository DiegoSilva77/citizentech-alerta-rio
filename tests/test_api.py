"""Testes da API: códigos de status, autenticação e cabeçalhos de segurança."""

from conftest import CHAVE

NOVO = {
    "codigo": "AF-02", "nome": "Arroio Novo - Ponte", "bairro": "Sarandi",
    "latitude": -29.99, "longitude": -51.12, "nivel_alerta_cm": 150, "nivel_critico_cm": 200,
}


def test_get_sensor_existente(cliente):
    r = cliente.get("/api/sensores/1")
    assert r.status_code == 200
    assert r.get_json()["codigo"] == "DL-01"


def test_get_sensor_inexistente_da_404(cliente):
    assert cliente.get("/api/sensores/999").status_code == 404


def test_post_sem_chave_da_401(cliente):
    assert cliente.post("/api/sensores", json=NOVO).status_code == 401


def test_post_com_chave_errada_da_401(cliente):
    r = cliente.post("/api/sensores", json=NOVO, headers={"X-API-Key": "chave-errada-qualquer"})
    assert r.status_code == 401


def test_post_sem_json_da_415(cliente):
    r = cliente.post("/api/sensores", data="texto", headers=CHAVE)
    assert r.status_code == 415


def test_post_valido_da_201_com_location(cliente):
    r = cliente.post("/api/sensores", json=NOVO, headers=CHAVE)
    assert r.status_code == 201
    assert r.headers["Location"].endswith("/api/sensores/2")


def test_post_invalido_da_400_e_lista_campos(cliente):
    r = cliente.post("/api/sensores", json={**NOVO, "latitude": 500}, headers=CHAVE)
    assert r.status_code == 400
    assert "latitude" in r.get_json()["campos"]


def test_put_atualiza(cliente):
    r = cliente.put("/api/sensores/1", json={**NOVO, "codigo": "DL-01"}, headers=CHAVE)
    assert r.status_code == 200
    assert r.get_json()["nome"] == NOVO["nome"]


def test_put_inexistente_da_404(cliente):
    assert cliente.put("/api/sensores/50", json=NOVO, headers=CHAVE).status_code == 404


def test_delete_da_204_e_depois_404(cliente):
    assert cliente.delete("/api/sensores/1", headers=CHAVE).status_code == 204
    assert cliente.delete("/api/sensores/1", headers=CHAVE).status_code == 404


def test_erro_nao_vaza_detalhes_internos(cliente):
    r = cliente.get("/api/sensores/999")
    texto = r.get_data(as_text=True)
    assert "Traceback" not in texto and "mysql" not in texto.lower()


def test_cabecalhos_de_seguranca(cliente):
    r = cliente.get("/api/sensores/1")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
