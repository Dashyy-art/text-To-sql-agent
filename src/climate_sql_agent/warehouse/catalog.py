"""Catalogue des marts : tables autorisées, documentation dbt et schéma réel."""

import json
from pathlib import Path

import yaml
from google.cloud import bigquery

DATASET = "marts"
# Chemin relatif à CE fichier, et non au dossier courant : le serveur MCP peut être
# lancé depuis n'importe où (par un client MCP, par exemple).
DOCS_PATH = Path(__file__).parent / "marts_docs.yml"
SAMPLE_ROWS = 3


def to_jsonable(value):
    """Convertit dates et autres types BigQuery en types simples (texte, nombres)."""
    return json.loads(json.dumps(value, default=str))


def load_docs(path: Path = DOCS_PATH) -> dict[str, dict]:
    """Lit la documentation dbt : {table: {"description": ..., "columns": {col: desc}}}."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    docs = {}
    for model in data["models"]:
        columns = {col["name"]: col.get("description", "") for col in model.get("columns", [])}
        docs[model["name"]] = {"description": model.get("description", ""), "columns": columns}
    return docs


def allowed_tables(client: bigquery.Client) -> list[str]:
    """Noms des tables du dataset autorisé, lus dans BigQuery."""
    return sorted(item.table_id for item in client.list_tables(DATASET))


def list_tables(client: bigquery.Client, docs: dict) -> list[dict]:
    """Une ligne par table : nom complet, description, nombre de lignes."""
    tables = []
    for name in allowed_tables(client):
        table = client.get_table(f"{DATASET}.{name}")  # métadonnées : gratuit
        tables.append(
            {
                "table": f"{DATASET}.{name}",
                "description": docs.get(name, {}).get("description", ""),
                "row_count": table.num_rows,
            }
        )
    return tables


def describe_table(client: bigquery.Client, docs: dict, table_name: str) -> dict:
    """Colonnes (nom, type, description) et quelques lignes d'exemple d'une table."""
    name = table_name.removeprefix(f"{DATASET}.")
    tables = allowed_tables(client)
    if name not in tables:
        raise ValueError(f"Table inconnue : {table_name}. Tables disponibles : {', '.join(tables)}")

    table = client.get_table(f"{DATASET}.{name}")
    column_docs = docs.get(name, {}).get("columns", {})
    columns = [
        {
            "name": field.name,
            "type": field.field_type,
            "description": column_docs.get(field.name, ""),
        }
        for field in table.schema
    ]
    # list_rows lit quelques lignes sans lancer de requête : gratuit.
    sample = [dict(row) for row in client.list_rows(table, max_results=SAMPLE_ROWS)]

    return {
        "table": f"{DATASET}.{name}",
        "description": docs.get(name, {}).get("description", ""),
        "row_count": table.num_rows,
        "columns": columns,
        "sample_rows": to_jsonable(sample),
    }
