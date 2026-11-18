"""Exécute les SQL de référence sur BigQuery et fige les résultats attendus.

Usage (depuis la racine du projet) :
    uv run --env-file .env python -m climate_sql_agent.eval.freeze
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from google.cloud import bigquery

from climate_sql_agent.eval.dataset import Behavior, load_questions

QUESTIONS_PATH = Path("eval/questions.yaml")
EXPECTED_PATH = Path("eval/expected_results.json")


def run_reference_sql(client: bigquery.Client, sql: str) -> tuple[dict, int]:
    """Exécute un SQL et renvoie (résultat, octets traités)."""
    job = client.query(sql)
    rows = job.result()  # attend la fin de la requête
    columns = [field.name for field in rows.schema]
    values = [list(row.values()) for row in rows]
    return {"columns": columns, "rows": values}, job.total_bytes_processed or 0


def main() -> None:
    project_id = os.environ["GCP_PROJECT_ID"]
    location = os.environ.get("BQ_LOCATION", "EU")
    client = bigquery.Client(project=project_id, location=location)

    questions = load_questions(QUESTIONS_PATH)
    results = {}
    total_bytes = 0

    for question in questions:
        if question.expected_behavior != Behavior.ANSWER:
            continue  # un piège n'a pas de SQL : son « résultat » est un comportement

        result, bytes_processed = run_reference_sql(client, question.reference_sql)
        if not result["rows"]:
            raise ValueError(f"{question.id} : le SQL de référence ne renvoie aucune ligne")

        results[question.id] = result
        total_bytes += bytes_processed
        print(f"{question.id} : {len(result['rows'])} ligne(s) -> {result['rows']}")

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "results": results,
    }
    text = json.dumps(output, indent=2, ensure_ascii=False, default=str)
    EXPECTED_PATH.write_text(text, encoding="utf-8")

    print(f"\n{len(results)} résultats figés dans {EXPECTED_PATH}")
    print(f"Octets traités au total : {total_bytes / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
