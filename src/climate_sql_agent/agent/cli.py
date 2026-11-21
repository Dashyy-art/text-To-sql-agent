"""Commande : climate-sql-agent "question" -> réponse, résumé et trace JSON."""

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from climate_sql_agent.agent.loop import run_agent
from climate_sql_agent.agent.providers import make_provider

TRACES_DIR = Path("traces")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pose une question à l'agent climat.")
    parser.add_argument("question", help="La question, en français, entre guillemets.")
    parser.add_argument(
        "--model",
        default=os.environ.get("AGENT_MODEL", "ollama:qwen3:8b"),
        help="Modèle Ollama, au format ollama:<modèle> (par défaut ollama:qwen3:8b).",
    )
    parser.add_argument("--think", action="store_true", help="Active le mode réflexion.")
    args = parser.parse_args()

    provider = make_provider(args.model, think=args.think)
    run = asyncio.run(run_agent(args.question, provider))

    print(run.answer)
    print(
        f"\n--- {len(run.steps)} appel(s) d'outils | {run.input_tokens} tokens en entrée, "
        f"{run.output_tokens} en sortie | {run.duration_s} s"
    )
    for step in run.steps:
        status = "ERREUR" if step.is_error else "ok"
        arguments = json.dumps(step.arguments, ensure_ascii=False)[:120]
        print(f"  {step.tool} [{status}] {arguments}")

    TRACES_DIR.mkdir(exist_ok=True)
    path = TRACES_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    text = json.dumps(run.to_dict(), indent=2, ensure_ascii=False, default=str)
    path.write_text(text, encoding="utf-8")
    print(f"Trace : {path}")


if __name__ == "__main__":
    main()
