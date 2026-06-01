# Agente Scratch

**Autor:** Dev Joshe Gatito  
**Versión:** 2.3.0  
**Fecha:** Mayo 2026

Genera proyectos `.sb3` para [Scratch 3.0](https://scratch.mit.edu) a partir de una descripción en lenguaje natural usando inteligencia artificial (Gemini 2.5 Flash).

![Agente Scratch](https://i.imgur.com/OtEdX4C.png)

---

## ¿Qué es Scratch?

[Scratch](https://scratch.mit.edu) es una plataforma de programación visual **gratuita** creada por el MIT, diseñada especialmente para niños, estudiantes y docentes. Permite crear juegos, animaciones e historias interactivas arrastrando bloques de código — sin escribir una sola línea de texto.

Es ampliamente utilizada en escuelas de todo el mundo como introducción a la programación y al pensamiento computacional. Los proyectos en Scratch se guardan en archivos `.sb3` que se pueden importar directamente desde la plataforma.

**Agente Scratch** nació para ayudar a docentes y estudiantes a generar proyectos Scratch desde una descripción en español, sin necesidad de construir los bloques manualmente — la IA lo hace por ti.

---

## Características

| Función | Descripción |
|---|---|
| **Generación con IA** | Convierte descripciones en lenguaje natural a bloques Scratch válidos |
| **Reparación automática** | Detecta y corrige errores de bloques automáticamente (hasta 3 reintentos) |
| **Sprites personalizados** | Usa tus propias imágenes en `.svg`, `.png`, `.jpg`, `.bmp`, `.gif`, `.sprite2`, `.sprite3` |
| **Sonidos** | Asigna sonidos `.mp3` y `.wav` a cada sprite del proyecto |
| **CLI instalable** | Se instala como comando en la terminal con `pip install agente-scratch` |
| **Subida a Scratch** | Sube el proyecto directo a tu cuenta de Scratch (siempre como privado) |
| **Servidor MCP** | Se integra con Claude Desktop como herramienta de IA via FastMCP |

---

## Requisitos

- Python 3.11 o superior
- Una API key gratuita de Google Gemini — consíguela en [Google AI Studio](https://aistudio.google.com/apikey)
- Cuenta en [Scratch](https://scratch.mit.edu) — solo si quieres subir proyectos directamente

---

## Instalación

### Desde PyPI (recomendado)

```bash
pip install agente-scratch
```

### Desde el código fuente

```bash
git clone https://github.com/joshegatito/agente-scratch
cd agente-scratch
python -m venv venv
venv\Scripts\activate        # Windows
pip install -e .
```

Después de instalar tendrás dos comandos disponibles en tu terminal:

| Comando | Descripción |
|---|---|
| `agentescratch` | Lanza el CLI interactivo para generar proyectos |
| `agentescratch-mcp` | Inicia el servidor MCP para Claude Desktop |

---

## Configuración

Crea un archivo `.env` en la carpeta donde vayas a usar el agente. Puedes copiar el ejemplo incluido:

```powershell
copy .env.example .env
```

Luego edítalo con tus datos:

```env
# Obligatoria — sin esta clave el agente no puede generar proyectos
GEMINI_API_KEY=tu_clave_aqui

# Opcionales — solo necesarias si quieres subir proyectos a Scratch
SCRATCH_USERNAME=tu_usuario_de_scratch
SCRATCH_PASSWORD=tu_contrasena_de_scratch

# Opcionales — valores por defecto ya configurados
MODELO_AGENTE=gemini-2.5-flash   # modelo de IA a usar
MAX_REINTENTOS=3                  # intentos de corrección automática
MCP_PORT=8000                     # puerto del servidor MCP en modo HTTP
```

> Para obtener tu API key gratuita: ve a [aistudio.google.com/apikey](https://aistudio.google.com/apikey), inicia sesión con tu cuenta de Google y crea una clave nueva.

---

## Uso

### Paso 1 — Prepara tus archivos

Crea una carpeta llamada `assets/` en tu proyecto y coloca ahí tus sprites y sonidos.

> Un **sprite** es un personaje o elemento visual del juego (el gato, un enemigo, una moneda). Puede ser una imagen en cualquiera de estos formatos: `.svg` `.png` `.jpg` `.bmp` `.gif` `.sprite2` `.sprite3`

> Un **sonido** es un efecto de audio que el sprite puede reproducir durante el juego: `.mp3` `.wav`

La carpeta `assets/` se crea automáticamente si no existe al lanzar el CLI.

### Paso 2 — Lanza el CLI

```bash
agentescratch
```

El agente te guiará paso a paso:

1. Describe el juego o actividad en lenguaje natural
2. Confirma los archivos encontrados en `assets/`
3. Asigna un nombre a cada sprite
4. Asigna sonidos a los sprites (opcional)
5. Elige un nombre para el archivo `.sb3`
6. El agente genera y empaqueta el proyecto automáticamente

### Paso 3 — Abre en Scratch

Una vez generado el `.sb3`, ábrelo en [scratch.mit.edu](https://scratch.mit.edu):

```
Archivo → Cargar desde tu computadora → selecciona el archivo .sb3
```

---

## Ejemplo de descripción

```
Un quiz de matemáticas. El sprite Profesor aparece en el centro y hace
preguntas de suma y resta con números del 1 al 10. Si el jugador responde
correcto dice "¡Correcto! +1 punto" y suma un punto al marcador.
Si falla dice la respuesta correcta. El juego repite para siempre.
```

El agente genera automáticamente todos los bloques necesarios: variables, operadores, preguntas, validación de respuesta y marcador de puntaje.

---

## Integración con Claude Desktop (MCP)

Agente Scratch puede usarse directamente desde Claude Desktop sin necesidad del CLI. El servidor MCP expone las herramientas del agente para que Claude las invoque automáticamente.

```bash
# Inicia el servidor en modo stdio (para Claude Desktop)
agentescratch-mcp

# Inicia en modo HTTP (para acceso desde red)
agentescratch-mcp --http
```

Agrega esta configuración a `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agente-scratch": {
      "command": "agentescratch-mcp"
    }
  }
}
```

Herramientas disponibles desde Claude Desktop:

| Herramienta | Descripción |
|---|---|
| `listar_sprites_disponibles` | Lista sprites y sonidos disponibles en `assets/` |
| `generar_proyecto` | Genera el `.sb3` completo desde una descripción |
| `validar_proyecto` | Valida una spec JSON de bloques |
| `info_agente` | Muestra versión y capacidades del agente |

---

## Cómo funciona internamente

```
Descripción del usuario
        │
        ▼
  Gemini 2.5 Flash
  (genera spec JSON con bloques Scratch por sprite)
        │
        ▼
  reparar_spec()
  (elimina opcodes inválidos, declara variables faltantes)
        │
        ▼
  empaquetar_sb3()
  (construye project.json + assets + sonidos → ZIP .sb3)
        │
        ▼
  Archivo .sb3 listo para abrir en Scratch
```

El agente usa **LangGraph** para orquestar el ciclo de generación, validación y corrección automática. Si la spec generada tiene errores, la corrige y vuelve a intentar hasta 3 veces antes de reportar el problema.

---

## Para desarrolladores

### Estructura del proyecto

```
agente_scratch/
├── __init__.py        # Versión y autor
├── core.py            # Motor principal: Gemini, generación, reparación, empaquetado, subida
├── cli/
│   └── app.py         # CLI interactivo con bienvenida Textual, --help y flujo paso a paso
└── agent/
    ├── tools.py       # Herramientas LangChain (@tool) que envuelven el motor
    ├── graph.py       # Grafo LangGraph: generar → validar → corregir → empaquetar
    └── mcp_server.py  # Servidor FastMCP para Claude Desktop

tests/
├── conftest.py        # Fixtures compartidas (specs, mocks de Gemini, assets temporales)
├── test_core.py       # Tests del motor (normalizar, reparar, empaquetar, Gemini)
├── agent/
│   └── test_tools.py  # Tests de herramientas LangChain
└── cli/
    └── test_app.py    # Tests del CLI (bienvenida, help, _leer)

pyproject.toml         # Configuración del paquete, dependencias y herramientas
requirements.txt       # Dependencias con versiones para desarrollo
.env.example           # Plantilla de variables de entorno
scratch.png            # Imagen del gato Scratch usada en la pantalla de bienvenida
```

### Entorno de desarrollo

```bash
git clone https://github.com/joshegatito/agente-scratch
cd agente-scratch
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

### Ejecutar tests

```bash
# Tests unitarios (sin llamadas reales a la API)
pytest tests/ -m "not integration" --tb=short

# Todos los tests con reporte de cobertura
pytest tests/ --cov=agente_scratch --cov-report=term-missing
```

### Lint, formato y tipos

```bash
# Verificar errores de estilo
ruff check agente_scratch/ tests/

# Aplicar formato automático
ruff format agente_scratch/ tests/

# Verificación de tipos estáticos
mypy agente_scratch/
```

### Contribuir

Las contribuciones son bienvenidas. Por favor abre un **issue** primero para discutir el cambio propuesto antes de enviar un pull request.

---

## Limitaciones

- La API interna de Scratch puede cambiar sin previo aviso y afectar la subida de proyectos
- Proyectos muy complejos pueden requerir ajustes manuales de bloques en Scratch
- Los proyectos se suben siempre como **privados** — debes compartirlos manualmente desde scratch.mit.edu
- Los sonidos referenciados en la descripción deben existir en `assets/` con el nombre exacto asignado

---

## Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 2.0.0 | Mayo 2026 | Agente LangGraph, servidor FastMCP, validador de opcodes, reparación automática |
| 2.3.0 | Mayo 2026 | CLI pip instalable, bienvenida Textual dinámica, soporte de sonidos (.mp3/.wav), formatos de imagen extendidos (.bmp .gif .sprite2), tests pytest, ruff + mypy |

---

*Dev Joshe Gatito — Agente Scratch v2.3.0*
