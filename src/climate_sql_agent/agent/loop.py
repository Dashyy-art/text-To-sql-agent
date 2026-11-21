"""Boucle agent : le modèle choisit ses outils, notre code les exécute via MCP."""

import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field

from mcp.client.client import Client
from mcp.client.stdio import StdioServerParameters

from climate_sql_agent.agent.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from climate_sql_agent.agent.providers import OllamaProvider

MAX_STEPS = 8  # nombre maximal d'appels au modèle pour une question


@dataclass
class ToolStep:
    tool: str
    arguments: dict
    is_error: bool
    output: str  # réponse de l'outil (tronquée dans la trace)
    duration_s: float


@dataclass
class AgentRun:
    question: str
    model: str
    prompt_version: str
    answer: str = ""
    final_sql: str | None = None  # dernier SQL exécuté avec succès
    final_result: dict | None = None  # son résultat : columns + rows
    steps: list[ToolStep] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    stopped_by_limit: bool = False
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def server_parameters() -> StdioServerParameters:
    """Lance notre serveur MCP comme sous-processus, avec le même Python et le même .env."""
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "climate_sql_agent.mcp_server.server"],
        env=dict(os.environ),
    )


def to_function_tools(mcp_tools) -> list[dict]:
    """Traduit les outils MCP au format "function calling" (format attendu par Ollama)."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        }
        for tool in mcp_tools
    ]


def build_system_prompt(excluded_tools: frozenset[str]) -> str:
    """Prompt système, sans les lignes qui citent un outil retiré (expériences)."""
    lines = SYSTEM_PROMPT.splitlines()
    return "\n".join(line for line in lines if not any(t in line for t in excluded_tools))


async def run_agent(
    question: str, provider: OllamaProvider, excluded_tools: frozenset[str] = frozenset()
) -> AgentRun:
    """Pose une question à l'agent et renvoie la réponse et la trace complète.

    excluded_tools : outils retirés à l'agent, pour mesurer leur apport (étape 7).
    """
    run = AgentRun(question=question, model=provider.name, prompt_version=PROMPT_VERSION)
    start = time.perf_counter()

    async with Client(server_parameters()) as mcp_client:
        mcp_tools = (await mcp_client.list_tools()).tools
        tools = to_function_tools([t for t in mcp_tools if t.name not in excluded_tools])
        messages = [
            {"role": "system", "content": build_system_prompt(excluded_tools)},
            {"role": "user", "content": question},
        ]

        for _ in range(MAX_STEPS):
            reply = provider.chat(messages, tools)
            run.llm_calls += 1
            run.input_tokens += reply.input_tokens
            run.output_tokens += reply.output_tokens
            messages.append(provider.assistant_message(reply))

            # Pas de demande d'outil : le modèle a donné sa réponse finale.
            if not reply.tool_calls:
                run.answer = reply.content
                break

            # Sinon, on exécute chaque outil demandé et on renvoie le résultat au modèle.
            for call in reply.tool_calls:
                tool_start = time.perf_counter()
                result = await mcp_client.call_tool(call.name, call.arguments)
                output = result.content[0].text if result.content else ""

                run.steps.append(
                    ToolStep(
                        tool=call.name,
                        arguments=call.arguments,
                        is_error=bool(result.is_error),
                        output=output[:2000],
                        duration_s=round(time.perf_counter() - tool_start, 2),
                    )
                )
                if call.name == "run_sql" and not result.is_error:
                    data = json.loads(output)
                    run.final_sql = data["sql_executed"]
                    run.final_result = {"columns": data["columns"], "rows": data["rows"]}

                messages.append(provider.tool_message(call, output))
        else:
            # La boucle for s'est terminée sans "break" : limite d'étapes atteinte.
            run.stopped_by_limit = True
            run.answer = f"Échec : pas de réponse après {MAX_STEPS} étapes."

    run.duration_s = round(time.perf_counter() - start, 2)
    return run
