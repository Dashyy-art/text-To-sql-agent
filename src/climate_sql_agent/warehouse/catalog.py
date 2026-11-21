"""Catalogue des marts : tables autorisées, documentation dbt et schéma réel (DuckDB)."""

import json
from pathlib import Path

import duckdb
import yaml

SCHEMA = "marts"
# Chemin relatif à CE fichier, et non au dossier courant : le serveur MCP peut être
# lancé depuis n'importe où (par un client MCP, par exemple).
DOCS_PATH = Path(__file__).parent / "marts_docs.yml"
SAMPLE_ROWS = 3


def to_jsonable(value):
    """Convertit dates et autres types de la base en types simples (texte, nombres)."""
    return json.loads(json.dumps(value, default=str))


def load_docs(path: Path = DOCS_PATH) -> dict[str, dict]:
    """Lit la documentation dbt : {table: {"description": ..., "columns": {col: desc}}}."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    docs = {}
    for model in data["models"]:
        columns = {col["name"]: col.get("description", "") for col in model.get("columns", [])}
        docs[model["name"]] = {"description": model.get("description", ""), "columns": columns}
    return docs


def allowed_tables(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Noms des tables du schéma autorisé, lus dans la base."""
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = ? "
        "ORDER BY table_name",
        [SCHEMA],
    ).fetchall()
    return [row[0] for row in rows]


def list_tables(con: duckdb.DuckDBPyConnection, docs: dict) -> list[dict]:
    """Une ligne par table : nom complet, description, nombre de lignes."""
    tables = []
    for name in allowed_tables(con):
        row_count = con.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{name}").fetchone()[0]
        tables.append(
            {
                "table": f"{SCHEMA}.{name}",
                "description": docs.get(name, {}).get("description", ""),
                "row_count": row_count,
            }
        )
    return tables


def describe_table(con: duckdb.DuckDBPyConnection, docs: dict, table_name: str) -> dict:
    """Colonnes (nom, type, description) et quelques lignes d'exemple d'une table."""
    name = table_name.removeprefix(f"{SCHEMA}.")
    tables = allowed_tables(con)
    if name not in tables:
        raise ValueError(f"Table inconnue : {table_name}. Tables disponibles : {', '.join(tables)}")

    # Le nom est vérifié ci-dessus (il fait partie des tables existantes) : pas d'injection.
    schema_rows = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
        [SCHEMA, name],
    ).fetchall()
    column_docs = docs.get(name, {}).get("columns", {})
    columns = [
        {"name": column, "type": data_type, "description": column_docs.get(column, "")}
        for column, data_type in schema_rows
    ]
    cursor = con.execute(f"SELECT * FROM {SCHEMA}.{name} LIMIT {SAMPLE_ROWS}")
    headers = [description[0] for description in cursor.description]
    sample = [dict(zip(headers, row, strict=True)) for row in cursor.fetchall()]
    row_count = con.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{name}").fetchone()[0]

    return {
        "table": f"{SCHEMA}.{name}",
        "description": docs.get(name, {}).get("description", ""),
        "row_count": row_count,
        "columns": columns,
        "sample_rows": to_jsonable(sample),
    }
