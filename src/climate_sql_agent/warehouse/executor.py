"""Accès à la base DuckDB : connexion verrouillée (niveau 1) et exécution plafonnée (niveau 3)."""

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb

from climate_sql_agent.warehouse.sql_guard import UnsafeSQLError, validate_sql

# La base est versionnée dans le dépôt : data/climat.duckdb (5 tables, ~7 Mo).
# Chemin calculé depuis ce fichier, car le serveur MCP peut être lancé depuis n'importe où.
DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "climat.duckdb"
TIMEOUT_S = 30  # durée maximale d'une requête
MAX_ROWS = 50  # lignes renvoyées au modèle (le reste est compté, pas envoyé)


class QueryError(Exception):
    """Requête refusée ou en échec. Le message est destiné au modèle."""


@dataclass
class QueryResult:
    sql: str  # le SQL réellement exécuté (après validation)
    columns: list[str]
    rows: list[list]
    total_rows: int  # nombre total de lignes du résultat (plafonné par le LIMIT)
    truncated: bool  # True si on n'a pas renvoyé toutes les lignes
    duration_s: float


def make_connection(path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Connexion verrouillée (niveau 1 des garde-fous).

    - read_only : aucune écriture possible (DROP, DELETE, CREATE refusés par le moteur) ;
    - enable_external_access=False : aucun fichier lisible ou écrivable hors de la base
      (read_csv, COPY, ATTACH), aucune extension téléchargeable ;
    - lock_configuration=True : la requête ne peut pas réactiver ces options avec SET ;
    - memory_limit et threads : la machine reste utilisable.
    """
    db_path = path or Path(os.environ.get("DUCKDB_PATH", DEFAULT_DB_PATH))
    return duckdb.connect(
        str(db_path),
        read_only=True,
        config={
            "enable_external_access": False,
            "lock_configuration": True,
            "memory_limit": "1GB",
            "threads": 2,
        },
    )


def run_query(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    max_rows: int = MAX_ROWS,
    timeout_s: float = TIMEOUT_S,
) -> QueryResult:
    """Valide (niveau 2), puis exécute avec un délai maximal (niveau 3)."""
    start = time.perf_counter()

    try:
        safe_sql = validate_sql(sql)
    except UnsafeSQLError as error:
        raise QueryError(str(error)) from error

    # DuckDB n'a pas de délai intégré : un minuteur interrompt la requête si elle dure trop.
    timer = threading.Timer(timeout_s, con.interrupt)
    timer.start()
    try:
        cursor = con.execute(safe_sql)
        columns = [description[0] for description in cursor.description]
        all_rows = cursor.fetchall()  # au plus 1 000 lignes, grâce au LIMIT ajouté
    except duckdb.InterruptException as error:
        raise QueryError(f"Requête trop longue (plus de {timeout_s:.0f} s).") from error
    except duckdb.Error as error:
        # Message utile pour le modèle, ex. « Referenced column "foo" not found ».
        raise QueryError(f"Erreur SQL : {str(error).splitlines()[0]}") from error
    finally:
        timer.cancel()

    rows = [list(row) for row in all_rows[:max_rows]]
    return QueryResult(
        sql=safe_sql,
        columns=columns,
        rows=rows,
        total_rows=len(all_rows),
        truncated=len(all_rows) > len(rows),
        duration_s=round(time.perf_counter() - start, 2),
    )
