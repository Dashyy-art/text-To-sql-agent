# Choix du modèle local

Ce document explique comment j'ai choisi le modèle de langage utilisé par l'agent. Le test a eu
lieu le 18 novembre 2026, au tout début du projet, sur un ordinateur portable équipé d'une carte
graphique RTX 4060 de 8 Go, sous WSL2, avec Ollama 0.30.

## Le protocole

J'ai posé cinq questions en français portant sur deux tables de la base : la série climatique
régionale (`mart_occitanie_yearly`) et la série par département (`mart_department_yearly`). Le
schéma de ces deux tables était donné directement dans le prompt, et le modèle disposait d'un
seul outil, `run_sql`, pour proposer une requête.

Pour chaque réponse, j'ai vérifié quatre choses. D'abord, si le modèle appelait bien l'outil au
lieu de répondre par du texte libre. Ensuite, si le SQL proposé était lisible par l'analyseur
sqlglot. Puis, si ce SQL était juste, ce que j'ai vérifié à la main. Enfin, j'ai relevé le temps
de réponse et le nombre de tokens générés, c'est-à-dire la quantité de texte produite.

Ma connexion internet était limitée (4G), ce qui rendait difficile le téléchargement de
plusieurs modèles de 5 Go. Plutôt que de comparer trois modèles de taille similaire, j'ai donc
comparé trois configurations qui ne demandaient pas de nouveau téléchargement. Cela permettait
de mesurer deux effets : celui du mode réflexion, en testant qwen3:8b avec et sans, et celui de
la taille du modèle, en ajoutant le très petit qwen2.5:0.5b.

Le script utilisé pour ce test vérifiait le SQL dans le dialecte de BigQuery, la base de
l'époque. Il a été retiré du dépôt lors du passage à DuckDB, mais il reste consultable dans
l'historique git.

## Les résultats

| Configuration | Appels d'outil corrects | SQL lisibles | SQL justes | Temps moyen | Tokens générés en moyenne |
|---|---|---|---|---|---|
| qwen3:8b avec réflexion | 5 sur 5 | 5 sur 5 | **5 sur 5** | 11,6 s | 410 |
| qwen3:8b sans réflexion | 5 sur 5 | 5 sur 5 | **4 sur 5** | 1,6 s | 52 |
| qwen2.5:0.5b | 4 sur 5 | 4 sur 5 | **1 sur 5** | 0,7 s | 88 |

## Ce que j'ai observé

Une requête lisible n'est pas forcément une requête juste. Le petit modèle qwen2.5:0.5b
produisait du SQL que l'analyseur acceptait, mais qui utilisait une colonne inexistante. C'est
pour cette raison que l'évaluation finale du projet compare les résultats obtenus en exécutant
les requêtes, et non le texte du SQL.

La taille du modèle compte beaucoup. Le modèle de 0,5 milliard de paramètres inventait des
colonnes, se trompait de table, et une fois n'a même pas appelé l'outil. Je l'ai donc écarté.

Le mode réflexion a permis de répondre juste à une question de plus : une moyenne sur la période
2015-2024, qu'il a correctement calculée avec `AVG`. En revanche, il était sept fois plus lent et
générait huit fois plus de texte.

## La décision

J'ai choisi qwen3:8b, utilisé par défaut sans le mode réflexion. Ce choix permettait d'itérer
rapidement pendant le développement, avec des réponses en moins de deux secondes. Le mode
réflexion est resté disponible sous forme de paramètre, pour être mesuré plus tard sur un jeu de
questions plus large.

Cette mesure a été faite ensuite, sur les 40 questions de test et avec l'agent complet. Le mode
réflexion obtient 52 % de bonnes réponses contre 42 % sans réflexion, mais il met 72 secondes par
question au lieu de 13,5. Les résultats complets sont dans le README.

## Les limites de ce test

Avec seulement cinq questions, l'écart entre 5 sur 5 et 4 sur 5 n'est pas significatif. Ce test
servait à écarter les configurations clairement insuffisantes et à choisir un point de départ,
pas à désigner définitivement le meilleur modèle.

Par ailleurs, le modèle n'avait droit qu'à un seul essai. À ce stade du projet, la boucle de
l'agent n'existait pas encore : le modèle proposait une requête, mais il ne voyait jamais son
résultat et ne pouvait donc pas se corriger. La boucle construite à l'étape 5, dans
`agent/loop.py`, lève cette limite. Le modèle peut désormais faire jusqu'à huit appels d'outils,
et il reçoit à chaque fois le résultat ou le message d'erreur, ce qui lui permet de corriger sa
requête.
