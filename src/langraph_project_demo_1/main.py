import asyncio
import operator
import os
from typing import Annotated, Literal

try:
    from . import agent, env
except ImportError:  # ejecucion directa: python src/.../main.py
    import agent
    import env

env.load_dotenv()

if os.getenv("LANGSMITH_API_KEY"):
    os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGSMITH_PROJECT", "langraph-demo")

from langchain.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tracers.stdout import (
    ConsoleCallbackHandler,
    get_bolded_text,
    get_colored_text,
)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

DELAY = float(os.getenv("NODE_DELAY", "0.5"))


class SafeConsoleCallbackHandler(ConsoleCallbackHandler):
    """ConsoleCallbackHandler que soporta tools con inputs estructurados."""

    def _on_tool_start(self, run) -> None:
        crumbs = self.get_breadcrumbs(run)
        payload = run.inputs
        if isinstance(payload, dict):
            payload = payload.get("input", payload)
        self.function_callback(
            f"{get_colored_text('[tool/start]', color='green')} "
            + get_bolded_text(f"[{crumbs}] Entering Tool run with input:\n")
            + f'"{payload}"'
        )


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


async def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""

    await asyncio.sleep(DELAY)
    response = await agent.model_with_tools.ainvoke(
        [
            SystemMessage(
                content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
            )
        ]
        + state["messages"]
    )
    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


async def tool_node(state: dict):
    """Performs the tool call"""

    await asyncio.sleep(DELAY)
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = agent.tools_by_name[tool_call["name"]]
        try:
            observation = await tool.ainvoke(tool_call["args"])
        except Exception as exc:
            observation = f"Error: {exc}"
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}


def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END


# Build workflow
agent_builder = StateGraph(MessagesState)

# Add nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)

# Add edges to connect nodes
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
agent_builder.add_edge("tool_node", "llm_call")

# Compile the agent
ag = agent_builder.compile()


def ask_user() -> str:
    options = {
        "1": "suma",
        "2": "resta",
        "3": "multiplicacion",
        "4": "division",
        "5": "raiz cuadrada",
        "6": "logaritmo",
    }

    print("Operaciones disponibles:")
    for key, label in options.items():
        print(f"  {key}. {label}")

    choice = input("Elige una operacion [1-6]: ").strip()
    while choice not in options:
        choice = input("Opcion no valida. Elige [1-6]: ").strip()

    if choice == "5":
        a = input("Numero: ").strip()
        return f"raiz cuadrada de {a}"

    if choice == "6":
        a = input("Numero: ").strip()
        base = input("Base [10]: ").strip() or "10"
        return f"logaritmo de {a} en base {base}"

    a = input("Primer numero: ").strip()
    b = input("Segundo numero: ").strip()
    return f"{options[choice]} {a} y {b}"


def _print_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage):
        print(f"  AI: {message.content!r}")
        for call in message.tool_calls:
            print(f"     tool_call -> {call['name']}({call['args']})")
    elif isinstance(message, ToolMessage):
        print(f"  Tool result ({message.tool_call_id}): {message.content}")
    else:
        message.pretty_print()


async def main() -> None:
    prompt = ask_user()
    inputs = {"messages": [HumanMessage(content=prompt)]}
    collected = list(inputs["messages"])
    config = {"callbacks": [SafeConsoleCallbackHandler()]}

    print("\n=== Ejecucion paso a paso ===")
    async for step in ag.astream(inputs, config=config, stream_mode="updates"):
        for node, update in step.items():
            print(f"[{node}]")
            for message in update.get("messages", []):
                collected.append(message)
                _print_message(message)

    print("\n=== Estado final ===")
    for message in collected:
        message.pretty_print()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
