
## Niveau 2 : analyse du SQL (sqlglot, dialecte BigQuery)

Liste blanche : une seule instruction, de type `SELECT` (ou `WITH … SELECT`, `UNION`),
lisant uniquement des tables `marts.<table>` ; ajout d'un `LIMIT 1000` si absent. Le SQL
exécuté est celui régénéré depuis l'arbre analysé. Tests : `tests/test_sql_guard.py`
(15 attaques refusées, 5 lectures acceptées, et les 40 SQL de référence acceptés).

## Niveau 3 : plafonds BigQuery

| Plafond | Valeur | Mécanisme |
|---|---|---|
| Volume lu | 100 Mo | `dry_run` avant exécution, puis `maximum_bytes_billed` |
| Durée | 30 s | `job_timeout_ms` (côté BigQuery) et `result(timeout)` (côté client) |
| Lignes renvoyées au modèle | 50 | `max_results`, avec le total et un indicateur de troncature |

Tests sans réseau : `tests/test_executor.py` (une requête refusée n'atteint jamais
BigQuery ; une requête trop coûteuse s'arrête après le dry run).
