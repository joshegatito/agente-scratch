# -*- coding: utf-8 -*-
"""
cli/app.py — Interfaz de terminal del Agente Scratch.
Bienvenida y ayuda con Textual (dinamica). Flujo interactivo con print/input.
"""

import sys
from pathlib import Path

from agente_scratch import VERSION, AUTOR
from agente_scratch.core import (
    ASSETS_DIR, EXTENSIONES_VALIDAS, SONIDOS_VALIDOS, MODELO,
    generar_logica_juego, empaquetar_sb3, subir_a_scratch,
)

# ─── Ruta de la imagen del gato ──────────────────────────────────────────────
_GATO_PNG = Path(__file__).parent.parent.parent / "scratch.png"
_ANCHO_GATO = 16


# ─── Render del gato con Pillow ──────────────────────────────────────────────

def _render_gato(ancho: int = _ANCHO_GATO) -> str:
    """Convierte scratch.png a bloques Unicode con markup de Textual."""
    if not _GATO_PNG.exists():
        return "[#FF8C1A]=^.^=[/]"
    try:
        from PIL import Image
        img = Image.open(_GATO_PNG).convert("RGBA")
        ratio = img.height / img.width
        alto = int(ancho * ratio * 0.55)
        img = img.resize((ancho, alto * 2), Image.LANCZOS)
        lineas = []
        for y in range(0, alto * 2, 2):
            linea = ""
            for x in range(ancho):
                _, _, _, a1 = img.getpixel((x, y))
                _, _, _, a2 = img.getpixel((x, y + 1))
                if a1 < 30 and a2 < 30:
                    linea += " "
                elif a1 < 30:
                    linea += "[#FF8C1A]▄[/]"
                elif a2 < 30:
                    linea += "[#FF8C1A]▀[/]"
                else:
                    linea += "[#FF8C1A]█[/]"
            lineas.append(linea)
        return "\n".join(lineas)
    except ImportError:
        return "[#FF8C1A]=^.^=[/]"


# ─── Bienvenida Textual ──────────────────────────────────────────────────────

def mostrar_bienvenida() -> None:
    """Muestra la pantalla de bienvenida con Textual — se ajusta al tamaño de la ventana."""
    from textual.app import App, ComposeResult
    from textual.widgets import Static
    from textual.containers import Horizontal

    gato_str = _render_gato(_ANCHO_GATO)
    info_str = (
        f"[bold #FF8C1A]Agente Scratch[/]  [dim]v{VERSION}[/]\n\n"
        f"[dim]{MODELO} · {AUTOR}[/]\n"
        f"[dim]{Path.cwd()}[/]\n\n"
        f"[dim]Presiona [bold]q[/] o [bold]Enter[/] para continuar[/]"
    )

    class _Bienvenida(App):
        CSS = """
        Screen {
            background: #0d0d0d;
            align: left top;
        }
        #contenedor {
            width: 100%;
            height: auto;
            border: round #FF8C1A;
            padding: 1 3;
            margin: 0;
        }
        #gato {
            width: auto;
            padding: 0 3 0 0;
        }
        #info {
            width: 1fr;
            height: auto;
            content-align: left middle;
            padding: 1 0;
        }
        """
        BINDINGS = [
            ("q", "quit", "Continuar"),
            ("enter", "quit", "Continuar"),
            ("escape", "quit", "Continuar"),
        ]

        def compose(self) -> ComposeResult:
            with Horizontal(id="contenedor"):
                yield Static(gato_str, id="gato", markup=True)
                yield Static(info_str, id="info", markup=True)

    _Bienvenida().run()


# ─── Ayuda Textual ───────────────────────────────────────────────────────────

def mostrar_help() -> None:
    """Muestra la ayuda completa con tablas Textual de comandos y variables."""
    from textual.app import App, ComposeResult
    from textual.widgets import Static, DataTable
    from textual.containers import Vertical

    class _Help(App):
        CSS = """
        Screen {
            background: #0d0d0d;
            align: left top;
        }
        #contenedor {
            width: 100%;
            height: auto;
            border: round #7B4FD4;
            padding: 1 2;
            margin: 0;
        }
        .titulo {
            color: #FF8C1A;
            text-style: bold;
            padding: 0 0 1 0;
        }
        .subtitulo {
            color: #4C97FF;
            text-style: bold;
            padding: 1 0 0 0;
        }
        .flujo {
            color: #3DBD4A;
            text-style: bold;
            padding: 1 0 0 0;
        }
        .nota {
            color: #888AAA;
            padding: 0 0 1 0;
        }
        DataTable {
            height: auto;
            margin: 0 0 1 0;
        }
        """
        BINDINGS = [
            ("q", "quit", "Cerrar"),
            ("enter", "quit", "Cerrar"),
            ("escape", "quit", "Cerrar"),
        ]

        def compose(self) -> ComposeResult:
            with Vertical(id="contenedor"):
                yield Static("COMANDOS", classes="titulo")
                yield self._tabla_comandos()
                yield Static("VARIABLES DE ENTORNO (.env)", classes="subtitulo")
                yield self._tabla_env()
                yield Static("FLUJO RAPIDO", classes="flujo")
                yield Static(
                    "  1. Coloca tus sprites en assets/  (.svg .png .bmp .jpg .gif .sprite2 .sprite3)\n"
                    "  2. Describe el juego cuando se te pida\n"
                    "  3. Asigna un nombre a cada sprite\n"
                    "  4. El .sb3 se genera en la carpeta del proyecto\n"
                    "  5. Importa en Scratch: File > Load from computer\n",
                    classes="nota",
                )
                yield Static("[dim]Presiona [bold]q[/] o [bold]Enter[/] para continuar[/]")

        def _tabla_comandos(self) -> DataTable:
            tabla = DataTable()
            tabla.add_columns("Comando", "Descripcion")
            tabla.add_rows([
                ("agentescratch",     "Lanza el CLI (instalado via pip)"),
                ("agentescratch-mcp", "Inicia servidor MCP para Claude Desktop"),
                ("--help / -h",       "Muestra esta ayuda"),
                ("/exit o Ctrl+C",    "Cierra el CLI limpiamente"),
            ])
            return tabla

        def _tabla_env(self) -> DataTable:
            tabla = DataTable()
            tabla.add_columns("Variable", "Descripcion")
            tabla.add_rows([
                ("GEMINI_API_KEY",   "API key de Google AI Studio (obligatoria)"),
                ("MODELO_AGENTE",    "Modelo a usar (default: gemini-2.5-flash)"),
                ("SCRATCH_USERNAME", "Usuario de Scratch (opcional, para subir)"),
                ("SCRATCH_PASSWORD", "Contrasena de Scratch (opcional, para subir)"),
                ("MAX_REINTENTOS",   "Reintentos del agente LangGraph (default: 3)"),
                ("MCP_PORT",         "Puerto del servidor MCP HTTP (default: 8000)"),
            ])
            return tabla

    _Help().run()


# ─── Input del CLI ───────────────────────────────────────────────────────────

def _leer(prompt: str) -> str:
    """Lee una línea de input capturando Ctrl+C, Ctrl+D y comandos de salida.

    Args:
        prompt: Texto del prompt a mostrar al usuario.

    Returns:
        Texto ingresado por el usuario con strip aplicado.

    Raises:
        SystemExit: Si el usuario escribe /exit, quit, salir o presiona Ctrl+C.
    """
    try:
        valor = input(prompt).strip()
        if valor.lower() in ("/exit", "exit", "quit", "salir"):
            raise SystemExit
        return valor
    except (KeyboardInterrupt, EOFError):
        raise SystemExit


def _salir() -> None:
    print("\n\nHasta luego!\n")
    sys.exit(0)


# ─── Punto de entrada ────────────────────────────────────────────────────────

def main() -> None:
    """Punto de entrada del CLI. Ejecuta el flujo interactivo completo."""
    mostrar_bienvenida()

    try:
        print("\nDescribe el proyecto (--help para ayuda):")
        desc = ""
        while not desc:
            desc = _leer("> ")
            if desc in ("--help", "-h"):
                mostrar_help()
                desc = ""
                print("\nDescribe el proyecto:")
                continue
            if not desc:
                print("No puede estar vacio.")

        if not ASSETS_DIR.exists():
            ASSETS_DIR.mkdir(parents=True)
            print(f"\nCarpeta assets/ creada en: {ASSETS_DIR.resolve()}")

        while True:
            encontrados = sorted(set(
                f for pat in EXTENSIONES_VALIDAS for f in ASSETS_DIR.glob(pat)))
            if not encontrados:
                print(f"\nassets/ vacia. Coloca archivos en: {ASSETS_DIR.resolve()}")
                _leer("Enter cuando esten listos...")
                continue
            print("\nArchivos en assets/:")
            for i, a in enumerate(encontrados, 1):
                print(f"  {i}. {a.name}")
            if _leer("\nSon todos? (s/n): ").lower() in ("s", "si"):
                break
            _leer("Agrega los que falten y presiona Enter...")

        assets_lista = []
        print("\nNombre de cada sprite:")
        for arch in encontrados:
            while True:
                nombre = _leer(f"  {arch.name} -> ")
                if nombre:
                    assets_lista.append({"nombre": nombre, "path": str(ASSETS_DIR / arch.name)})
                    break
                print("  No puede estar vacio.")

        nombre_out = _leer("\nNombre del archivo [mi_juego]: ") or "mi_juego"
        if not nombre_out.endswith(".sb3"):
            nombre_out += ".sb3"

        # ─── Sonidos (opcionales) ─────────────────────────────────────────────
        sonidos_lista = []
        sonidos_encontrados = sorted(set(
            f for pat in SONIDOS_VALIDOS for f in ASSETS_DIR.glob(pat)))
        if sonidos_encontrados:
            print(f"\nSe encontraron {len(sonidos_encontrados)} sonido(s) en assets/:")
            for i, s in enumerate(sonidos_encontrados, 1):
                print(f"  {i}. {s.name}")
            if _leer("Asignar sonidos a los sprites? (s/n): ").lower() in ("s", "si"):
                nombres_sprites = [a["nombre"] for a in assets_lista]
                for snd in sonidos_encontrados:
                    print(f"\nSonido: {snd.name}")
                    print("  Sprites disponibles:")
                    for i, n in enumerate(nombres_sprites, 1):
                        print(f"    {i}. {n}")
                    print("    0. No asignar")
                    while True:
                        opcion = _leer("  Asignar a sprite (numero): ")
                        if opcion == "0":
                            break
                        if opcion.isdigit() and 1 <= int(opcion) <= len(nombres_sprites):
                            sprite_destino = nombres_sprites[int(opcion) - 1]
                            nombre_snd = _leer(f"  Nombre del sonido [{snd.stem}]: ") or snd.stem
                            sonidos_lista.append({
                                "sprite": sprite_destino,
                                "nombre": nombre_snd,
                                "path": str(snd),
                            })
                            print(f"  -> Asignado a '{sprite_destino}'")
                            break
                        print("  Opcion invalida.")

        print(f"\nResumen: {len(assets_lista)} sprite(s), {len(sonidos_lista)} sonido(s) -> {nombre_out}")
        if _leer("Proceder? (s/n): ").lower() not in ("s", "si"):
            print("Cancelado.")
            _salir()

        print("\nGenerando logica del proyecto...")
        nombres = [a["nombre"] for a in assets_lista]
        spec = generar_logica_juego(desc, nombres_sprites=nombres)

        for adv in spec.get("advertencias", []):
            print(f"Aviso: {adv}")

        print(f"Empaquetando {len(spec.get('sprites', []))} sprites...")
        res = empaquetar_sb3(spec, assets_lista, nombre_out, sonidos=sonidos_lista)

        if res["success"]:
            print(f"\nArchivo  : {res['archivo']}")
            print(f"Tipo     : {res['tipo_juego']}")
            print(f"Sprites  : {res['sprites']}")
            print(f"Tamanio  : {res['tamanio_bytes']} bytes")
            print(f"\nScratch: File -> Load from computer -> {nombre_out}")

            print("\nSubir el proyecto a tu cuenta de Scratch?")
            print("El proyecto se creara como PRIVADO.")
            if _leer("Subir? (s/n): ").lower() in ("s", "si"):
                print("\nSubiendo a Scratch...")
                resultado_subida = subir_a_scratch(res["archivo"],
                                                   nombre_out.replace(".sb3", ""))
                if resultado_subida["success"]:
                    print("\nSubido exitosamente.")
                    print(f"URL : {resultado_subida['url']}")
                    print("Puedes compartirlo manualmente desde scratch.mit.edu")
                else:
                    print(f"\nError al subir: {resultado_subida['error']}")
            else:
                print("Subida cancelada. El archivo .sb3 queda guardado localmente.")

    except SystemExit:
        _salir()
