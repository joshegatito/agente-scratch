# -*- coding: utf-8 -*-
"""
agent/graph.py — Grafo del agente Scratch con LangGraph.
Define el flujo autonomo: generar → validar → corregir → empaquetar.
El agente reintenta hasta MAX_REINTENTOS veces si la spec tiene errores.
"""

import os
import json
from typing import Annotated, TypedDict, List

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agente_scratch.agent.tools import listar_assets, generar_spec, validar_spec, empaquetar

load_dotenv()

MAX_REINTENTOS = int(os.getenv("MAX_REINTENTOS", "3"))
MODELO = os.getenv("MODELO_AGENTE", "gemini-2.5-flash")


# ─── Estado del grafo ─────────────────────────────────────────────────────────
class EstadoAgente(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    reintentos: int
    spec_actual: str
    spec_valida: bool
    errores_validacion: List[str]


# ─── Modelo con herramientas enlazadas ───────────────────────────────────────
def _crear_modelo() -> ChatGoogleGenerativeAI:
    """Crea el modelo LangChain con las herramientas del agente enlazadas.

    Returns:
        Modelo Gemini con las 4 herramientas enlazadas via ``bind_tools``.

    Raises:
        ValueError: Si GEMINI_API_KEY no está definida en el entorno.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no encontrada en .env")
    llm = ChatGoogleGenerativeAI(model=MODELO, google_api_key=api_key, temperature=0.1)
    herramientas = [listar_assets, generar_spec, validar_spec, empaquetar]
    return llm.bind_tools(herramientas)


# ─── Nodos del grafo ──────────────────────────────────────────────────────────

def _nodo_agente(estado: EstadoAgente) -> dict:
    # Nodo principal: el modelo decide que herramienta invocar segun el estado
    modelo = _crear_modelo()
    mensajes = estado["messages"]

    if estado.get("errores_validacion") and estado.get("reintentos", 0) > 0:
        contexto = (
            f"La spec generada tiene {len(estado['errores_validacion'])} error(es):\n"
            + "\n".join(f"  - {e}" for e in estado["errores_validacion"])
            + f"\n\nReintento {estado['reintentos']} de {MAX_REINTENTOS}. "
            "Llama generar_spec de nuevo con una descripcion mas precisa "
            "usando SOLO opcodes validos y variables correctamente declaradas."
        )
        mensajes = mensajes + [HumanMessage(content=contexto)]

    respuesta = modelo.invoke(mensajes)
    return {"messages": [respuesta]}


def _nodo_procesar_validacion(estado: EstadoAgente) -> dict:
    # Procesa el resultado de validar_spec y actualiza el estado del grafo
    for msg in reversed(estado["messages"]):
        if isinstance(msg, ToolMessage) and "valido" in msg.content:
            try:
                resultado = json.loads(msg.content)
                es_valida = resultado.get("valido", False)
                errores = resultado.get("errores", [])
                return {
                    "spec_valida": es_valida,
                    "errores_validacion": errores,
                    "reintentos": estado.get("reintentos", 0) + (0 if es_valida else 1),
                }
            except json.JSONDecodeError:
                pass

    return {"spec_valida": False, "errores_validacion": ["No se pudo leer resultado de validacion"]}


# ─── Condiciones de enrutamiento ──────────────────────────────────────────────

def _enrutar_desde_agente(estado: EstadoAgente) -> str:
    ultimo = estado["messages"][-1]
    if hasattr(ultimo, "tool_calls") and ultimo.tool_calls:
        nombres_tools = [tc["name"] for tc in ultimo.tool_calls]
        if "validar_spec" in nombres_tools:
            return "tools_con_validacion"
        return "tools"
    return END


def _enrutar_post_validacion(estado: EstadoAgente) -> str:
    if estado.get("spec_valida"):
        return "agente"
    if estado.get("reintentos", 0) >= MAX_REINTENTOS:
        return END
    return "agente"


# ─── Construccion del grafo ───────────────────────────────────────────────────

def construir_grafo() -> StateGraph:
    """Construye y compila el grafo LangGraph del agente.

    Define los nodos (agente, tools, procesar_validacion), las aristas
    condicionales y el punto de entrada. El grafo implementa el ciclo
    generar → validar → corregir con hasta MAX_REINTENTOS reintentos.

    Returns:
        Grafo compilado listo para invocar con ``grafo.invoke(estado)``.
    """
    herramientas = [listar_assets, generar_spec, validar_spec, empaquetar]
    nodo_tools = ToolNode(herramientas)

    grafo = StateGraph(EstadoAgente)
    grafo.add_node("agente", _nodo_agente)
    grafo.add_node("tools", nodo_tools)
    grafo.add_node("tools_con_validacion", nodo_tools)
    grafo.add_node("procesar_validacion", _nodo_procesar_validacion)

    grafo.set_entry_point("agente")

    grafo.add_conditional_edges("agente", _enrutar_desde_agente, {
        "tools": "tools",
        "tools_con_validacion": "tools_con_validacion",
        END: END,
    })

    grafo.add_edge("tools", "agente")
    grafo.add_edge("tools_con_validacion", "procesar_validacion")

    grafo.add_conditional_edges("procesar_validacion", _enrutar_post_validacion, {
        "agente": "agente",
        END: END,
    })

    return grafo.compile()


# ─── Funcion principal de ejecucion ──────────────────────────────────────────

def ejecutar_agente(
    descripcion: str,
    nombres_sprites: List[str],
    nombre_salida: str,
) -> dict:
    """Ejecuta el agente completo de forma autónoma.

    Punto de entrada principal del agente LangGraph. Construye el grafo,
    formula el prompt inicial y lo ejecuta. El agente genera la spec,
    la valida y la empaqueta, reintentando si hay errores.

    Args:
        descripcion: Descripción del juego en lenguaje natural.
        nombres_sprites: Lista de nombres exactos de sprites a incluir.
        nombre_salida: Nombre del archivo .sb3 de salida (sin extensión).

    Returns:
        Diccionario con ``success`` (bool), ``archivo``, ``sprites``,
        ``tipo_juego`` y ``reintentos_usados`` si exitoso,
        o ``error`` y ``errores_validacion`` si falló.
    """
    grafo = construir_grafo()
    sprites_str = ", ".join(nombres_sprites)

    prompt_inicial = (
        f"Genera un proyecto Scratch completo siguiendo estos pasos en orden:\n"
        f"1. Llama listar_assets para ver que archivos hay disponibles.\n"
        f"2. Llama generar_spec con la descripcion y los sprites indicados.\n"
        f"3. Llama validar_spec con la spec generada.\n"
        f"4. Si la spec es valida, llama empaquetar con la spec, los sprites y el nombre '{nombre_salida}'.\n"
        f"5. Si hay errores en la validacion, corrige y repite desde el paso 2.\n\n"
        f"Descripcion del juego: {descripcion}\n"
        f"Sprites a usar: {sprites_str}\n"
        f"Nombre del archivo de salida: {nombre_salida}"
    )

    estado_inicial: EstadoAgente = {
        "messages": [HumanMessage(content=prompt_inicial)],
        "reintentos": 0,
        "spec_actual": "",
        "spec_valida": False,
        "errores_validacion": [],
    }

    resultado_final = grafo.invoke(estado_inicial)

    for msg in reversed(resultado_final["messages"]):
        if isinstance(msg, ToolMessage) and "archivo" in msg.content:
            try:
                datos = json.loads(msg.content)
                if datos.get("success"):
                    return {
                        "success": True,
                        "archivo": datos["archivo"],
                        "sprites": datos.get("sprites"),
                        "tipo_juego": datos.get("tipo_juego"),
                        "reintentos_usados": resultado_final.get("reintentos", 0),
                    }
            except json.JSONDecodeError:
                pass

    errores = resultado_final.get("errores_validacion", [])
    return {
        "success": False,
        "error": "No se pudo generar un proyecto valido.",
        "errores_validacion": errores,
        "reintentos_usados": resultado_final.get("reintentos", 0),
    }

