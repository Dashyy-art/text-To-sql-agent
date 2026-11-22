"""Commande climate-sql-eval : fait tourner l'agent sur le jeu d'éval, note et rapporte.

Exemples :
    climate-sql-eval --split dev                          # réglage du prompt
    climate-sql-eval --split test --runs 3 --label reference
    climate-sql-eval --split test --no-docs --label sans-doc-dbt
    climate-sql-eval --split test --without-tool check_result --label sans-check
    climate-sql-eval --think --label reflexion --resume eval/results/<fichier>.jsonl
                                                          # reprend un passage interrompu
"""

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from climate_sql_agent.agent.loop import run_agent
from climate_sql_agent.agent.providers import make_provider
from climate_sql_agent.eval.compare import (
    behavior_match,
    is_superlative,
    results_match,
    results_match_tolerant,
)
from climate_sql_agent.eval.dataset import Behavior, EvalQuestion, load_questions
from climate_sql_agent.eval.report import build_report

QUESTIONS_PATH = Path("eval/questions.yaml")
EXPECTED_PATH = Path("eval/expected_results.json")
RESULTS_DIR = Path("eval/results")


def grade(question: EvalQuestion, run, expected: dict) -> tuple[bool, bool]:
    """La réponse est-elle juste ? Renvoie (notation stricte, notation v2 tolérante)."""
    if question.expected_behavior == Behavior.ANSWER:
        rows = run.final_result["rows"] if run.final_result else None
        wanted = expected[question.id]["rows"]
        strict = results_match(wanted, rows, question.order_matters)
        superlative = is_superlative(question.reference_sql)
        return strict, results_match_tolerant(wanted, rows, question.order_matters, superlative)
    ok = behavior_match(question.expected_behavior, run.answer, run.final_result)
    return ok, ok


async def run_once(
    questions, expected, provider, excluded_tools, output: Path, append: bool = False
) -> list[dict]:
    """Un passage : une ligne JSON par question, écrite au fur et à mesure.

    append=True ajoute à la fin d'un fichier existant (reprise d'un passage interrompu).
    """
    lines = []
    with output.open("a" if append else "w", encoding="utf-8") as file:
        for question in questions:
            base = {
                "id": question.id,
                "category": question.category.value,
                "split": question.split.value,
                "expected_behavior": question.expected_behavior.value,
            }
            try:
                run = await run_agent(question.question, provider, excluded_tools)
                strict, tolerant = grade(question, run, expected)
                line = {**base, "correct": strict, "correct_tolerant": tolerant, **run.to_dict()}
                for step in line["steps"]:
                    step["output"] = step["output"][:300]  # fichier de résultats plus léger
            except Exception as error:
                # Une panne ne doit pas arrêter le passage : elle est comptée comme un échec.
                line = {
                    **base,
                    "correct": False,
                    "correct_tolerant": False,
                    "crash": repr(error),
                    "model": provider.name,
                    "prompt_version": "?",
                }

            verdict = "JUSTE" if line["correct"] else ("PANNE" if "crash" in line else "faux")
            detail = f"{line.get('duration_s', 0):5.1f} s  {line.get('input_tokens', 0):6} tok"
            print(
                f"{question.id} [{question.category.value:<11}] {verdict:<5} {detail}", flush=True
            )
            file.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
            lines.append(line)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Évalue l'agent sur le jeu de questions.")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--runs", type=int, default=1, help="Nombre de passages (variabilité).")
    parser.add_argument("--model", default=os.environ.get("AGENT_MODEL", "ollama:qwen3:8b"))
    parser.add_argument("--think", action="store_true", help="Active le mode réflexion.")
    parser.add_argument("--label", default="reference", help="Nom de la configuration.")
    parser.add_argument("--no-docs", action="store_true", help="Retire la doc dbt des outils.")
    parser.add_argument("--without-tool", action="append", default=[], help="Outil à retirer.")
    parser.add_argument("--limit", type=int, help="Seulement les N premières questions.")
    parser.add_argument(
        "--resume", type=Path, help="Reprend un passage interrompu (fichier .jsonl existant)."
    )
    args = parser.parse_args()
    if args.resume and args.runs != 1:
        parser.error("--resume ne s'utilise qu'avec un seul passage (--runs 1)")

    if args.no_docs:
        os.environ["MARTS_DOCS"] = "off"  # transmis au serveur MCP lancé par l'agent

    questions = load_questions(QUESTIONS_PATH)
    if args.split != "all":
        questions = [q for q in questions if q.split.value == args.split]
    questions = questions[: args.limit] if args.limit else questions
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))["results"]
    provider = make_provider(args.model, think=args.think)
    excluded = frozenset(args.without_tool)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = f"{datetime.now():%Y%m%d-%H%M}"
    name = f"{stamp}_{args.label}_{args.split}"
    # Préchauffage : charge le modèle avant de chronométrer (sinon la 1re question paie
    # le chargement, et la latence p95 est faussée).
    provider.chat([{"role": "user", "content": "Bonjour"}], [])

    if args.resume:
        # Reprise : on garde les questions déjà notées et on ne fait que les autres.
        done = [json.loads(line) for line in args.resume.read_text(encoding="utf-8").splitlines()]
        done_ids = {line["id"] for line in done}
        remaining = [q for q in questions if q.id not in done_ids]
        print(
            f"\n=== Reprise de {args.resume} : {len(done)} déjà notées, {len(remaining)} restantes"
        )
        new = asyncio.run(
            run_once(remaining, expected, provider, excluded, args.resume, append=True)
        )
        runs = [done + new]
        name = args.resume.stem.removesuffix("_run1")
    else:
        runs = []
        for index in range(1, args.runs + 1):
            print(f"\n=== {args.label} : passage {index}/{args.runs} ({len(questions)} questions)")
            output = RESULTS_DIR / f"{name}_run{index}.jsonl"
            runs.append(asyncio.run(run_once(questions, expected, provider, excluded, output)))

    report_path = RESULTS_DIR / f"{name}_rapport.md"
    report_path.write_text(build_report(args.label, runs), encoding="utf-8")
    print(f"\nRapport : {report_path}")


if __name__ == "__main__":
    main()
