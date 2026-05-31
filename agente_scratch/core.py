# -*- coding: utf-8 -*-
"""
core.py — Motor principal del Agente Scratch.
Contiene: cliente Gemini, generacion de spec, reparacion, empaquetado y subida a Scratch.
"""

import os
import json
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

ASSETS_DIR = Path("assets")
EXTENSIONES_VALIDAS = (
    "*.svg", "*.png", "*.bmp", "*.jpg", "*.jpeg", "*.gif",
    "*.sprite2", "*.sprite3",
)
SONIDOS_VALIDOS = ("*.mp3", "*.wav")

# ─── Cliente Gemini ───────────────────────────────────────────────────────────
_gemini_client: Optional[genai.Client] = None

# Lee el modelo desde .env — permite cambiarlo sin tocar el codigo
MODELO = os.getenv("MODELO_AGENTE", "gemini-2.5-flash")


def _init_gemini_client() -> genai.Client:
    """Inicializa el cliente Gemini leyendo la API key desde el entorno.

    Returns:
        Cliente Gemini inicializado y listo para usar.

    Raises:
        ValueError: Si GEMINI_API_KEY no está definida en el entorno.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no encontrada en .env")
    global _gemini_client
    _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _call_gemini(prompt: str) -> Dict[str, Any]:
    """Envía un prompt a Gemini y devuelve la respuesta parseada como dict.

    Args:
        prompt: Texto completo del prompt incluyendo el SYSTEM_PROMPT.

    Returns:
        Diccionario con la respuesta JSON de Gemini.

    Raises:
        RuntimeError: Si Gemini devuelve respuesta vacía o JSON inválido.
    """
    global _gemini_client
    if _gemini_client is None:
        _init_gemini_client()
    try:
        response = _gemini_client.models.generate_content(
            model=MODELO,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        if not response.text:
            raise ValueError("Respuesta vacia del modelo")
        return json.loads(response.text.strip())
    except Exception as e:
        raise RuntimeError(f"Error en la generacion: {e}")


# ─── Prompt del sistema ───────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Eres el motor de logica de un generador de proyectos Scratch 3.0.
Recibes una descripcion de juego y devuelves SOLO un objeto JSON valido con la logica de bloques.
Nunca generas el project.json completo. Solo generas la especificacion de bloques por sprite.

REGLAS ABSOLUTAS:
- Responde SOLO con JSON valido. Sin texto, sin markdown, sin explicaciones.
- Usa SOLO opcodes de la lista aprobada. Si algo no es posible, marcalo en advertencias.
- IDs de bloques: formato s{i}_b{nnn} ejemplo: s0_b001, s0_b002
- IDs de variables: formato var_{nombre} ejemplo: var_puntaje
- IDs de broadcasts: formato msg_{nombre} ejemplo: msg_gameover
- Maximo 40 bloques por sprite. Si necesitas mas, usa broadcasts para dividir.
- Maximo 6 sprites totales.
- El nombre del sprite en la respuesta debe coincidir EXACTAMENTE con el nombre que el usuario indique.

OPCODES APROBADOS (usa SOLO estos):

Movimiento:
  motion_movesteps         inputs: {STEPS: [1, [4, "10"]]}
  motion_gotoxy            inputs: {X: [1, [4, "0"]], Y: [1, [4, "0"]]}
  motion_changexby         inputs: {DX: [1, [4, "10"]]}
  motion_changeyby         inputs: {DY: [1, [4, "10"]]}
  motion_setx              inputs: {X: [1, [4, "0"]]}
  motion_sety              inputs: {Y: [1, [4, "0"]]}
  motion_xposition         reporter, sin inputs
  motion_yposition         reporter, sin inputs
  motion_ifonedgebounce    inputs: {}
  motion_pointindirection  inputs: {DIRECTION: [1, [8, "90"]]}
  motion_turnright         inputs: {DEGREES: [1, [8, "15"]]}
  motion_turnleft          inputs: {DEGREES: [1, [8, "15"]]}
  motion_direction         reporter, sin inputs

Control:
  control_forever          inputs: {SUBSTACK: [2, "id_primer_bloque_interno"]}
  control_if               inputs: {CONDITION: [2, "id_cond"], SUBSTACK: [2, "id_si"]}
  control_if_else          inputs: {CONDITION: [2, "id_cond"], SUBSTACK: [2, "id_si"], SUBSTACK2: [2, "id_no"]}
  control_wait             inputs: {DURATION: [1, [5, "0.1"]]}
  control_repeat           inputs: {TIMES: [1, [6, "10"]], SUBSTACK: [2, "id_bloque"]}
  control_repeat_until     inputs: {CONDITION: [2, "id_cond"], SUBSTACK: [2, "id_bloque"]}
  control_stop             fields: {STOP_OPTION: ["all", null]}
  control_wait_until       inputs: {CONDITION: [2, "id_cond"]}

Sensores:
  sensing_keypressed          inputs: {KEY_OPTION: [1, "id_menu_tecla"]}
  sensing_keyoptions          fields: {KEY_OPTION: ["right arrow", null]}
  sensing_touchingobject      inputs: {TOUCHINGOBJECTMENU: [1, "id_menu_objeto"]}
  sensing_touchingobjectmenu  fields: {TOUCHING_OBJECT: ["nombre_sprite", null]}
  sensing_touchingcolor       inputs: {COLOR: [1, [9, "#FF0000"]]}
  sensing_askandwait          inputs: {QUESTION: [1, [10, "Cuanto es 5 + 3?"]]}
  sensing_answer              reporter, sin inputs, sin fields
  sensing_timer               reporter, sin inputs
  sensing_resettimer          inputs: {}
  sensing_mousedown           reporter, sin inputs
  sensing_mousex              reporter, sin inputs
  sensing_mousey              reporter, sin inputs

Operadores:
  operator_add       inputs: {NUM1: [1, [4, "0"]], NUM2: [1, [4, "0"]]}
  operator_subtract  inputs: {NUM1: [1, [4, "0"]], NUM2: [1, [4, "0"]]}
  operator_multiply  inputs: {NUM1: [1, [4, "0"]], NUM2: [1, [4, "0"]]}
  operator_divide    inputs: {NUM1: [1, [4, "0"]], NUM2: [1, [4, "0"]]}
  operator_random    inputs: {FROM: [1, [4, "1"]], TO: [1, [4, "10"]]}
  operator_gt        inputs: {OPERAND1: [1, [4, "0"]], OPERAND2: [1, [4, "50"]]}
  operator_lt        inputs: {OPERAND1: [1, [4, "0"]], OPERAND2: [1, [4, "50"]]}
  operator_equals    inputs: {OPERAND1: [1, [10, "a"]], OPERAND2: [1, [10, "b"]]}
  operator_and       inputs: {OPERAND1: [2, "id_cond1"], OPERAND2: [2, "id_cond2"]}
  operator_or        inputs: {OPERAND1: [2, "id_cond1"], OPERAND2: [2, "id_cond2"]}
  operator_not       inputs: {OPERAND: [2, "id_cond"]}
  operator_join      inputs: {STRING1: [1, [10, "hola"]], STRING2: [1, [10, "mundo"]]}
  operator_letter_of inputs: {LETTER: [1, [6, "1"]], STRING: [1, [10, "mundo"]]}
  operator_length    inputs: {STRING: [1, [10, "mundo"]]}
  operator_contains  inputs: {STRING1: [1, [10, "manzana"]], STRING2: [1, [10, "a"]]}
  operator_mod       inputs: {NUM1: [1, [4, "10"]], NUM2: [1, [4, "3"]]}
  operator_round     inputs: {NUM: [1, [4, "9.5"]]}
  operator_mathop    fields: {OPERATOR: ["sqrt", null]}, inputs: {NUM: [1, [4, "9"]]}

Variables:
  data_setvariableto     fields: {VARIABLE: ["nombre", "id_var"]}, inputs: {VALUE: [1, [10, "0"]]}
  data_changevariableby  fields: {VARIABLE: ["nombre", "id_var"]}, inputs: {VALUE: [1, [4, "1"]]}
  data_variable          fields: {VARIABLE: ["nombre", "id_var"]} reporter
  data_showvariable      fields: {VARIABLE: ["nombre", "id_var"]}
  data_hidevariable      fields: {VARIABLE: ["nombre", "id_var"]}

Eventos:
  event_whenflagclicked        parent: null, topLevel: true, inputs: {}
  event_whenkeypressed         fields: {KEY_OPTION: ["space", null]}, parent: null, topLevel: true
  event_broadcast              inputs: {BROADCAST_INPUT: [1, [11, "nombre_msg", "id_msg"]]}
  event_whenbroadcastreceived  fields: {BROADCAST_OPTION: ["nombre_msg", "id_msg"]}, parent: null, topLevel: true
  event_whenstageclicked       parent: null, topLevel: true, inputs: {}
  event_whenthisspriteclicked  parent: null, topLevel: true, inputs: {}

Apariencia:
  looks_say              inputs: {MESSAGE: [1, [10, "texto"]]}
  looks_sayforsecs       inputs: {MESSAGE: [1, [10, "texto"]], SECS: [1, [4, "2"]]}
  looks_think            inputs: {MESSAGE: [1, [10, "texto"]]}
  looks_thinkforsecs     inputs: {MESSAGE: [1, [10, "texto"]], SECS: [1, [4, "2"]]}
  looks_hide             inputs: {}
  looks_show             inputs: {}
  looks_setsizeto        inputs: {SIZE: [1, [4, "100"]]}
  looks_changesizeby     inputs: {CHANGE: [1, [4, "10"]]}
  looks_switchcostumeto  inputs: {COSTUME: [1, "id_menu_costume"]}
  looks_costume          fields: {COSTUME: ["nombre_costume", null]} shadow: true
  looks_nextcostume      inputs: {}
  looks_seteffectto      fields: {EFFECT: ["color", null]}, inputs: {VALUE: [1, [4, "0"]]}
  looks_changeeffectby   fields: {EFFECT: ["color", null]}, inputs: {CHANGE: [1, [4, "25"]]}
  looks_cleargraphiceffects inputs: {}
  looks_size             reporter, sin inputs
  looks_gotofrontback    fields: {FRONT_BACK: ["front", null]}
  looks_goforwardbackwardlayers fields: {FORWARD_BACKWARD: ["forward", null]}, inputs: {NUM: [1, [4, "1"]]}

Sonido:
  sound_playuntildone    inputs: {SOUND_MENU: [1, "id_menu_sonido"]}
  sound_sounds_menu      fields: {SOUND_MENU: ["Pop", null]} shadow: true
  sound_play             inputs: {SOUND_MENU: [1, "id_menu_sonido"]}
  sound_stopallsounds    inputs: {}
  sound_setvolumeto      inputs: {VOLUME: [1, [4, "100"]]}
  sound_changevolumeby   inputs: {VOLUME: [1, [4, "10"]]}

Mis bloques:
  procedures_definition  topLevel: true, parent: null, inputs: {custom_block: [1, "id_prototype"]}
  procedures_prototype   shadow: true, topLevel: false, mutation con proccode y argumentids
  procedures_call        topLevel: false, mutation con proccode y argumentids

REGLAS DE BLOQUES OBLIGATORIAS:
- Todo bloque tiene: opcode, next, parent, inputs, fields, shadow: false, topLevel
- topLevel: true SOLO en bloques sombrero (event_*, procedures_definition)
- next apunta al ID del bloque siguiente, null si es el ultimo
- parent apunta al ID del bloque anterior, null si es topLevel
- Bloques de menu tienen shadow: true, topLevel: false
- sensing_answer y operator_random son reporters: van dentro de inputs de otros bloques

NUNCA hagas esto:
- Opcodes inventados
- Omitir el campo shadow en cualquier bloque
- topLevel: true en un bloque que tiene parent != null
- Referenciar un ID de bloque que no existe
- Generar mas sprites de los que el usuario indico
- Usar el opcode "text" — NO EXISTE en Scratch 3.0
- Crear bloques sombra separados para literales de texto o numeros

LITERALES DE TEXTO Y NUMEROS — REGLA CRITICA:
Los valores literales (texto, numeros) van SIEMPRE inline dentro del array de inputs.
NUNCA se crean como bloques separados con opcode "text" u otros.

CORRECTO — literal inline:
  "inputs": {"MESSAGE": [1, [10, "Hola mundo"]]}

INCORRECTO — NO hagas esto nunca:
  "inputs": {"MESSAGE": [1, "s0_b_shadow"]},
  "s0_b_shadow": {"opcode": "text", "inputs": {}, "fields": {"TEXT": ["Hola mundo", null]}, "shadow": true}

FORMATO DE INPUTS:
  Texto:       [1, [10, "valor_texto"]]
  Numero:      [1, [4, "42"]]
  Entero:      [1, [6, "10"]]
  Angulo:      [1, [8, "90"]]
  Color:       [1, [9, "#FF0000"]]
  Broadcast:   [1, [11, "nombre_msg", "id_msg"]]
  Reporter:    [1, "id_del_bloque_reporter"] o [2, "id_del_bloque_reporter"]

VARIABLES — FORMATO OBLIGATORIO:
  En el dict "variables" del sprite:
    {"var_puntaje": ["puntaje", 0]}   <- CORRECTO: [nombre_legible, valor_inicial]
    {"var_puntaje": "var_puntaje"}    <- INCORRECTO, nunca asi

  En fields de bloques data_*:
    {"VARIABLE": ["puntaje", "var_puntaje"]}  <- [nombre_legible, id_variable]

BROADCASTS — FORMATO OBLIGATORIO:
  En el dict "broadcasts" del stage o sprite:
    {"msg_gameover": "game_over"}   <- {id_msg: nombre_legible}

  En event_broadcast:
    "inputs": {"BROADCAST_INPUT": [1, [11, "game_over", "msg_gameover"]]}  <- inline, NUNCA bloque separado

  En event_whenbroadcastreceived:
    "fields": {"BROADCAST_OPTION": ["game_over", "msg_gameover"]}

ESTRUCTURA DE RESPUESTA REQUERIDA (devuelve EXACTAMENTE este formato):
{
  "tipo_juego": "puzle",
  "advertencias": [],
  "stage": {
    "variables": {},
    "broadcasts": {}
  },
  "sprites": [
    {
      "nombre": "NombreExactoDelSprite",
      "x": 0,
      "y": 0,
      "variables": {},
      "broadcasts": {},
      "blocks": {}
    }
  ]
}

PATRONES DE JUEGO:

Matematicas con entrada de texto:
  Variables: var_num1, var_num2, var_resultado, var_puntaje
  1. setvariableto var_num1 con operator_random
  2. setvariableto var_num2 con operator_random
  3. setvariableto var_resultado con la operacion
  4. sensing_askandwait con operator_join para construir la pregunta
  5. control_if operator_equals sensing_answer var_resultado
     correcto: sayforsecs "Correcto!", changevariableby puntaje 1
     incorrecto: sayforsecs con operator_join "Incorrecto. Era: " + var_resultado

Gravedad + salto:
  Variables: var_vy, var_en_suelo
  Loop forever: changeyby var_vy, si toca plataforma sety +1 var_vy=0 var_en_suelo=1
  Tecla salto: si var_en_suelo=1 entonces var_vy = fuerza_salto
  Cada tick: changevariableby var_vy -1

Enemigo patrol:
  Loop forever: movesteps velocidad, ifonedgebounce

Game over:
  Loop forever: si toca enemigo broadcast game_over hide
  whenbroadcastreceived game_over: sayforsecs "Game Over" 2, stop all

REGLAS CRITICAS ADICIONALES:

FLUJO SECUENCIAL — NUNCA uses broadcasts para dividir un flujo que debe ser lineal:
  Si el juego tiene un ciclo pregunta→respuesta→verificacion, todo debe ir dentro de un
  control_forever con sensing_askandwait bloqueante. Los broadcasts son NO bloqueantes —
  el hilo que los dispara sigue ejecutandose sin esperar al receptor, lo que rompe la logica.
  CORRECTO: forever { sortear → calcular → askandwait → verificar → feedback }
  INCORRECTO: forever { broadcast ask → wait } + when ask { askandwait } + when check { verificar }

VARIABLE OPERADOR — NUNCA uses texto literal con multiples operadores:
  Si el operador cambia segun una condicion (suma o resta, mayor o menor, etc.),
  SIEMPRE declara una variable var_operador y asignala en cada rama del if/else.
  Luego usala en el join de la pregunta.
  CORRECTO:
    if tipo=1: resultado = num1+num2, var_operador = "+"
    else:      resultado = num1-num2, var_operador = "-"
    askandwait join(num1, join(var_operador, join(num2, " = ?")))
  INCORRECTO:
    askandwait join(num1, join("+ o -", join(num2, " = ?")))

SONIDOS — USA los nombres exactos de los archivos que el usuario proporciono:
  Los nombres de sonido en sound_sounds_menu fields DEBEN coincidir exactamente con
  los nombres que el usuario asigno al configurar el proyecto (sin extension).
  Si el usuario describio multiples sonidos (bienvenida, acierto, error, etc.),
  asigna cada bloque sound_playuntildone al sonido correspondiente segun el contexto.
  Si solo hay un sonido disponible, usalo en todos los bloques de sonido.
  NUNCA inventes nombres como "Correct Sound", "Welcome Music", "Pop" u otros
  que no fueron proporcionados por el usuario.
"""


# ─── Normalizar respuesta de Gemini ──────────────────────────────────────────
def normalizar_spec(raw: Any) -> Dict[str, Any]:
    """Normaliza la respuesta de Gemini al formato canónico de spec.

    Gemini a veces envuelve la respuesta en una clave extra. Esta función
    garantiza que siempre se devuelva un dict con la clave 'sprites'.

    Args:
        raw: Respuesta cruda de Gemini, esperada como dict.

    Returns:
        Diccionario con claves ``tipo_juego``, ``advertencias``, ``stage`` y ``sprites``.

    Raises:
        ValueError: Si ``raw`` no es un diccionario.
    """
    if not isinstance(raw, dict):
        raise ValueError(f"Gemini devolvio tipo inesperado: {type(raw)}")

    if "sprites" in raw:
        return raw

    for val in raw.values():
        if isinstance(val, dict) and "sprites" in val:
            return val

    return {
        "tipo_juego": raw.get("tipo_juego", "desconocido"),
        "advertencias": raw.get("advertencias", [f"Estructura inesperada: {list(raw.keys())}"]),
        "stage": raw.get("stage", {"variables": {}, "broadcasts": {}}),
        "sprites": []
    }


# ─── Reparador de spec ────────────────────────────────────────────────────────
def reparar_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Elimina bloques con opcodes inválidos y repara referencias rotas.

    Red de seguridad post-generación: elimina bloques ``text`` y
    ``event_broadcast_unlinked`` que Gemini genera incorrectamente,
    reconecta los inputs de sus bloques padre con literales inline,
    y declara automáticamente variables usadas pero no declaradas.

    Args:
        spec: Especificación de bloques tal como la devuelve Gemini.

    Returns:
        La misma spec con bloques inválidos eliminados y variables declaradas.
    """
    # Elimina bloques con opcodes invalidos y reconecta referencias.
    OPCODES_INVALIDOS = {"text", "event_broadcast_unlinked"}

    for sprite in spec.get("sprites", []):
        bloques: Dict[str, Any] = sprite.get("blocks", {})
        variables_declaradas: Dict[str, Any] = sprite.get("variables", {})

        bloques_invalidos: Dict[str, Any] = {}
        for bid, bloque in list(bloques.items()):
            if bloque.get("opcode") in OPCODES_INVALIDOS:
                valor = None
                fields = bloque.get("fields", {})
                if "TEXT" in fields:
                    valor = fields["TEXT"][0]
                elif "VALUE" in fields:
                    valor = fields["VALUE"][0]
                bloques_invalidos[bid] = {"valor": valor, "opcode": bloque.get("opcode")}

        if not bloques_invalidos:
            _declarar_variables_faltantes(bloques, variables_declaradas)
            sprite["variables"] = variables_declaradas
            continue

        for bid, bloque in bloques.items():
            if bid in bloques_invalidos:
                continue
            inputs = bloque.get("inputs", {})
            for key, val in list(inputs.items()):
                if not isinstance(val, list) or len(val) < 2:
                    continue
                ref = val[1]
                if isinstance(ref, str) and ref in bloques_invalidos:
                    texto = bloques_invalidos[ref]["valor"] or ""
                    inputs[key] = [1, [10, str(texto)]]

        for bid in bloques_invalidos:
            bloques.pop(bid, None)

        _declarar_variables_faltantes(bloques, variables_declaradas)
        sprite["variables"] = variables_declaradas

    stage_bloques = spec.get("stage", {}).get("blocks", {})
    stage_vars = spec.get("stage", {}).get("variables", {})
    if stage_bloques:
        _declarar_variables_faltantes(stage_bloques, stage_vars)
        spec["stage"]["variables"] = stage_vars

    return spec


def _declarar_variables_faltantes(bloques: Dict[str, Any],
                                   variables: Dict[str, Any]) -> None:
    # Escanea fields VARIABLE y declara las que faltan con valor inicial 0
    for bloque in bloques.values():
        fields = bloque.get("fields", {})
        if "VARIABLE" in fields:
            campo = fields["VARIABLE"]
            if isinstance(campo, list) and len(campo) >= 2:
                nombre_legible = campo[0]
                var_id = campo[1]
                if var_id and var_id not in variables:
                    variables[var_id] = [nombre_legible, 0]


# ─── Lectura de assets ────────────────────────────────────────────────────────
def leer_asset(ruta: Path, nombre: str) -> Dict[str, Any]:
    """Lee un archivo de sprite y devuelve sus bytes y metadatos.

    Soporta formatos .sprite3 (ZIP con sprite.json), .png y .svg.
    Calcula el hash MD5 para el nombre de archivo requerido por Scratch.

    Args:
        ruta: Ruta absoluta al archivo del sprite.
        nombre: Nombre del sprite (usado para logging).

    Returns:
        Diccionario con claves ``bytes``, ``hash``, ``filename``,
        ``formato``, ``rotationCenterX`` y ``rotationCenterY``.
    """
    ext = ruta.suffix.lower()
    if ext == ".sprite3":
        with zipfile.ZipFile(ruta, "r") as z:
            sj = json.loads(z.read("sprite.json"))
            costume = sj["costumes"][0]
            fmt = costume["dataFormat"]
            ab = z.read(f"{costume['assetId']}.{fmt}")
            rx = costume.get("rotationCenterX", 48)
            ry = costume.get("rotationCenterY", 48)
        h = hashlib.md5(ab).hexdigest()
        return {"bytes": ab, "hash": h, "filename": f"{h}.{fmt}",
                "formato": fmt, "rotationCenterX": rx, "rotationCenterY": ry}
    elif ext in (".png", ".bmp", ".jpg", ".jpeg", ".gif"):
        # Todos los formatos bitmap se tratan igual que PNG en Scratch
        fmt = ext.lstrip(".")
        if fmt == "jpeg":
            fmt = "jpg"
        ab = ruta.read_bytes()
        h = hashlib.md5(ab).hexdigest()
        return {"bytes": ab, "hash": h, "filename": f"{h}.{fmt}",
                "formato": fmt, "rotationCenterX": 48, "rotationCenterY": 48}
    else:
        # SVG y cualquier otro formato vectorial
        ab = ruta.read_bytes()
        h = hashlib.md5(ab).hexdigest()
        return {"bytes": ab, "hash": h, "filename": f"{h}.svg",
                "formato": "svg", "rotationCenterX": 48, "rotationCenterY": 50}


# ─── Lectura de sonidos ───────────────────────────────────────────────────────
def leer_sonido(ruta: Path, nombre: str) -> Dict[str, Any]:
    """Lee un archivo de sonido y devuelve sus bytes y metadatos para Scratch.

    Soporta .mp3 y .wav. Calcula el hash MD5 requerido por Scratch.

    Args:
        ruta: Ruta absoluta al archivo de sonido.
        nombre: Nombre del sonido que aparecerá en Scratch.

    Returns:
        Diccionario con claves ``bytes``, ``hash``, ``filename``,
        ``formato`` y ``nombre``.
    """
    ext = ruta.suffix.lower()
    fmt = "mp3" if ext == ".mp3" else "wav"
    ab = ruta.read_bytes()
    h = hashlib.md5(ab).hexdigest()
    return {"bytes": ab, "hash": h, "filename": f"{h}.{fmt}",
            "formato": fmt, "nombre": nombre}


# ─── Generacion de logica ─────────────────────────────────────────────────────
def generar_logica_juego(
    descripcion: str,
    nombres_sprites: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Genera la especificación de bloques Scratch desde lenguaje natural.

    Construye el prompt con el SYSTEM_PROMPT del dominio, inyecta la
    restricción de sprites si se proporcionan, llama a Gemini, normaliza
    la respuesta y repara opcodes inválidos.

    Args:
        descripcion: Texto libre que describe el juego a generar.
        nombres_sprites: Nombres exactos de los sprites a incluir.
            Si es None, Gemini elige la cantidad y nombres.

    Returns:
        Diccionario con claves ``tipo_juego``, ``advertencias``,
        ``stage`` y ``sprites``.

    Raises:
        RuntimeError: Si Gemini devuelve una respuesta vacía o inválida.
    """
    # Inyecta restriccion de sprites para que Gemini use EXACTAMENTE los indicados
    if nombres_sprites:
        lista = ", ".join(f'"{n}"' for n in nombres_sprites)
        restriccion = (
            f"\n\nSPRITES OBLIGATORIOS: Genera logica SOLO para estos {len(nombres_sprites)} "
            f"sprite(s): [{lista}]. "
            f"No crees sprites adicionales. No cambies los nombres. "
            f"El campo 'nombre' en cada sprite de tu respuesta debe ser EXACTAMENTE uno de estos."
        )
    else:
        restriccion = ""

    raw = _call_gemini(f"{SYSTEM_PROMPT}\n\nDescripcion del juego: {descripcion}{restriccion}")
    spec = normalizar_spec(raw)
    spec = reparar_spec(spec)
    return spec


# ─── Empaquetado .sb3 ─────────────────────────────────────────────────────────
def empaquetar_sb3(
    spec: Dict[str, Any],
    assets: List[Dict[str, str]],
    output: str,
    sonidos: Optional[List[Dict[str, str]]] = None,
    log_fn=print,
) -> Dict[str, Any]:
    """Empaqueta una spec de bloques en un archivo .sb3 listo para Scratch.

    Construye el project.json con los targets (Stage + sprites), incluye
    los assets de imagen y sonido, y comprime todo en un ZIP con extensión .sb3.
    Si un asset no existe, usa un SVG de fallback azul.

    Args:
        spec: Especificación de bloques generada por ``generar_logica_juego``.
        assets: Lista de dicts con claves ``nombre`` y ``path`` (sprites).
        output: Ruta del archivo .sb3 de salida (con extensión).
        sonidos: Lista de dicts con claves ``sprite``, ``nombre`` y ``path``.
            ``sprite`` indica a qué sprite pertenece el sonido.
            Si es None, ningún sprite tendrá sonidos.
        log_fn: Función de logging, por defecto ``print``.

    Returns:
        Diccionario con claves ``success``, ``archivo``, ``tamanio_bytes``,
        ``sprites``, ``tipo_juego`` y ``advertencias``.
    """
    backdrop = b'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><rect width="480" height="360" fill="#FFFFFF"/></svg>'
    bh = hashlib.md5(backdrop).hexdigest()

    # ─── Carga de assets de imagen ────────────────────────────────────────────
    asset_map: Dict[str, Dict] = {}
    for item in assets:
        nombre = item["nombre"]
        ruta = Path(item["path"])
        if not ruta.exists():
            log_fn(f"Advertencia: {ruta.name} no encontrado, usando cuadrado")
            sb = (f'<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60">'
                  f'<rect width="60" height="60" fill="#4C97FF"/></svg>').encode()
            sh = hashlib.md5(sb).hexdigest()
            asset_map[nombre] = {"bytes": sb, "hash": sh,
                                 "filename": f"{sh}.svg", "formato": "svg",
                                 "rotationCenterX": 48, "rotationCenterY": 50}
        else:
            asset_map[nombre] = leer_asset(ruta, nombre)

    # ─── Carga de sonidos agrupados por sprite ────────────────────────────────
    # sonido_map: {nombre_sprite: [dict_sonido, ...]}
    sonido_map: Dict[str, List[Dict]] = {}
    for item in (sonidos or []):
        nombre_sprite = item["sprite"]
        ruta = Path(item["path"])
        if not ruta.exists():
            log_fn(f"Advertencia: sonido {ruta.name} no encontrado, se omite")
            continue
        sd = leer_sonido(ruta, item["nombre"])
        sonido_map.setdefault(nombre_sprite, []).append(sd)

    targets = [{
        "isStage": True, "name": "Stage",
        "variables": spec.get("stage", {}).get("variables", {}),
        "lists": {}, "broadcasts": spec.get("stage", {}).get("broadcasts", {}),
        "blocks": {}, "comments": {}, "currentCostume": 0,
        "costumes": [{"name": "backdrop1", "dataFormat": "svg",
                      "assetId": bh, "md5ext": f"{bh}.svg",
                      "rotationCenterX": 240, "rotationCenterY": 180}],
        "sounds": [], "volume": 100, "layerOrder": 0,
        "tempo": 60, "videoTransparency": 50, "videoState": "on",
        "textToSpeechLanguage": None
    }]

    sprites_spec = spec.get("sprites", [])
    for i, sprite in enumerate(sprites_spec):
        nombre = sprite.get("nombre", f"Sprite{i}")

        # Busca el asset de imagen para este sprite
        ad = None
        for key, val in asset_map.items():
            if key.lower() == nombre.lower():
                ad = val
                break
        if ad is None and asset_map:
            ad = list(asset_map.values())[0]
            log_fn(f"Advertencia: '{nombre}' sin asset, usando el primero")
        elif ad is None:
            fb = b'<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"><rect width="60" height="60" fill="#FF6680"/></svg>'
            fh = hashlib.md5(fb).hexdigest()
            ad = {"bytes": fb, "hash": fh, "filename": f"{fh}.svg",
                  "formato": "svg", "rotationCenterX": 48, "rotationCenterY": 50}

        # Construye la lista de sonidos en formato Scratch
        sounds_scratch = []
        for idx, sd in enumerate(sonido_map.get(nombre, [])):
            sounds_scratch.append({
                "name": sd["nombre"],
                "assetId": sd["hash"],
                "dataFormat": sd["formato"],
                "md5ext": sd["filename"],
                "rate": 44100,
                "sampleCount": 0,
            })

        br = 2 if ad["formato"] in ("png", "bmp", "jpg", "jpeg", "gif") else 1
        targets.append({
            "isStage": False, "name": nombre,
            "variables": sprite.get("variables", {}),
            "lists": {}, "broadcasts": sprite.get("broadcasts", {}),
            "blocks": sprite.get("blocks", {}),
            "comments": {}, "currentCostume": 0,
            "costumes": [{"name": "costume1", "bitmapResolution": br,
                          "dataFormat": ad["formato"], "assetId": ad["hash"],
                          "md5ext": ad["filename"],
                          "rotationCenterX": ad["rotationCenterX"],
                          "rotationCenterY": ad["rotationCenterY"]}],
            "sounds": sounds_scratch, "volume": 100, "layerOrder": i + 1,
            "visible": True, "x": sprite.get("x", 0), "y": sprite.get("y", 0),
            "size": 100, "direction": 90, "draggable": False,
            "rotationStyle": "all around"
        })

    pd = {"targets": targets, "monitors": [], "extensions": [],
          "meta": {"semver": "3.0.0", "vm": "13.7.4-svg", "agent": "Mozilla/5.0"}}

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json", json.dumps(pd, ensure_ascii=False, indent=2))
        zf.writestr(f"{bh}.svg", backdrop)
        seen: set = set()
        # Escribe assets de imagen
        for ad in asset_map.values():
            if ad["filename"] not in seen:
                zf.writestr(ad["filename"], ad["bytes"])
                seen.add(ad["filename"])
        # Escribe archivos de sonido
        for sds in sonido_map.values():
            for sd in sds:
                if sd["filename"] not in seen:
                    zf.writestr(sd["filename"], sd["bytes"])
                    seen.add(sd["filename"])

    size = Path(output).stat().st_size
    return {"success": True, "archivo": str(Path(output).resolve()),
            "tamanio_bytes": size, "sprites": len(sprites_spec),
            "tipo_juego": spec.get("tipo_juego", "desconocido"),
            "advertencias": spec.get("advertencias", [])}


# ─── Subida a Scratch ─────────────────────────────────────────────────────────
def subir_a_scratch(ruta_sb3: str, titulo: str) -> Dict[str, Any]:
    """Sube un archivo .sb3 a la cuenta de Scratch del usuario.

    Usa scratchattach solo para autenticación (cookies y headers).
    Las llamadas HTTP se hacen directamente con requests en 3 pasos:
    crear proyecto vacío, subir assets, actualizar project.json.
    El proyecto siempre se crea como PRIVADO.

    Args:
        ruta_sb3: Ruta al archivo .sb3 generado.
        titulo: Título del proyecto en Scratch.

    Returns:
        Diccionario con ``success`` (bool), ``url`` e ``id`` si exitoso,
        o ``error`` (str) si falló.
    """
    # Usa scratchattach solo para autenticacion. La subida se hace con requests directo.
    username = os.getenv("SCRATCH_USERNAME", "").strip()
    password = os.getenv("SCRATCH_PASSWORD", "").strip()

    if not username or not password:
        return {"success": False, "error": "Credenciales no configuradas en .env"}

    try:
        import scratchattach as sa
    except ImportError:
        return {"success": False,
                "error": "scratchattach no instalado. Ejecuta: pip install scratchattach==2.1.17"}

    import warnings
    warnings.filterwarnings("ignore")

    try:
        sesion = sa.login(username, password)
    except Exception:
        return {"success": False, "error": "Usuario o contrasena incorrectos"}

    try:
        import requests as req

        cookies = sesion._cookies
        headers = sesion._headers

        # Paso 1: Crear proyecto vacio y obtener ID
        r1 = req.post(
            "https://projects.scratch.mit.edu/",
            params={"title": titulo},
            headers=headers,
            cookies=cookies,
            timeout=15
        )
        if r1.status_code != 200:
            return {"success": False, "error": f"No se pudo crear el proyecto ({r1.status_code})"}

        project_id = r1.json().get("id") or r1.json().get("content-name")
        if not project_id:
            return {"success": False, "error": "No se obtuvo ID del proyecto"}

        # Paso 2: Subir assets del .sb3
        with zipfile.ZipFile(ruta_sb3, "r") as z:
            for nombre in z.namelist():
                if nombre == "project.json":
                    continue
                ext = nombre.split(".")[-1] if "." in nombre else "svg"
                mime = "image/png" if ext == "png" else "image/svg+xml"
                datos = z.read(nombre)
                req.post(
                    f"https://assets.scratch.mit.edu/{nombre}",
                    headers={**headers, "Content-Type": mime},
                    cookies=cookies,
                    data=datos,
                    timeout=15
                )

        # Paso 3: Subir el project.json real
        with zipfile.ZipFile(ruta_sb3, "r") as z:
            project_json = z.read("project.json")

        r3 = req.put(
            f"https://projects.scratch.mit.edu/{project_id}",
            headers={**headers, "Content-Type": "application/json"},
            cookies=cookies,
            data=project_json,
            timeout=15
        )
        if r3.status_code != 200:
            return {"success": False, "error": f"Error al actualizar el proyecto ({r3.status_code})"}

        url = f"https://scratch.mit.edu/projects/{project_id}/"
        return {"success": True, "url": url, "id": project_id}

    except req.exceptions.ConnectionError:
        return {"success": False, "error": "No se pudo conectar con Scratch. Intenta mas tarde."}
    except req.exceptions.Timeout:
        return {"success": False, "error": "Tiempo de espera agotado. Intenta mas tarde."}
    except Exception as e:
        return {"success": False, "error": str(e)}
