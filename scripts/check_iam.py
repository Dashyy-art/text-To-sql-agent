"""Vérifie les droits réels du compte de service de l'agent (niveau 1 : IAM).

On appelle BigQuery DIRECTEMENT, sans aucun garde-fou applicatif :
seul l'IAM peut bloquer ces requêtes.

Usage : uv run --env-file .env python scripts/check_iam.py
"""

import os

from google.api_core.exceptions import Forbidden, NotFound
from google.cloud import bigquery

CHECKS = [
    # (description, requête, doit réussir ?)
    ("Lire marts", "SELECT COUNT(*) FROM marts.mart_occitanie_yearly", True),
    (
        "Supprimer dans marts",
        "DELETE FROM marts.mart_occitanie_yearly WHERE observation_year = 1991",
        False,
    ),
    ("Supprimer une table", "DROP TABLE marts.mart_heatwaves", False),
    ("Créer une table", "CREATE TABLE marts.test_agent AS SELECT 1 AS x", False),
    ("Lire raw", "SELECT COUNT(*) FROM raw.precipitation_temperature_vent_31", False),
]


def main() -> None:
    client = bigquery.Client(
        project=os.environ["GCP_PROJECT_ID"],
        location=os.environ["BQ_LOCATION"],
    )
    print(f"Identité utilisée : {client._credentials.service_account_email}\n")

    all_ok = True
    for description, sql, should_succeed in CHECKS:
        try:
            client.query(sql).result()
            succeeded = True
            detail = "exécutée"
        except (Forbidden, NotFound) as error:
            succeeded = False
            detail = error.message.split(";")[0]

        ok = succeeded == should_succeed
        all_ok = all_ok and ok
        status = "OK " if ok else "KO "
        print(f"[{status}] {description} -> {detail}")

    print("\nTous les droits sont conformes." if all_ok else "\nATTENTION : droits non conformes !")


if __name__ == "__main__":
    main()
