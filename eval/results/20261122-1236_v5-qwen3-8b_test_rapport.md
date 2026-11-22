# Rapport d'évaluation : v5-qwen3-8b

- Modèle : `ollama:qwen3:8b` ; prompt : `v5`
- Questions : 40 ; passages : 1

## Résultats

| Métrique | Valeur |
|---|---|
| Exactitude, notation stricte (moyenne des passages) | **48%** |
| Exactitude, notation v2 tolérante (moyenne) | **48%** |
| Exactitude par passage | 48% |
| Latence p50 / p95 | 20.6 s / 32.4 s |
| Tokens par question (entrée / sortie) | 8210 / 265 |
| Appels d'outils par question | 3.3 |
| Questions arrêtées par la limite d'étapes | 1.0 |
| Échecs techniques | 0.0 |

## Exactitude par catégorie (moyenne des passages)

| Catégorie | Exactitude |
|---|---|
| simple | 62% |
| aggregation | 62% |
| temporal | 38% |
| multi_table | 0% |
| trap | 75% |

## Coût estimé si l'agent tournait sur une API payante

Tokens mesurés × tarifs publics (relevés le 2026-11-03). Le modèle local est gratuit.

| Tarif appliqué | Par question | Pour 1 000 questions |
|---|---|---|
| API entrée de gamme | 0.00095 $ | 0.95 $ |
| API haut de gamme | 0.01907 $ | 19.07 $ |

## Questions en échec (nombre de passages ratés)

- q003 [simple] : 1/1
- q004 [simple] : 1/1
- q009 [simple] : 1/1
- q011 [aggregation] : 1/1
- q017 [aggregation] : 1/1
- q018 [aggregation] : 1/1
- q022 [temporal] : 1/1
- q023 [temporal] : 1/1
- q025 [temporal] : 1/1
- q026 [temporal] : 1/1
- q030 [temporal] : 1/1
- q031 [multi_table] : 1/1
- q032 [multi_table] : 1/1
- q034 [multi_table] : 1/1
- q035 [multi_table] : 1/1
- q036 [multi_table] : 1/1
- q037 [multi_table] : 1/1
- q039 [multi_table] : 1/1
- q040 [multi_table] : 1/1
- q047 [trap] : 1/1
- q048 [trap] : 1/1
