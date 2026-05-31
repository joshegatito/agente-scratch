# -*- coding: utf-8 -*-
"""
agent/test_tools.py — Tests unitarios para agente_scratch/agent/tools.py.

Cubre: listar_assets, generar_spec, validar_spec, empaquetar.
"""

import json
import pytest

from agente_scratch.agent.tools import listar_assets, validar_spec


# ─── listar_assets ────────────────────────────────────────────────────────────

def test_listar_assets_carpeta_inexistente_devuelve_mensaje(monkeypatch, tmp_path):
    """Si assets/ no existe debe devolver JSON con lista vacía y mensaje."""
    monkeypatch.setattr("agente_scratch.agent.tools.ASSETS_DIR", tmp_path / "no_existe")
    resultado = json.loads(listar_assets.invoke({}))
    assert resultado["archivos"] == []


def test_listar_assets_carpeta_vacia_devuelve_mensaje(monkeypatch, tmp_path):
    """Si assets/ está vacía debe devolver JSON con lista vacía."""
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setattr("agente_scratch.agent.tools.ASSETS_DIR", assets)
    resultado = json.loads(listar_assets.invoke({}))
    assert resultado["archivos"] == []


def test_listar_assets_con_sprite_devuelve_nombre(assets_tmp):
    """Si hay un .svg en assets/ debe aparecer en la lista."""
    resultado = json.loads(listar_assets.invoke({}))
    assert "Gato.svg" in resultado["archivos"]
    assert resultado["total"] == 1


# ─── validar_spec ─────────────────────────────────────────────────────────────

def test_validar_spec_opcode_invalido_reporta_error():
    """Un opcode inventado debe reportarse como error."""
    spec = {
        "sprites": [
            {
                "nombre": "Gato",
                "variables": {},
                "blocks": {
                    "s0_b001": {
                        "opcode": "opcode_inventado_inexistente",
                        "inputs": {},
                        "fields": {},
                        "shadow": False,
                        "topLevel": True,
                        "next": None,
                        "parent": None,
                    }
                },
            }
        ]
    }
    resultado = json.loads(validar_spec.invoke({"spec_json": json.dumps(spec)}))
    assert resultado["valido"] is False
    assert any("opcode_inventado_inexistente" in e for e in resultado["errores"])


def test_validar_spec_referencia_inexistente_reporta_error():
    """Una referencia a un bloque que no existe debe reportarse."""
    spec = {
        "sprites": [
            {
                "nombre": "Gato",
                "variables": {},
                "blocks": {
                    "s0_b001": {
                        "opcode": "control_if",
                        "inputs": {"CONDITION": [2, "bloque_inexistente"]},
                        "fields": {},
                        "shadow": False,
                        "topLevel": True,
                        "next": None,
                        "parent": None,
                    }
                },
            }
        ]
    }
    resultado = json.loads(validar_spec.invoke({"spec_json": json.dumps(spec)}))
    assert resultado["valido"] is False
    assert any("bloque_inexistente" in e for e in resultado["errores"])


def test_validar_spec_valida_devuelve_valido_true(spec_valida):
    """Una spec válida debe devolver valido=True sin errores."""
    resultado = json.loads(validar_spec.invoke({"spec_json": json.dumps(spec_valida)}))
    assert resultado["valido"] is True
    assert resultado["errores"] == []


def test_validar_spec_json_invalido_devuelve_error():
    """JSON malformado debe devolver valido=False con mensaje de error."""
    resultado = json.loads(validar_spec.invoke({"spec_json": "esto no es json {{{"}))
    assert resultado["valido"] is False
