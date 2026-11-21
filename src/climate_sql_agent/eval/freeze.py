"""Exécute les SQL de référence sur la base DuckDB et fige les résultats attendus.

Usage (depuis la racine du projet) :
    uv run python -m climate_sql_agent.eval.freeze
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from climate_sql_agent.eval.dataset import Behavior, load_questions
from climate_sql_agent.warehouse.catalog import to_jsonable
from climate_sql_agent.warehouse.executor import make_connection, run_query

QUESTIONS_PATH = Path("eval/questions.yaml")
EXPECTED_PATH = Path("eval/expected_results.json")


def main() -> None:
    con = make_connection()  # la même connexion verrouillée que l'agent
    questions = load_questions(QUESTIONS_PATH)
    results = {}

    for question in questions:
        if question.expected_behavior != Behavior.ANSWER:
            continue  # un piège n'a pas de SQL : son « résultat » est un comportement

        # Passe par les mêmes garde-fous que l'agent : un SQL de référence refusé
        # serait une erreur du jeu d'éval.
        result = run_query(con, question.reference_sql, max_rows=1000)
        if not result.rows:
            raise ValueError(f"{question.id} : le SQL de référence ne renvoie aucune ligne")

        results[question.id] = {"columns": result.columns, "rows": to_jsonable(result.rows)}
        print(f"{question.id} : {len(result.rows)} ligne(s) -> {result.rows}")

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "results": results,
    }
    text = json.dumps(output, indent=2, ensure_ascii=False)
    EXPECTED_PATH.write_text(text, encoding="utf-8")
    print(f"\n{len(results)} résultats figés dans {EXPECTED_PATH}")


if __name__ == "__main__":
    main()
