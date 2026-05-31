# -*- coding: utf-8 -*-
"""
cli/test_app.py — Tests unitarios para agente_scratch/cli/app.py.

Cubre: mostrar_bienvenida, mostrar_help, _leer con /exit.
"""

import pytest
from unittest.mock import patch
from io import StringIO


# ─── mostrar_bienvenida ───────────────────────────────────────────────────────

def test_mostrar_bienvenida_no_lanza_excepcion():
    """mostrar_bienvenida invoca una App Textual — se mockea .run() para evitar TUI real."""
    from agente_scratch.cli.app import mostrar_bienvenida
    with patch("agente_scratch.cli.app._render_gato", return_value="=^.^="):
        with patch("textual.app.App.run", return_value=None):
            mostrar_bienvenida()


def test_mostrar_help_no_lanza_excepcion():
    """mostrar_help debe ejecutarse sin lanzar excepciones."""
    from agente_scratch.cli.app import mostrar_help
    with patch("agente_scratch.cli.app._console") as mock_console:
        mock_console.print = lambda *a, **kw: None
        mostrar_help()


# ─── _leer ────────────────────────────────────────────────────────────────────

def test_leer_exit_lanza_system_exit():
    """/exit debe lanzar SystemExit."""
    from agente_scratch.cli.app import _leer
    with patch("builtins.input", return_value="/exit"):
        with pytest.raises(SystemExit):
            _leer("> ")


def test_leer_ctrl_c_lanza_system_exit():
    """Ctrl+C (KeyboardInterrupt) debe lanzar SystemExit."""
    from agente_scratch.cli.app import _leer
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit):
            _leer("> ")


def test_leer_valor_normal_lo_devuelve():
    """Un input normal debe devolverse sin modificar (strip aplicado)."""
    from agente_scratch.cli.app import _leer
    with patch("builtins.input", return_value="  hola mundo  "):
        resultado = _leer("> ")
    assert resultado == "hola mundo"


def test_leer_quit_lanza_system_exit():
    """'quit' también debe lanzar SystemExit."""
    from agente_scratch.cli.app import _leer
    with patch("builtins.input", return_value="quit"):
        with pytest.raises(SystemExit):
            _leer("> ")
