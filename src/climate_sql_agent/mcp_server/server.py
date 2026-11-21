"""Serveur MCP : expose l'entrepôt climat à un modèle, en lecture seule."""

import logging
import os
import sys
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from climate_sql_agent.warehouse import catalog
from climate_sql_agent.warehouse.checks import check_result as run_checks
from climate_sql_agent.warehouse.executor import QueryError, make_connection, run_query

# En stdio, la sortie standard transporte le protocole : les journaux vont sur stderr.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

server = MCPServer(
    name="climat-occitanie",
    instructions=(
        "Données climatiques observées en Occitanie (Météo-France), 13 départements. "
        "Démarche : list_tables, puis describe_table, puis run_sql, puis check_result."
    ),
)

# Indique aux clients que ces outils ne modifient rien (simple indication, pas une garantie).
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False)

# Documentation dbt des marts. MARTS_DOCS=off la retire, pour mesurer son apport (étape 7).
DOCS = catalog.load_docs() if os.environ.get("MARTS_DOCS", "on") != "off" else {}
_connection = None


def get_connection():
    """Ouvre la base DuckDB (verrouillée, lecture seule) au premier besoin, puis la réutilise."""
    global _connection
    if _connection is None:
        _connection = make_connection()
    return _connection


@server.tool(annotations=READ_ONLY)
def list_tables() -> dict:
    """Liste les tables interrogeables (schéma marts) avec leur description et leur
    nombre de lignes. À appeler en premier pour savoir quelles données existent."""
    return {"tables": catalog.list_tables(get_connection(), DOCS)}


@server.tool(annotations=READ_ONLY)
def describe_table(
    table_name: Annotated[str, Field(description="Nom de la table, ex. 'mart_heatwaves'.")],
) -> dict:
    """Donne les colonnes d'une table (nom, type, description) et 3 lignes d'exemple.
    À appeler avant d'écrire une requête, pour utiliser les noms de colonnes exacts."""
    try:
        return catalog.describe_table(get_connection(), DOCS, table_name)
    except ValueError as error:
        raise ToolError(str(error)) from error


@server.tool(annotations=READ_ONLY)
def run_sql(
    query: Annotated[str, Field(description="Une seule requête SELECT, dialecte DuckDB.")],
) -> dict:
    """Exécute UNE requête SQL de lecture (dialecte DuckDB) et renvoie le résultat.

    Règles : un seul SELECT (WITH autorisé), tables écrites marts.<table>, aucune
    modification de données. Au plus 50 lignes sont renvoyées ; "truncated" indique
    s'il en existe davantage. En cas d'erreur, lis le message et corrige la requête."""
    try:
        result = run_query(get_connection(), query)
    except QueryError as error:
        logger.info("run_sql refusé : %s", error)
        raise ToolError(str(error)) from error

    logger.info("run_sql OK : %d ligne(s) en %.2f s", result.total_rows, result.duration_s)
    return {
        "sql_executed": result.sql,
        "columns": result.columns,
        "rows": catalog.to_jsonable(result.rows),
        "total_rows": result.total_rows,
        "truncated": result.truncated,
    }


@server.tool(annotations=READ_ONLY)
def check_result(
    columns: Annotated[list[str], Field(description="Le champ 'columns' renvoyé par run_sql.")],
    rows: Annotated[list[list], Field(description="Le champ 'rows' renvoyé par run_sql.")],
) -> dict:
    """Contrôle la cohérence d'un résultat de run_sql avant de répondre : résultat vide,
    valeurs NULL, valeurs hors bornes physiques (températures, jours, années, mois)."""
    warnings = run_checks(columns, rows)
    return {"ok": not warnings, "warnings": warnings}


def main() -> None:
    server.run()  # transport stdio par défaut


if __name__ == "__main__":
    main()
