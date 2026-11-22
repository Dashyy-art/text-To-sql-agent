# Rapport d'évaluation : qwen3-reflexion

- Modèle : `ollama:qwen3:8b` ; prompt : `v4`
- Questions : 40 ; passages : 1

## Résultats

| Métrique | Valeur |
|---|---|
| Exactitude, notation stricte (moyenne des passages) | **52%** |
| Exactitude, notation v2 tolérante (moyenne) | **57%** |
| Exactitude par passage | 52% |
| Latence p50 / p95 | 72.0 s / 106.9 s |
| Tokens par question (entrée / sortie) | 8405 / 1855 |
| Appels d'outils par question | 2.5 |
| Questions arrêtées par la limite d'étapes | 0.0 |
| Échecs techniques | 0.0 |

## Exactitude par catégorie (moyenne des passages)

| Catégorie | Exactitude |
|---|---|
| simple | 62% |
| aggregation | 62% |
| temporal | 50% |
| multi_table | 12% |
| trap | 75% |

## Coût estimé si l'agent tournait sur une API payante

Tokens mesurés × tarifs publics (relevés le 2026-11-03). Le modèle local est gratuit.

| Tarif appliqué | Par question | Pour 1 000 questions |
|---|---|---|
| API entrée de gamme | 0.00177 $ | 1.77 $ |
| API haut de gamme | 0.03536 $ | 35.36 $ |

## Questions en échec (nombre de passages ratés)

- q003 [simple] : 1/1
- q005 [simple] : 1/1
- q010 [simple] : 1/1
- q011 [aggregation] : 1/1
- q013 [aggregation] : 1/1
- q017 [aggregation] : 1/1
- q023 [temporal] : 1/1
- q025 [temporal] : 1/1
- q026 [temporal] : 1/1
- q030 [temporal] : 1/1
- q031 [multi_table] : 1/1
- q032 [multi_table] : 1/1
- q034 [multi_table] : 1/1
- q035 [multi_table] : 1/1
- q036 [multi_table] : 1/1
- q039 [multi_table] : 1/1
- q040 [multi_table] : 1/1
- q047 [trap] : 1/1
- q048 [trap] : 1/1
