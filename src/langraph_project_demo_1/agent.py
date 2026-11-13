import asyncio
import math
import os
import random

try:
    from . import env
    from .mock_model import MockToolCallingChatModel
except ImportError:  # ejecucion directa: python src/.../agent.py
    import env
    from mock_model import MockToolCallingChatModel

from langchain.chat_models import init_chat_model
from langchain.tools import tool

env.load_dotenv()

DELAY = float(os.getenv("TOOL_DELAY", "0.6"))

MODEL = os.getenv("LLM_MODEL", "").strip()
PROVIDER = os.getenv("LLM_PROVIDER", "").strip() or None
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
BASE_URL = os.getenv("LLM_BASE_URL", "").strip() or None
USE_MOCK = os.getenv("USE_MOCK_LLM", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
if not MODEL and anthropic_key and not anthropic_key.startswith("your-"):
    MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    PROVIDER = PROVIDER or "anthropic"

if (
    USE_MOCK
    or not MODEL
    or MODEL.lower() == "mock"
    or (PROVIDER and PROVIDER.lower() == "mock")
):
    print("[agent] Usando MockToolCallingChatModel")
    print(
        "[agent] Define LLM_MODEL (y LLM_PROVIDER si hace falta) para usar un LLM real."
    )
    model = MockToolCallingChatModel()
else:
    model_kwargs: dict[str, object] = {"temperature": TEMPERATURE}
    if BASE_URL:
        model_kwargs["base_url"] = BASE_URL
    print(f"[agent] Usando LLM: {PROVIDER or 'auto'} / {MODEL}")
    try:
        model = init_chat_model(MODEL, model_provider=PROVIDER, **model_kwargs)
    except Exception as exc:
        raise SystemExit(
            f"[agent] No se pudo inicializar el LLM '{MODEL}' "
            f"(provider={PROVIDER or 'auto'}): {exc}"
        ) from exc


async def _tool_delay() -> None:
    await asyncio.sleep(DELAY + random.uniform(0, 0.5))


# Define tools
@tool
async def add(a: float, b: float) -> float:
    """Suma `a` y `b`."""
    await _tool_delay()
    return a + b


@tool
async def subtract(a: float, b: float) -> float:
    """Resta `b` a `a`."""
    await _tool_delay()
    return a - b


@tool
async def multiply(a: float, b: float) -> float:
    """Multiplica `a` por `b`."""
    await _tool_delay()
    return a * b


@tool
async def divide(a: float, b: float) -> float:
    """Divide `a` entre `b`."""
    await _tool_delay()
    if b == 0:
        raise ValueError("No se puede dividir entre cero.")
    return a / b


@tool
async def square_root(a: float) -> float:
    """Calcula la raiz cuadrada de `a`."""
    await _tool_delay()
    if a < 0:
        raise ValueError("No existe raiz cuadrada real de un numero negativo.")
    return math.sqrt(a)


@tool
async def logarithm(a: float, base: float = 10) -> float:
    """Calcula el logaritmo de `a` en la `base` indicada."""
    await _tool_delay()
    if a <= 0:
        raise ValueError("El logaritmo solo esta definido para numeros positivos.")
    if base <= 0 or base == 1:
        raise ValueError("La base del logaritmo debe ser positiva y distinta de 1.")
    return math.log(a, base)


# Augment the LLM with tools
tools = [add, subtract, multiply, divide, square_root, logarithm]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)


if __name__ == "__main__":

    async def _demo() -> None:
        from langchain.messages import HumanMessage

        response = await model_with_tools.ainvoke(
            [HumanMessage(content="Multiplica 6 y 7.")]
        )
        print("Tool calls:", response.tool_calls)
        for call in response.tool_calls:
            result = await tools_by_name[call["name"]].ainvoke(call["args"])
            print(f"{call['name']}({call['args']}) = {result}")

    asyncio.run(_demo())
