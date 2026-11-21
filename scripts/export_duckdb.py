"""Copie UNIQUE des 5 marts du projet 1 (BigQuery) vers un fichier DuckDB local.

Ce script n'a servi qu'une fois, pour sortir le projet du cloud : depuis, l'agent lit
uniquement data/climat.duckdb. Il est gardé pour la traçabilité (d'où viennent les données).

Usage (nécessite l'entrepôt BigQuery du projet 1 et un compte qui peut le lire) :
    uv run --with google-cloud-bigquery python scripts/export_duckdb.py <id-projet-gcp>
"""

import csv
import sys
import tempfile
from pathlib import Path

import duckdb
from google.cloud import bigquery

TABLES = [
    "mart_station_monthly",
    "mart_station_yearly",
    "mart_department_yearly",
    "mart_occitanie_yearly",
    "mart_heatwaves",
]
OUTPUT = Path("data/climat.duckdb")
# Correspondance des types BigQuery -> DuckDB
TYPES = {
    "STRING": "VARCHAR",
    "INTEGER": "BIGINT",
    "FLOAT": "DOUBLE",
    "BOOLEAN": "BOOLEAN",
    "DATE": "DATE",
}


def main() -> None:
    client = bigquery.Client(project=sys.argv[1])
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.unlink(missing_ok=True)
    con = duckdb.connect(str(OUTPUT))
    con.execute("CREATE SCHEMA marts")

    with tempfile.TemporaryDirectory() as tmp:
        for name in TABLES:
            table = client.get_table(f"marts.{name}")
            columns = {field.name: TYPES[field.field_type] for field in table.schema}

            # list_rows lit la table sans requête SQL : gratuit, aucun octet facturé.
            path = Path(tmp) / f"{name}.csv"
            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(columns)
                for row in client.list_rows(table):
                    writer.writerow(row.values())

            con.execute(
                f"CREATE TABLE marts.{name} AS SELECT * FROM read_csv(?, header=true, columns=?)",
                [str(path), columns],
            )
            count = con.execute(f"SELECT COUNT(*) FROM marts.{name}").fetchone()[0]
            print(f"{name} : {count} lignes (BigQuery : {table.num_rows})")

    con.close()
    print(f"\nFichier créé : {OUTPUT} ({OUTPUT.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
