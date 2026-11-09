"""Testes que conferem a separação MVC: cada camada faz só o seu papel."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from alerta_rio.views import json_view

PACOTE = Path(__file__).resolve().parent.parent / "alerta_rio"


def test_view_converte_tipos_do_mysql():
    linha = {"nivel_cm": Decimal("123.4"), "criado_em": datetime(2026, 11, 9, 10, 0, 0), "ativo": 1}
    assert json_view.serializar(linha) == {"nivel_cm": 123.4, "criado_em": "2026-11-09T10:00:00", "ativo": True}


def test_models_nao_dependem_do_flask():
    """Model não pode saber de HTTP: nenhuma delas importa o Flask."""
    for arquivo in (PACOTE / "models").glob("*.py"):
        assert "flask" not in arquivo.read_text(encoding="utf-8").lower(), arquivo.name


def test_controllers_nao_escrevem_sql():
    """SQL é assunto da Model; controller só chama as funções dela."""
    for arquivo in (PACOTE / "controllers").glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8").upper()
        for comando in ("SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM"):
            assert comando not in texto, f"{arquivo.name} contém {comando.strip()}"
