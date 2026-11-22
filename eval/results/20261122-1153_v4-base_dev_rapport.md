# Rapport d'évaluation : v4-base

- Modèle : `ollama:qwen3:8b` ; prompt : `v4`
- Questions : 10 ; passages : 1

## Résultats

| Métrique | Valeur |
|---|---|
| Exactitude, notation stricte (moyenne des passages) | **50%** |
| Exactitude, notation v2 tolérante (moyenne) | **50%** |
| Exactitude par passage | 50% |
| Latence p50 / p95 | 13.4 s / 32.0 s |
| Tokens par question (entrée / sortie) | 10017 / 338 |
| Appels d'outils par question | 4.1 |
| Questions arrêtées par la limite d'étapes | 1.0 |
| Échecs techniques | 0.0 |

## Exactitude par catégorie (moyenne des passages)

| Catégorie | Exactitude |
|---|---|
| simple | 100% |
| aggregation | 50% |
| temporal | 50% |
| multi_table | 0% |
| trap | 50% |

## Coût estimé si l'agent tournait sur une API payante

Tokens mesurés × tarifs publics (relevés le 2026-11-03). Le modèle local est gratuit.

| Tarif appliqué | Par question | Pour 1 000 questions |
|---|---|---|
| API entrée de gamme | 0.00117 $ | 1.17 $ |
| API haut de gamme | 0.02342 $ | 23.42 $ |

## Questions en échec (nombre de passages ratés)

- q012 [aggregation] : 1/1
- q028 [temporal] : 1/1
- q033 [multi_table] : 1/1
- q038 [multi_table] : 1/1
- q046 [trap] : 1/1
