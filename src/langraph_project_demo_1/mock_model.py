import asyncio
import os
import random
import re
import unicodedata
import uuid
from typing import Any, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable

LLM_DELAY = float(os.getenv("MOCK_LLM_DELAY", "1.5"))


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _detect_operation(text: str) -> str:
    text = _normalize(text)
    if any(word in text for word in ("raiz", "sqrt", "square root")):
        return "square_root"
    if any(word in text for word in ("logaritmo", "log")):
        return "logarithm"
    if any(word in text for word in ("multiplic", "times", "product", "*")):
        return "multiply"
    if any(word in text for word in ("divisi", "dividir", "quotient", "/")):
        return "divide"
    if any(word in text for word in ("resta", "restar", "subtract", "minus")):
        return "subtract"
    return "add"


def _parse_numbers(text: str) -> list[float]:
    values = []
    for raw in re.findall(r"-?\d+(?:[.,]\d+)?", text):
        number = float(raw.replace(",", "."))
        values.append(int(number) if number.is_integer() else number)
    return values


class MockToolCallingChatModel(BaseChatModel):
    """Modelo determinista que simula un LLM con tool calling (sin API)."""

    @property
    def _llm_type(self) -> str:
        return "mock-tool-calling"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable:
        return self

    def _generate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        last = messages[-1]

        if isinstance(last, ToolMessage):
            message = AIMessage(content=f"El resultado es {last.content}.")
            return ChatResult(generations=[ChatGeneration(message=message)])

        human = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
        )
        text = "" if human is None else str(human.content)

        operation = _detect_operation(text)
        numbers = _parse_numbers(text)

        if operation == "square_root":
            if not numbers:
                return self._ask_for_numbers()
            args = {"a": numbers[0]}
        elif operation == "logarithm":
            if not numbers:
                return self._ask_for_numbers()
            args = {
                "a": numbers[0],
                "base": numbers[1] if len(numbers) > 1 else 10,
            }
        else:
            if len(numbers) < 2:
                return self._ask_for_numbers()
            args = {"a": numbers[0], "b": numbers[1]}

        tool_call = {
            "name": operation,
            "args": args,
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "tool_call",
        }
        message = AIMessage(content="", tool_calls=[tool_call])
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        print("[mock-llm] pensando...")
        await asyncio.sleep(LLM_DELAY + random.uniform(0, 0.8))
        return self._generate(
            messages, stop=stop, run_manager=run_manager, **kwargs
        )

    @staticmethod
    def _ask_for_numbers() -> ChatResult:
        message = AIMessage(content="Necesito los números para resolver la operación.")
        return ChatResult(generations=[ChatGeneration(message=message)])
