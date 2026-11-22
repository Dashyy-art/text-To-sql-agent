# Rapport d'évaluation : v5-contrat

- Modèle : `ollama:qwen3:8b` ; prompt : `v5`
- Questions : 10 ; passages : 1

## Résultats

| Métrique | Valeur |
|---|---|
| Exactitude, notation stricte (moyenne des passages) | **50%** |
| Exactitude, notation v2 tolérante (moyenne) | **50%** |
| Exactitude par passage | 50% |
| Latence p50 / p95 | 19.9 s / 46.5 s |
| Tokens par question (entrée / sortie) | 10308 / 368 |
| Appels d'outils par question | 3.9 |
| Questions arrêtées par la limite d'étapes | 0.0 |
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
| API entrée de gamme | 0.00122 $ | 1.22 $ |
| API haut de gamme | 0.02430 $ | 24.30 $ |

## Questions en échec (nombre de passages ratés)

- q019 [aggregation] : 1/1
- q024 [temporal] : 1/1
- q033 [multi_table] : 1/1
- q038 [multi_table] : 1/1
- q046 [trap] : 1/1
