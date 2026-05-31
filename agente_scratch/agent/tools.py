# -*- coding: utf-8 -*-
"""
agent/tools.py — Herramientas LangChain que envuelven el motor del Agente Scratch.
Cada @tool es una accion que el agente LangGraph puede invocar de forma autonoma.
"""

import json
from typing import Annotated

from langchain_core.tools import tool

from agente_scratch.core import (
    generar_logica_juego,
    empaquetar_sb3,
    ASSETS_DIR,
    EXTENSIONES_VALIDAS,
    SONIDOS_VALIDOS,
)

# Opcodes validos segun el SYSTEM_PROMPT — se usan para validar la spec
OPCODES_VALIDOS = {
    "motion_movesteps", "motion_gotoxy", "motion_changexby", "motion_changeyby",
    "motion_setx", "motion_sety", "motion_xposition", "motion_yposition",
    "motion_ifonedgebounce", "motion_pointindirection", "motion_turnright",
    "motion_turnleft", "motion_direction",
    "control_forever", "control_if", "control_if_else", "control_wait",
    "control_repeat", "control_repeat_until", "control_stop", "control_wait_until",
    "sensing_keypressed", "sensing_keyoptions", "sensing_touchingobject",
    "sensing_touchingobjectmenu", "sensing_touchingcolor", "sensing_askandwait",
    "sensing_answer", "sensing_timer", "sensing_resettimer", "sensing_mousedown",
    "sensing_mousex", "sensing_mousey",
    "operator_add", "operator_subtract", "operator_multiply", "operator_divide",
    "operator_random", "operator_gt", "operator_lt", "operator_equals",
    "operator_and", "operator_or", "operator_not", "operator_join",
    "operator_letter_of", "operator_length", "operator_contains",
    "operator_mod", "operator_round", "operator_mathop",
    "data_setvariableto", "data_changevariableby", "data_variable",
    "data_showvariable", "data_hidevariable",
    "event_whenflagclicked", "event_whenkeypressed", "event_broadcast",
    "event_whenbroadcastreceived", "event_whenstageclicked",
    "event_whenthisspriteclicked",
    "looks_say", "looks_sayforsecs", "looks_think", "looks_thinkforsecs",
    "looks_hide", "looks_show", "looks_setsizeto", "looks_changesizeby",
    "looks_switchcostumeto", "looks_costume", "looks_nextcostume",
    "looks_seteffectto", "looks_changeeffectby", "looks_cleargraphiceffects",
    "looks_size", "looks_gotofrontback", "looks_goforwardbackwardlayers",
    "sound_playuntildone", "sound_sounds_menu", "sound_play",
    "sound_stopallsounds", "sound_setvolumeto", "sound_changevolumeby",
    "procedures_definition", "procedures_prototype", "procedures_call",
}


@tool
def listar_assets() -> str:
    """Lista los sprites y sonidos disponibles en assets/ en formato JSON.

    Returns:
        JSON con claves ``sprites`` (lista), ``sonidos`` (lista) y sus totales,
        o ``mensaje`` si la carpeta no existe o está vacía.
    """
    if not ASSETS_DIR.exists():
        return json.dumps({"sprites": [], "sonidos": [], "mensaje": "La carpeta assets/ no existe."})

    sprites = sorted(set(
        f.name for pat in EXTENSIONES_VALIDAS
        for f in ASSETS_DIR.glob(pat)
    ))
    sonidos = sorted(set(
        f.name for pat in SONIDOS_VALIDOS
        for f in ASSETS_DIR.glob(pat)
    ))

    if not sprites and not sonidos:
        return json.dumps({
            "sprites": [], "sonidos": [],
            "mensaje": "assets/ esta vacia. Coloca archivos de imagen o audio."
        })

    return json.dumps({
        "sprites": sprites, "total_sprites": len(sprites),
        "sonidos": sonidos, "total_sonidos": len(sonidos),
    })


@tool
def generar_spec(
    descripcion: Annotated[str, "Descripcion del juego en lenguaje natural"],
    nombres_sprites: Annotated[str, "Nombres de sprites separados por coma. Ejemplo: Profesor,Canasta"],
) -> str:
    """Genera la especificación de bloques Scratch desde una descripción en lenguaje natural.

    Llama a ``generar_logica_juego`` del motor y serializa el resultado a JSON.
    Usar ANTES de ``validar_spec`` y ``empaquetar``.

    Args:
        descripcion: Texto libre que describe el juego a generar.
        nombres_sprites: Nombres de sprites separados por coma.

    Returns:
        JSON con la spec generada, o JSON con clave ``error`` si falló.
    """
    nombres = [n.strip() for n in nombres_sprites.split(",") if n.strip()]
    if not nombres:
        return json.dumps({"error": "Debes proporcionar al menos un nombre de sprite."})

    try:
        spec = generar_logica_juego(descripcion, nombres_sprites=nombres)
        return json.dumps(spec, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def validar_spec(spec_json: Annotated[str, "Spec JSON generada por generar_spec"]) -> str:
    """Valida una spec de bloques Scratch buscando errores estructurales.

    Verifica opcodes inválidos, referencias a bloques inexistentes
    y variables usadas pero no declaradas.

    Args:
        spec_json: JSON de la spec generada por ``generar_spec``.

    Returns:
        JSON con ``valido`` (bool), ``errores`` (lista) y ``total_errores``.
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return json.dumps({"valido": False, "errores": [f"JSON invalido: {e}"]})

    errores = []

    for sprite in spec.get("sprites", []):
        nombre_sprite = sprite.get("nombre", "desconocido")
        bloques = sprite.get("blocks", {})
        ids_existentes = set(bloques.keys())
        variables_declaradas = set(sprite.get("variables", {}).keys())

        for bid, bloque in bloques.items():
            opcode = bloque.get("opcode", "")

            if opcode not in OPCODES_VALIDOS:
                errores.append(f"[{nombre_sprite}] OPCODE INVALIDO: '{opcode}' en bloque {bid}")

            for key, val in bloque.get("inputs", {}).items():
                if isinstance(val, list) and len(val) >= 2:
                    ref = val[1]
                    if isinstance(ref, str) and ref not in ids_existentes:
                        errores.append(
                            f"[{nombre_sprite}] Referencia inexistente: '{ref}' en {bid}.inputs.{key}"
                        )

            fields = bloque.get("fields", {})
            if "VARIABLE" in fields:
                campo = fields["VARIABLE"]
                if isinstance(campo, list) and len(campo) >= 2:
                    var_id = campo[1]
                    if var_id and var_id not in variables_declaradas:
                        errores.append(
                            f"[{nombre_sprite}] Variable no declarada: '{var_id}' usada en {bid}"
                        )

    if errores:
        return json.dumps({"valido": False, "errores": errores, "total_errores": len(errores)})

    return json.dumps({"valido": True, "errores": [], "mensaje": "Spec valida. Lista para empaquetar."})


@tool
def empaquetar(
    spec_json: Annotated[str, "Spec JSON validada por validar_spec"],
    asignacion_sprites: Annotated[str, "Pares nombre:archivo separados por coma. Ejemplo: Profesor:Cat.sprite3"],
    nombre_salida: Annotated[str, "Nombre del archivo de salida sin extension. Ejemplo: mi_juego"],
    asignacion_sonidos: Annotated[str, "Pares sprite|nombre|archivo separados por coma. Ejemplo: Profesor|Pop|pop.mp3. Vacio si no hay sonidos."] = "",
) -> str:
    """Empaqueta la spec validada en un archivo .sb3 listo para importar en Scratch.

    Usar solo después de que ``validar_spec`` confirme que no hay errores.

    Args:
        spec_json: JSON de la spec validada.
        asignacion_sprites: Pares ``nombre:archivo`` separados por coma.
        nombre_salida: Nombre del .sb3 sin extensión.
        asignacion_sonidos: Pares ``sprite|nombre|archivo`` separados por coma. Opcional.

    Returns:
        JSON con ``success``, ``archivo``, ``tamanio_bytes`` y ``log``.
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return json.dumps({"success": False, "error": f"JSON invalido: {e}"})

    assets_lista = []
    for par in asignacion_sprites.split(","):
        par = par.strip()
        if ":" not in par:
            continue
        nombre, archivo = par.split(":", 1)
        ruta = str(ASSETS_DIR / archivo.strip())
        assets_lista.append({"nombre": nombre.strip(), "path": ruta})

    if not assets_lista:
        return json.dumps({"success": False, "error": "No se pudo parsear la asignacion de sprites."})

    sonidos_lista = []
    for par in (asignacion_sonidos or "").split(","):
        par = par.strip()
        if "|" not in par:
            continue
        partes = par.split("|", 2)
        if len(partes) == 3:
            sprite, nombre_snd, archivo = partes
            sonidos_lista.append({
                "sprite": sprite.strip(),
                "nombre": nombre_snd.strip(),
                "path": str(ASSETS_DIR / archivo.strip()),
            })

    nombre_out = nombre_salida.strip()
    if not nombre_out.endswith(".sb3"):
        nombre_out += ".sb3"

    mensajes_log = []
    resultado = empaquetar_sb3(
        spec, assets_lista, nombre_out,
        sonidos=sonidos_lista or None,
        log_fn=mensajes_log.append,
    )
    resultado["log"] = mensajes_log
    return json.dumps(resultado, ensure_ascii=False)
