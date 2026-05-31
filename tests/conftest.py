# -*- coding: utf-8 -*-
"""
conftest.py — Fixtures globales para la suite de tests de agente_scratch.

Siguiendo el Framework SDD: cada fixture representa un estado verificable
del sistema, no un detalle de implementación.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def spec_valida() -> dict:
    """Retorna una spec mínima válida con un sprite y un bloque sombrero."""
    return {
        "tipo_juego": "test",
        "advertencias": [],
        "stage": {"variables": {}, "broadcasts": {}},
        "sprites": [
            {
                "nombre": "Gato",
                "x": 0,
                "y": 0,
                "variables": {},
                "broadcasts": {},
                "blocks": {
                    "s0_b001": {
                        "opcode": "event_whenflagclicked",
                        "next": None,
                        "parent": None,
                        "inputs": {},
                        "fields": {},
                        "shadow": False,
                        "topLevel": True,
                    }
                },
            }
        ],
    }


@pytest.fixture
def spec_con_opcode_invalido() -> dict:
    """Retorna una spec con un bloque 'text' inválido para probar reparar_spec."""
    return {
        "tipo_juego": "test",
        "advertencias": [],
        "stage": {"variables": {}, "broadcasts": {}},
        "sprites": [
            {
                "nombre": "Gato",
                "x": 0,
                "y": 0,
                "variables": {},
                "broadcasts": {},
                "blocks": {
                    "s0_b001": {
                        "opcode": "looks_say",
                        "next": None,
                        "parent": None,
                        "inputs": {"MESSAGE": [1, "s0_sombra"]},
                        "fields": {},
                        "shadow": False,
                        "topLevel": False,
                    },
                    "s0_sombra": {
                        "opcode": "text",
                        "next": None,
                        "parent": "s0_b001",
                        "inputs": {},
                        "fields": {"TEXT": ["Hola mundo", None]},
                        "shadow": True,
                        "topLevel": False,
                    },
                },
            }
        ],
    }


@pytest.fixture
def gemini_mock(monkeypatch):
    """Parchea _call_gemini para evitar llamadas reales a la API de Gemini."""
    mock = MagicMock(return_value={
        "tipo_juego": "test",
        "advertencias": [],
        "stage": {"variables": {}, "broadcasts": {}},
        "sprites": [],
    })
    monkeypatch.setattr("agente_scratch.core._call_gemini", mock)
    return mock


@pytest.fixture
def assets_tmp(tmp_path: Path, monkeypatch) -> Path:
    """Crea una carpeta assets/ temporal y parchea ASSETS_DIR para apuntar a ella."""
    assets = tmp_path / "assets"
    assets.mkdir()
    svg = assets / "Gato.svg"
    svg.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"/>')
    monkeypatch.setattr("agente_scratch.core.ASSETS_DIR", assets)
    monkeypatch.setattr("agente_scratch.agent.tools.ASSETS_DIR", assets)
    return assets
