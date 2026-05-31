# -*- coding: utf-8 -*-
"""
agent/mcp_server.py — Servidor FastMCP para Agente Scratch.
Expone las herramientas del agente como servidor MCP compatible con
Claude Desktop y cualquier cliente MCP.

Modos de ejecucion:
  agentescratch-mcp          -> modo stdio (Claude Desktop)
  agentescratch-mcp --http   -> modo HTTP en puerto 8000
"""

import os
import sys
import json

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from agente_scratch import VERSION, AUTOR
from agente_scratch.core import ASSETS_DIR, EXTENSIONES_VALIDAS, SONIDOS_VALIDOS
from agente_scratch.agent.graph import ejecutar_agente
from agente_scratch.agent.tools import OPCODES_VALIDOS

load_dotenv()

mcp = FastMCP(
    name="Agente Scratch",
    instructions=(
        "Soy el Agente Scratch. Genero proyectos .sb3 para Scratch 3.0 a partir "
        "de descripciones en lenguaje natural. "
        "Puedo listar los sprites disponibles, generar la logica del juego, "
        "validarla y empaquetarla en un archivo .sb3 listo para importar en Scratch. "
        "Coloca tus archivos de sprites (.svg, .png, .bmp, .jpg, .gif, .sprite2, .sprite3) "
        "en la carpeta assets/ antes de generar."
    )
)


@mcp.tool()
def listar_sprites_disponibles() -> str:
    """
    Lista los sprites y sonidos disponibles en la carpeta assets/.
    Usar primero para saber con que assets se puede trabajar.
    Sprites: .svg, .png, .bmp, .jpg, .gif, .sprite2, .sprite3
    Sonidos: .mp3, .wav
    """
    if not ASSETS_DIR.exists():
        return "La carpeta assets/ no existe. Creala y coloca tus sprites y sonidos ahi."

    sprites = sorted(set(
        f.name for pat in EXTENSIONES_VALIDAS
        for f in ASSETS_DIR.glob(pat)
    ))
    sonidos = sorted(set(
        f.name for pat in SONIDOS_VALIDOS
        for f in ASSETS_DIR.glob(pat)
    ))

    if not sprites and not sonidos:
        return "No hay archivos en assets/. Coloca sprites (.svg, .png...) o sonidos (.mp3, .wav)."

    lineas = []
    if sprites:
        lineas.append("Sprites disponibles:")
        for i, nombre in enumerate(sprites, 1):
            lineas.append(f"  {i}. {nombre}")
    if sonidos:
        lineas.append("\nSonidos disponibles:")
        for i, nombre in enumerate(sonidos, 1):
            lineas.append(f"  {i}. {nombre}")
    lineas.append(f"\nTotal: {len(sprites)} sprite(s), {len(sonidos)} sonido(s)")
    return "\n".join(lineas)


@mcp.tool()
def generar_proyecto(
    descripcion: str,
    sprites: str,
    nombre_archivo: str = "mi_juego"
) -> str:
    """
    Genera un proyecto Scratch (.sb3) completo a partir de una descripcion.
    El agente genera la logica, la valida y la empaqueta automaticamente.
    Si encuentra errores los corrige solo (hasta 3 reintentos).

    Args:
        descripcion: Descripcion del juego en lenguaje natural.
        sprites: Nombres de los sprites separados por coma, tal como aparecen en assets/.
        nombre_archivo: Nombre del .sb3 a generar (sin extension). Default: mi_juego
    """
    nombres = [n.strip() for n in sprites.split(",") if n.strip()]

    if not nombres:
        return "Error: debes indicar al menos un nombre de sprite."

    resultado = ejecutar_agente(
        descripcion=descripcion,
        nombres_sprites=nombres,
        nombre_salida=nombre_archivo
    )

    if resultado.get("success"):
        reintentos = resultado.get("reintentos_usados", 0)
        correcciones = f" (con {reintentos} correcciones)" if reintentos > 0 else ""
        return (
            f"Proyecto generado exitosamente{correcciones}.\n"
            f"Archivo: {resultado['archivo']}\n"
            f"Tipo de juego: {resultado.get('tipo_juego', 'desconocido')}\n"
            f"Sprites: {resultado.get('sprites', len(nombres))}\n\n"
            f"Para usarlo en Scratch:\n"
            f"  1. Abre scratch.mit.edu\n"
            f"  2. File → Load from computer\n"
            f"  3. Selecciona: {nombre_archivo}.sb3"
        )
    else:
        errores = resultado.get("errores_validacion", [])
        errores_txt = "\n".join(f"  - {e}" for e in errores) if errores else "  Error desconocido"
        return (
            f"No se pudo generar el proyecto despues de {resultado.get('reintentos_usados', 0)} reintentos.\n"
            f"Errores encontrados:\n{errores_txt}\n\n"
            f"Sugerencia: simplifica la descripcion o reduce la cantidad de sprites."
        )


@mcp.tool()
def validar_proyecto(spec_json: str) -> str:
    """
    Valida una especificacion JSON de bloques Scratch.
    Util para depurar si se tiene una spec en JSON y se quiere verificar
    antes de empaquetar manualmente.

    Args:
        spec_json: El JSON de la especificacion generada.
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return f"JSON invalido: {e}"

    errores = []

    for sprite in spec.get("sprites", []):
        nombre_sprite = sprite.get("nombre", "desconocido")
        bloques = sprite.get("blocks", {})
        ids_existentes = set(bloques.keys())
        variables_declaradas = set(sprite.get("variables", {}).keys())

        for bid, bloque in bloques.items():
            opcode = bloque.get("opcode", "")
            if opcode not in OPCODES_VALIDOS:
                errores.append(f"[{nombre_sprite}] OPCODE INVALIDO: '{opcode}' en {bid}")
            for key, val in bloque.get("inputs", {}).items():
                if isinstance(val, list) and len(val) >= 2:
                    ref = val[1]
                    if isinstance(ref, str) and ref not in ids_existentes:
                        errores.append(f"[{nombre_sprite}] Referencia inexistente: '{ref}' en {bid}.inputs.{key}")
            fields = bloque.get("fields", {})
            if "VARIABLE" in fields:
                campo = fields["VARIABLE"]
                if isinstance(campo, list) and len(campo) >= 2:
                    var_id = campo[1]
                    if var_id and var_id not in variables_declaradas:
                        errores.append(f"[{nombre_sprite}] Variable no declarada: '{var_id}' en {bid}")

    if errores:
        lineas = [f"Se encontraron {len(errores)} error(es):"]
        for e in errores:
            lineas.append(f"  - {e}")
        return "\n".join(lineas)

    return "Spec valida. No se encontraron errores."


@mcp.tool()
def info_agente() -> str:
    """
    Muestra informacion sobre el Agente Scratch: version, capacidades,
    formato de sprites soportado y como configurarlo.
    """
    return f"""
Agente Scratch v{VERSION}
Autor: {AUTOR}

CAPACIDADES:
  - Genera proyectos .sb3 para Scratch 3.0 desde lenguaje natural
  - Valida y corrige automaticamente errores de bloques (hasta 3 reintentos)
  - Soporta sprites en .svg, .png, .bmp, .jpg, .gif, .sprite2 y .sprite3
  - Usa Gemini 2.5 Flash como modelo de generacion

COMO USAR:
  1. Coloca tus sprites en la carpeta assets/
  2. Llama listar_sprites_disponibles() para ver que hay
  3. Llama generar_proyecto() con tu descripcion y los nombres de sprites
  4. El .sb3 se guarda en la carpeta del proyecto

CONFIGURACION (.env):
  GEMINI_API_KEY    = tu clave de API de Google
  MAX_REINTENTOS    = 3 (por defecto)
  MODELO_AGENTE     = gemini-2.5-flash (por defecto)
""".strip()


def main() -> None:
    """Punto de entrada del servidor MCP.

    Lanza el servidor en modo stdio (para Claude Desktop) o en modo HTTP
    si se pasa el flag ``--http``. El puerto HTTP se configura con
    la variable de entorno ``MCP_PORT`` (default: 8000).
    """
    if "--http" in sys.argv:
        puerto = int(os.getenv("MCP_PORT", "8000"))
        print(f"Servidor MCP HTTP iniciado en http://localhost:{puerto}")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=puerto)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
