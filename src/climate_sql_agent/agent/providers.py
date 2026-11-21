"""Le modèle de l'agent : un modèle local servi par Ollama (par défaut qwen3:8b).

La boucle agent passe par cette petite classe au lieu d'appeler Ollama directement :
les réglages du modèle (contexte, réflexion, température) sont regroupés ici.
"""

from dataclasses import dataclass, field
from typing import Any

import ollama


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class LLMReply:
    content: str  # texte de la réponse (vide si le modèle demande des outils)
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None  # message d'origine, renvoyé tel quel dans l'historique


class OllamaProvider:
    """Modèle local via l'API native d'Ollama (réglages think et num_ctx)."""

    def __init__(self, model: str, think: bool = False, context_tokens: int = 8192):
        self.name = f"ollama:{model}"
        self.model = model
        self.think = think
        self.context_tokens = context_tokens

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMReply:
        response = ollama.chat(
            model=self.model,
            messages=messages,
            tools=tools,
            think=self.think,
            options={"temperature": 0, "num_ctx": self.context_tokens},
        )
        calls = [
            ToolCall(name=c.function.name, arguments=dict(c.function.arguments))
            for c in response.message.tool_calls or []
        ]
        return LLMReply(
            content=response.message.content or "",
            tool_calls=calls,
            input_tokens=response.prompt_eval_count or 0,
            output_tokens=response.eval_count or 0,
            raw=response.message,
        )

    def assistant_message(self, reply: LLMReply) -> Any:
        """Message du modèle, gardé dans l'historique."""
        return reply.raw

    def tool_message(self, call: ToolCall, output: str) -> dict:
        """Résultat d'un outil, renvoyé au modèle."""
        return {"role": "tool", "tool_name": call.name, "content": output}


def make_provider(spec: str, think: bool = False) -> OllamaProvider:
    """Crée le modèle à partir d'un texte "ollama:<modèle>", par exemple "ollama:qwen3:8b"."""
    provider, _, model = spec.partition(":")
    if provider != "ollama" or not model:
        raise ValueError(f"Format attendu 'ollama:<modèle>' (ex. ollama:qwen3:8b), reçu : {spec!r}")
    return OllamaProvider(model, think=think)
