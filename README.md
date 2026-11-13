# LangGraph Terminal Agent Demo

Agente de terminal construido con **LangGraph** que resuelve operaciones aritmeticas usando **tool calling**. Incluye un **LLM mockeado** que funciona sin API key y permite conectar cualquier proveedor de LLM configurable por variables de entorno.

## Caracteristicas

- Grafo de LangGraph con nodos asincronos y delays simulados.
- Tools para suma, resta, multiplicacion, division, raiz cuadrada y logaritmo.
- Mock LLM determinista que decide la tool segun la operacion elegida.
- Soporte para Anthropic, OpenAI, Google, Ollama y endpoints compatibles con OpenAI.
- Interfaz de consola con menu de operaciones.
- Trazas locales en consola con `ConsoleCallbackHandler`.
- Integracion opcional con LangSmith.
- Sin API key obligatoria: el modo mock funciona al instante.

## Stack

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) para entorno y dependencias
- LangChain
- LangGraph
- LangChain Anthropic (incluido por defecto)
- LangSmith (opcional)

## Requisitos

- Python `>=3.12`
- uv instalado

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Instalacion

```bash
git clone <URL_DEL_REPOSITORIO>
cd langraph_demo
uv sync
```

Esto crea el entorno virtual en `.venv` e instala las dependencias declaradas en `pyproject.toml` y `uv.lock`.

## Configuracion del entorno

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

El archivo `.env` **no se versiona** en git. El ejemplo si se versiona como `.env.example`.

Si no configuras ningun modelo, la app usa el mock automaticamente:

```bash
uv run langgraph-demo
```

## Uso

### Ejecutar el agente principal

```bash
uv run langgraph-demo
```

o directamente como modulo:

```bash
uv run python -m langraph_project_demo_1.main
```

Tambien puedes ejecutar el script sin instalar el entry point:

```bash
uv run python src/langraph_project_demo_1/main.py
```

### Ejecutar la demo de tools

```bash
uv run python -m langraph_project_demo_1.agent
```

### Menu de operaciones

La app pide por consola:

1. Suma
2. Resta
3. Multiplicacion
4. Division
5. Raiz cuadrada
6. Logaritmo

Despues solicita los numeros necesarios y muestra paso a paso la decision del LLM, la tool ejecutada y el estado final.

## Usar un LLM real

La seleccion del modelo se hace con variables de entorno. Si `LLM_MODEL` no esta definido, se usa el mock.

| Caso | Variables principales |
|---|---|
| Mock (sin API) | ninguna |
| Anthropic | `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-sonnet-4-6`, `ANTHROPIC_API_KEY=...` |
| OpenAI | `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o`, `OPENAI_API_KEY=...` |
| Google | `LLM_PROVIDER=google_genai`, `LLM_MODEL=gemini-2.5-pro`, `GOOGLE_API_KEY=...` |
| Ollama local | `LLM_PROVIDER=ollama`, `LLM_MODEL=llama3.1`, `LLM_BASE_URL=http://localhost:11434` |
| OpenAI-compatible | `LLM_PROVIDER=openai`, `LLM_MODEL=...`, `LLM_BASE_URL=http://localhost:1234/v1` |

### Ejemplo Anthropic

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

### Ejemplo OpenAI

Instala la integracion y configura el `.env`:

```bash
uv add langchain-openai
```

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

### Ejemplo Google

```bash
uv add langchain-google-genai
```

```env
LLM_PROVIDER=google_genai
LLM_MODEL=gemini-2.5-pro
GOOGLE_API_KEY=...
```

### Ejemplo Ollama local

```bash
uv add langchain-ollama
```

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
LLM_BASE_URL=http://localhost:11434
```

### Forzar el mock

Aunque tengas un modelo configurado:

```env
USE_MOCK_LLM=true
```

## Variables de entorno

| Variable | Default | Descripcion |
|---|---|---|
| `LLM_MODEL` | vacio | Modelo a usar. Si esta vacio, se usa el mock |
| `LLM_PROVIDER` | inferido | Proveedor: `anthropic`, `openai`, `google_genai`, `ollama`, etc. |
| `LLM_TEMPERATURE` | `0` | Temperatura del modelo |
| `LLM_BASE_URL` | vacio | URL para Ollama, LM Studio, vLLM u otros endpoints |
| `USE_MOCK_LLM` | `false` | Fuerza el uso del mock |
| `ANTHROPIC_API_KEY` | vacio | API key de Anthropic |
| `OPENAI_API_KEY` | vacio | API key de OpenAI o endpoint compatible |
| `GOOGLE_API_KEY` | vacio | API key de Google |
| `MOCK_LLM_DELAY` | `1.5` | Delay base del LLM mock (segundos) |
| `TOOL_DELAY` | `0.6` | Delay base de cada tool (segundos) |
| `NODE_DELAY` | `0.5` | Delay base de los nodos del grafo (segundos) |
| `LANGSMITH_TRACING` | `false` | Activa el envio de trazas a LangSmith |
| `LANGSMITH_API_KEY` | vacio | API key de LangSmith |
| `LANGSMITH_PROJECT` | `langraph-demo` | Nombre del proyecto en LangSmith |

Los delays incluyen un pequeno valor aleatorio para simular latencia realista. Puedes ajustarlos al ejecutar:

```bash
MOCK_LLM_DELAY=2.5 TOOL_DELAY=1 NODE_DELAY=0.8 uv run langgraph-demo
```

## Arquitectura del grafo

```text
START
  |
  v
llm_call  --(tool_calls)-->  tool_node
  |                             |
  |                             v
  +------------------------ llm_call
  |
  +--(sin tool_calls)--> END
```

- `llm_call`: el LLM decide si llamar una tool.
- `tool_node`: ejecuta la tool elegida y devuelve un `ToolMessage`.
- `should_continue`: enruta a `tool_node` o a `END`.

En modo mock, `MockToolCallingChatModel` analiza el texto en espanol, detecta la operacion y genera el `tool_call` correspondiente.

## Trazas

### Trazas locales

La app usa `SafeConsoleCallbackHandler`, basado en `ConsoleCallbackHandler`, para imprimir en terminal las llamadas al LLM y a las tools sin necesidad de red.

### LangSmith (opcional)

LangSmith Cloud requiere acceso a internet. Agrega al `.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=langraph-demo
```

`main.py` activa el tracing automaticamente si detecta `LANGSMITH_API_KEY`.

## Estructura del proyecto

```text
.
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
└── src/
    └── langraph_project_demo_1/
        ├── __init__.py
        ├── agent.py
        ├── env.py
        ├── main.py
        └── mock_model.py
```

- `main.py`: grafo, nodos async, menu de consola y streaming.
- `agent.py`: tools, seleccion del LLM y configuracion del proveedor.
- `mock_model.py`: LLM mock con deteccion de operaciones.
- `env.py`: carga de `.env` sin dependencias externas.

## Problemas comunes

### `ModuleNotFoundError: No module named 'langgraph'`

Estas usando el Python del sistema en lugar del entorno del proyecto. Usa `uv run` o el Python de `.venv`:

```bash
uv run python src/langraph_project_demo_1/main.py
```

No uses `/bin/python3` ni rutas absolutas al Python global.

### Falta el paquete del proveedor

Cada proveedor tiene su integracion:

```bash
uv add langchain-openai
uv add langchain-google-genai
uv add langchain-ollama
```

### LangSmith no muestra trazas

Verifica que tengas internet, una `LANGSMITH_API_KEY` valida y `LANGSMITH_TRACING=true`.

## Seguridad

- Nunca subas `.env` al repositorio.
- Rota cualquier API key que hayas compartido accidentalmente.
- `.env` esta incluido en `.gitignore`; `.env.example` solo contiene valores de ejemplo.
