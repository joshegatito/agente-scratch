# -*- coding: utf-8 -*-
"""
test_core.py — Tests unitarios para agente_scratch/core.py.

Cubre: normalizar_spec, reparar_spec, _declarar_variables_faltantes,
empaquetar_sb3 y validación de entorno de Gemini.
"""

import zipfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agente_scratch.core import (
    normalizar_spec,
    reparar_spec,
    empaquetar_sb3,
)


# ─── normalizar_spec ──────────────────────────────────────────────────────────

def test_normalizar_spec_con_sprites_devuelve_mismo_dict(spec_valida):
    """Si el dict ya tiene 'sprites', debe devolverse sin modificar."""
    resultado = normalizar_spec(spec_valida)
    assert resultado is spec_valida


def test_normalizar_spec_envuelto_en_clave_extra_lo_desenvuelve():
    """Gemini a veces envuelve la respuesta en una clave extra — debe desenvolverse."""
    raw = {
        "respuesta": {
            "tipo_juego": "puzle",
            "advertencias": [],
            "stage": {"variables": {}, "broadcasts": {}},
            "sprites": [],
        }
    }
    resultado = normalizar_spec(raw)
    assert "sprites" in resultado
    assert resultado["tipo_juego"] == "puzle"


def test_normalizar_spec_sin_sprites_devuelve_estructura_vacia():
    """Si no encuentra sprites en ningún nivel, devuelve estructura con sprites vacío."""
    raw = {"tipo_juego": "desconocido", "advertencias": []}
    resultado = normalizar_spec(raw)
    assert resultado["sprites"] == []


def test_normalizar_spec_tipo_invalido_lanza_value_error():
    """Si la entrada no es un dict, debe lanzar ValueError."""
    with pytest.raises(ValueError):
        normalizar_spec(["no", "es", "un", "dict"])


# ─── reparar_spec ─────────────────────────────────────────────────────────────

def test_reparar_spec_elimina_opcode_text_y_reconecta_inputs(spec_con_opcode_invalido):
    """El bloque 'text' debe eliminarse y su valor debe quedar inline en el padre."""
    resultado = reparar_spec(spec_con_opcode_invalido)
    bloques = resultado["sprites"][0]["blocks"]

    assert "s0_sombra" not in bloques, "El bloque 'text' debe eliminarse"
    mensaje = bloques["s0_b001"]["inputs"]["MESSAGE"]
    assert mensaje == [1, [10, "Hola mundo"]], "El input debe convertirse a literal inline"


def test_reparar_spec_sin_opcodes_invalidos_no_modifica(spec_valida):
    """Una spec sin opcodes inválidos debe salir idéntica."""
    import copy
    original = copy.deepcopy(spec_valida)
    resultado = reparar_spec(spec_valida)
    assert resultado["sprites"][0]["blocks"] == original["sprites"][0]["blocks"]


def test_reparar_spec_declara_variable_faltante():
    """Variables usadas en blocks pero no declaradas deben agregarse automáticamente."""
    spec = {
        "tipo_juego": "test",
        "advertencias": [],
        "stage": {"variables": {}, "broadcasts": {}},
        "sprites": [
            {
                "nombre": "Gato",
                "variables": {},
                "blocks": {
                    "s0_b001": {
                        "opcode": "data_setvariableto",
                        "next": None,
                        "parent": None,
                        "inputs": {"VALUE": [1, [10, "0"]]},
                        "fields": {"VARIABLE": ["puntaje", "var_puntaje"]},
                        "shadow": False,
                        "topLevel": False,
                    }
                },
            }
        ],
    }
    resultado = reparar_spec(spec)
    variables = resultado["sprites"][0]["variables"]
    assert "var_puntaje" in variables
    assert variables["var_puntaje"] == ["puntaje", 0]


# ─── empaquetar_sb3 ───────────────────────────────────────────────────────────

def test_empaquetar_sb3_genera_zip_con_project_json(spec_valida, tmp_path):
    """El .sb3 generado debe ser un ZIP válido que contenga project.json."""
    salida = str(tmp_path / "juego.sb3")
    resultado = empaquetar_sb3(spec_valida, [], salida)

    assert resultado["success"] is True
    assert Path(salida).exists()
    with zipfile.ZipFile(salida) as z:
        assert "project.json" in z.namelist()


def test_empaquetar_sb3_asset_inexistente_usa_fallback_svg(spec_valida, tmp_path):
    """Si el asset no existe, debe usarse un SVG de fallback sin fallar."""
    salida = str(tmp_path / "juego.sb3")
    assets = [{"nombre": "Gato", "path": str(tmp_path / "no_existe.svg")}]
    resultado = empaquetar_sb3(spec_valida, assets, salida)
    assert resultado["success"] is True


def test_empaquetar_sb3_retorna_metadatos_correctos(spec_valida, tmp_path):
    """El resultado debe incluir sprites, tipo_juego y tamanio_bytes."""
    salida = str(tmp_path / "juego.sb3")
    resultado = empaquetar_sb3(spec_valida, [], salida)
    assert "sprites" in resultado
    assert "tipo_juego" in resultado
    assert resultado["tamanio_bytes"] > 0


# ─── _call_gemini ─────────────────────────────────────────────────────────────

def test_call_gemini_sin_api_key_lanza_value_error(monkeypatch):
    """Sin GEMINI_API_KEY en el entorno debe lanzar ValueError al inicializar."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("agente_scratch.core._gemini_client", None)

    from agente_scratch.core import _init_gemini_client
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        _init_gemini_client()


def test_generar_logica_juego_inyecta_restriccion_de_sprites(gemini_mock):
    """La restricción de sprites debe incluirse en el prompt enviado a Gemini."""
    from agente_scratch.core import generar_logica_juego

    generar_logica_juego("un juego de plataformas", nombres_sprites=["Jugador", "Enemigo"])

    prompt_enviado = gemini_mock.call_args[0][0]
    assert "Jugador" in prompt_enviado
    assert "Enemigo" in prompt_enviado
    assert "SPRITES OBLIGATORIOS" in prompt_enviado
