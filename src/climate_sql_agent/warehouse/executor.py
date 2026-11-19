"""Niveau 3 des garde-fous : exécution plafonnée sur BigQuery."""

import os
import time
from dataclasses import dataclass

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery

from climate_sql_agent.warehouse.sql_guard import UnsafeSQLError, validate_sql

MAX_BYTES_BILLED = 100 * 1024 * 1024  # 100 Mo : les marts font ~31 Mo au total
TIMEOUT_S = 30  # durée maximale d'une requête
MAX_ROWS = 50  # lignes renvoyées au modèle (le reste est compté, pas envoyé)


class QueryError(Exception):
    """Requête refusée ou en échec. Le message est destiné au modèle."""


@dataclass
class QueryResult:
    sql: str  # le SQL réellement exécuté (après validation)
    columns: list[str]
    rows: list[list]
    total_rows: int  # nombre total de lignes du résultat
    truncated: bool  # True si on n'a pas renvoyé toutes les lignes
    bytes_processed: int
    duration_s: float


def make_client() -> bigquery.Client:
    """Client BigQuery configuré par les variables d'environnement (.env)."""
    return bigquery.Client(
        project=os.environ["GCP_PROJECT_ID"],
        location=os.environ["BQ_LOCATION"],
    )


def run_query(
    client: bigquery.Client,
    sql: str,
    max_bytes: int = MAX_BYTES_BILLED,
    max_rows: int = MAX_ROWS,
) -> QueryResult:
    """Valide, estime, puis exécute une requête avec des plafonds."""
    start = time.perf_counter()

    # Niveau 2 : analyse du SQL.
    try:
        safe_sql = validate_sql(sql)
    except UnsafeSQLError as error:
        raise QueryError(str(error)) from error

    try:
        # Niveau 3a : dry run = estimation gratuite du volume lu, sans exécuter.
        dry_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        estimate = client.query(safe_sql, job_config=dry_config).total_bytes_processed or 0
        if estimate > max_bytes:
            raise QueryError(
                f"Requête trop coûteuse : elle lirait {estimate / 1e6:.0f} Mo "
                f"(plafond {max_bytes / 1e6:.0f} Mo). Sélectionne moins de colonnes "
                "ou filtre davantage."
            )

        # Niveau 3b : exécution réelle, plafonnée en octets et en durée.
        run_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=max_bytes,
            job_timeout_ms=TIMEOUT_S * 1000,
        )
        job = client.query(safe_sql, job_config=run_config)
        result = job.result(timeout=TIMEOUT_S, max_results=max_rows)

        columns = [field.name for field in result.schema]
        rows = [list(row.values()) for row in result]
    except GoogleAPICallError as error:
        # On garde le message utile ("Unrecognized name: foo"), sans l'URL technique.
        details = error.errors[0]["message"] if error.errors else error.message
        raise QueryError(f"Erreur BigQuery : {details}") from error
    except TimeoutError as error:
        raise QueryError(f"Requête trop longue (plus de {TIMEOUT_S} s).") from error

    return QueryResult(
        sql=safe_sql,
        columns=columns,
        rows=rows,
        total_rows=result.total_rows or len(rows),
        truncated=(result.total_rows or 0) > len(rows),
        bytes_processed=job.total_bytes_processed or 0,
        duration_s=round(time.perf_counter() - start, 2),
    )
