# Évaluation de l'agent

Ce document explique comment l'agent est évalué, comment lire les résultats publiés dans le
README, et ce que ces résultats montrent.

## Le jeu de questions

Le jeu d'évaluation compte 50 questions en français, que j'ai écrites avant de construire
l'agent pour ne pas l'adapter à ce qu'il savait déjà faire. Elles sont réparties en cinq
catégories de dix : questions simples, agrégations, questions temporelles, questions qui
croisent plusieurs tables, et pièges. Pour un piège, la bonne réponse n'est pas un chiffre mais
un comportement : refuser une modification des données, demander une précision quand la
question est ambiguë, ou dire qu'une donnée n'existe pas.

Dix questions servent à la mise au point du prompt, et les quarante autres sont réservées à la
mesure finale. Pour chaque question, la réponse attendue a été obtenue en exécutant une requête
SQL de référence, puis enregistrée dans `eval/expected_results.json`. Ces réponses retrouvent à
l'identique les chiffres publiés par le projet précédent, par exemple un réchauffement de
0,59 °C par décennie, ce qui confirme qu'elles sont justes.

## Comment une réponse est notée

La notation compare les résultats et non le texte des requêtes, car deux requêtes écrites
différemment peuvent donner le même résultat correct. Cette méthode s'appelle l'exactitude
d'exécution (*execution accuracy*) et c'est celle des bancs d'essai de référence du domaine.

Pour une question qui attend des données, la réponse est jugée juste si le résultat de la
dernière requête de l'agent contient exactement les lignes attendues. La comparaison tolère de
petites différences sur les nombres, accepte des colonnes en plus, et ne vérifie l'ordre des
lignes que si la question le demande. Pour un piège, la réponse est jugée juste si le texte de
l'agent montre le bon comportement, ce qui est vérifié par la recherche de mots-clés.

Deux notations sont publiées. La notation stricte exige le nombre exact de lignes attendu. La
notation v2 est un peu plus tolérante : pour une question du type « quel est le département le
plus touché ? », elle accepte un classement si la bonne réponse arrive en premier, et elle
reconnaît quelques formulations de refus que la première version ne détectait pas. Cette
notation v2 a été écrite après avoir lu les premières réponses. Pour rester transparent, les
deux chiffres sont donc publiés, et la même règle est appliquée à tous les modèles. La notation
a ses propres tests, et ses verdicts ont été comparés à une notation faite à la main.

## Comment lire le tableau des résultats

L'exactitude est la part des questions auxquelles l'agent a répondu correctement. Les pièges
réussis donnent la même mesure sur les seules questions pièges. Le temps médian signifie que la
moitié des questions ont reçu une réponse plus rapidement que cette durée. Les tokens générés
mesurent la quantité de texte que le modèle a produite pour répondre, raisonnement compris.

Les résultats varient légèrement d'un passage à l'autre : environ deux questions sur quarante
changent de verdict quand on relance la même configuration. Un écart de moins de cinq points
entre deux configurations ne permet donc pas de conclure que l'une est meilleure que l'autre.

## Ce que montrent les résultats

Le mode réflexion, où le modèle raisonne longuement avant de répondre, est ce qui améliore le
plus les résultats. Avec le même modèle, il fait gagner 10 à 12 points et réussit tous les
pièges. En contrepartie, il rend l'agent environ cinq fois plus lent.

Le modèle qwen3.5:9b, plus récent, raisonne un peu mieux que qwen3:8b. Mais il est trop gros
pour tenir entièrement dans les 8 Go de la carte graphique : une partie du modèle tourne sur le
processeur, ce qui triple presque le temps de réponse.

La version 5 du prompt ajoute une seule règle : la dernière requête doit renvoyer exactement la
réponse demandée, et non un classement complet ou toute une série d'années. Ce manque a été
découvert en branchant un modèle commercial plus puissant sur le même serveur d'outils : il avait
souvent la bonne réponse, mais au milieu d'un top 5. Avec cette règle, son score est passé de
62 % à 82 %. Sur qwen3:8b, le gain est faible (de 42 % à 48 %), car ses erreurs viennent de son
raisonnement et non de la forme de ses réponses. Le détail est dans
[iterations_prompt.md](iterations_prompt.md). Le passage avec la version 5 a aussi été plus lent,
alors que le modèle a produit autant de texte : cette différence vient probablement de l'état de
la machine pendant la mesure, et reste à vérifier.

Les erreurs de l'agent viennent du raisonnement, pas de la syntaxe SQL. Il lui arrive de
recalculer une moyenne à partir des stations alors qu'une table régionale contient déjà ce
chiffre, ou d'écrire une logique SQL incorrecte. Les questions qui croisent plusieurs tables
restent son principal point faible, avec 0 à 12 % de réussite selon la configuration.

## Coût

Le coût d'utilisation est nul, puisque tout tourne en local. À titre de comparaison, faire
traiter 1 000 questions par une API payante avec le même volume de texte coûterait environ
0,95 $ avec une API d'entrée de gamme (0,10 $ par million de tokens en entrée et 0,50 $ en
sortie), et environ 19 $ avec une API haut de gamme (2 $ et 10 $ par million de tokens).

## Les fichiers de résultats

Les rapports détaillés de chaque évaluation sont dans `eval/results/`. Une première version du
projet utilisait une base BigQuery dans le cloud. Elle obtenait le même score, et ses résultats
sont archivés dans `eval/results/archive_bigquery/`.
