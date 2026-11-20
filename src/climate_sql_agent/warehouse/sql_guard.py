"""Niveau 2 des garde-fous : analyse du SQL avant toute exécution."""

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

ALLOWED_DATASET = "marts"
DEFAULT_LIMIT = 1000

# Types d'instructions qui modifient des données ou la structure.
WRITE_NODES = (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop)


class UnsafeSQLError(ValueError):
    """SQL refusé. Le message est lu par le modèle : il doit l'aider à se corriger."""


def validate_sql(sql: str) -> str:
    """Vérifie qu'un SQL est une lecture sûre et renvoie le SQL à exécuter.

    Règles : une seule instruction, de type SELECT, qui ne lit que des tables
    du dataset autorisé. Ajoute un LIMIT s'il n'y en a pas.
    """
    # 1. Le SQL doit être lisible en dialecte BigQuery.
    try:
        statements = sqlglot.parse(sql, read="bigquery")
    except ParseError as error:
        raise UnsafeSQLError(f"SQL illisible en dialecte BigQuery : {error}") from error

    # "SELECT 1;" peut produire une instruction vide après le ';' : on l'ignore.
    statements = [s for s in statements if s is not None]

    # 2. Une seule instruction (bloque "SELECT ...; DROP TABLE ...").
    if len(statements) != 1:
        raise UnsafeSQLError(
            f"Une seule requête est autorisée, {len(statements)} trouvées. "
            "N'enchaîne pas plusieurs requêtes avec ';'."
        )
    tree = statements[0]

    # 3. Uniquement de la lecture : SELECT, WITH ... SELECT, UNION...
    if not isinstance(tree, exp.Query) or tree.find(*WRITE_NODES):
        raise UnsafeSQLError(
            "Seules les requêtes de lecture (SELECT) sont autorisées. "
            "Aucune modification des données n'est possible."
        )

    # 4. Toutes les tables lues doivent être dans le dataset autorisé.
    cte_names = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        is_cte = table.name in cte_names and not table.db
        if is_cte:
            continue  # référence à une sous-requête nommée (WITH), pas à une vraie table
        if table.catalog or table.db != ALLOWED_DATASET:
            raise UnsafeSQLError(
                f"Table non autorisée : {table.sql(dialect='bigquery')}. "
                f"Écris les tables sous la forme {ALLOWED_DATASET}.<nom_de_table>, "
                f"par exemple {ALLOWED_DATASET}.mart_occitanie_yearly."
            )

    # 5. Plafond de lignes : on ajoute un LIMIT s'il manque.
    if isinstance(tree, exp.Select) and not tree.args.get("limit"):
        tree = tree.limit(DEFAULT_LIMIT)

    return tree.sql(dialect="bigquery")
