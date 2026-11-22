# Rapport d'évaluation : v5-contrat-b

- Modèle : `ollama:qwen3:8b` ; prompt : `v5`
- Questions : 10 ; passages : 1

## Résultats

| Métrique | Valeur |
|---|---|
| Exactitude, notation stricte (moyenne des passages) | **40%** |
| Exactitude, notation v2 tolérante (moyenne) | **40%** |
| Exactitude par passage | 40% |
| Latence p50 / p95 | 18.3 s / 46.1 s |
| Tokens par question (entrée / sortie) | 10352 / 320 |
| Appels d'outils par question | 3.9 |
| Questions arrêtées par la limite d'étapes | 0.0 |
| Échecs techniques | 0.0 |

## Exactitude par catégorie (moyenne des passages)

| Catégorie | Exactitude |
|---|---|
| simple | 100% |
| aggregation | 0% |
| temporal | 50% |
| multi_table | 0% |
| trap | 50% |

## Coût estimé si l'agent tournait sur une API payante

Tokens mesurés × tarifs publics (relevés le 2026-11-03). Le modèle local est gratuit.

| Tarif appliqué | Par question | Pour 1 000 questions |
|---|---|---|
| API entrée de gamme | 0.00120 $ | 1.20 $ |
| API haut de gamme | 0.02391 $ | 23.91 $ |

## Questions en échec (nombre de passages ratés)

- q012 [aggregation] : 1/1
- q019 [aggregation] : 1/1
- q024 [temporal] : 1/1
- q033 [multi_table] : 1/1
- q038 [multi_table] : 1/1
- q046 [trap] : 1/1
