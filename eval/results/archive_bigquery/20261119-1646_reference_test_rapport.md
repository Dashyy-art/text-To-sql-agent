# Rapport d'évaluation : reference

- Modèle : `ollama:qwen3:8b` ; prompt : `v3`
- Questions : 40 ; passages : 1

## Résultats

| Métrique | Valeur |
|---|---|
| Exactitude (moyenne des passages) | **42%** |
| Exactitude par passage | 42% |
| Latence p50 / p95 | 22.8 s / 58.2 s |
| Tokens par question (entrée / sortie) | 8276 / 273 |
| Appels d'outils par question | 3.5 |
| Questions arrêtées par la limite d'étapes | 0.0 |
| Échecs techniques | 0.0 |
| Octets BigQuery lus par passage | 57.8 Mo |

## Exactitude par catégorie (moyenne des passages)

| Catégorie | Exactitude |
|---|---|
| simple | 62% |
| aggregation | 38% |
| temporal | 0% |
| multi_table | 25% |
| trap | 88% |

## Coût estimé si l'agent tournait sur une API payante

Tokens mesurés × tarifs publics (relevés le 2026-11-03). Le modèle local est gratuit.

| Tarif appliqué | Par question | Pour 1 000 questions |
|---|---|---|
| API entrée de gamme | 0.00096 $ | 0.96 $ |
| API haut de gamme | 0.01928 $ | 19.28 $ |

## Questions en échec (nombre de passages ratés)

- q003 [simple] : 1/1
- q004 [simple] : 1/1
- q009 [simple] : 1/1
- q011 [aggregation] : 1/1
- q013 [aggregation] : 1/1
- q017 [aggregation] : 1/1
- q018 [aggregation] : 1/1
- q020 [aggregation] : 1/1
- q021 [temporal] : 1/1
- q022 [temporal] : 1/1
- q023 [temporal] : 1/1
- q025 [temporal] : 1/1
- q026 [temporal] : 1/1
- q027 [temporal] : 1/1
- q029 [temporal] : 1/1
- q030 [temporal] : 1/1
- q031 [multi_table] : 1/1
- q032 [multi_table] : 1/1
- q035 [multi_table] : 1/1
- q036 [multi_table] : 1/1
- q039 [multi_table] : 1/1
- q040 [multi_table] : 1/1
- q047 [trap] : 1/1
