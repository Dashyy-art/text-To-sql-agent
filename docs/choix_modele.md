# Choix du modèle local

Date : 2026-11-18 · Matériel : RTX 4060 Laptop (8 Go VRAM), WSL2 · Ollama 0.30

## Protocole
- 5 questions en français sur 2 marts (`mart_occitanie_yearly`, `mart_department_yearly`).
- Schéma des 2 tables donné dans le prompt système ; un seul outil `run_sql(query)`.
- Pour chaque réponse : appel d'outil produit ? SQL lisible par sqlglot (BigQuery) ?
  SQL **juste** (vérifié à la main) ? Durée (modèle préchauffé) et tokens générés.
- Script de comparaison ponctuel, retiré du dépôt depuis le passage à DuckDB (il vérifiait le
  SQL en dialecte BigQuery) ; il reste consultable dans l'historique git.

**Contrainte :** connexion limitée (4G). Plutôt que 3 modèles de taille équivalente, on compare
3 configurations sans téléchargement supplémentaire : l'effet du mode réflexion, et l'effet de la taille.

## Résultats

| Configuration | Appels d'outil | SQL lisibles | SQL justes | Temps moyen (s) | Tokens moyens |
|---|---|---|---|---|---|
| qwen3:8b (réflexion) | 5/5 | 5/5 | **5/5** | 11,6 | 410 |
| qwen3:8b (sans réflexion) | 5/5 | 5/5 | **4/5** | 1,6 | 52 |
| qwen2.5:0.5b | 4/5 | 4/5 | **1/5** | 0,7 | 88 |

## Observations
- **Lisible ≠ juste** : qwen2.5:0.5b produit un SQL accepté par sqlglot mais qui utilise une
  colonne inexistante. D'où l'évaluation par comparaison des résultats (execution accuracy).
- **Taille** : le modèle de 0,5 B invente des colonnes, se trompe de table, et une fois ne
  produit pas d'appel d'outil. Éliminé.
- **Réflexion** : +1 question juste (moyenne 2015-2024 calculée avec `AVG`), mais 7× plus lent
  et 8× plus de tokens.

## Décision
- Modèle : **qwen3:8b**.
- Mode par défaut : **sans réflexion** (itérations rapides pendant le développement).
- Le mode réflexion reste un paramètre ; il sera mesuré sur les 50 questions à l'étape 7.

## Limites
- 5 questions : l'écart 5/5 contre 4/5 n'est pas significatif. Ce test élimine et choisit un
  point de départ ; il ne tranche pas.
- Un seul tour (pas de boucle agent) : le modèle ne voit pas le résultat de sa requête et ne
  peut pas se corriger.
