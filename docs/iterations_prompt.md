# Les versions du prompt système

Le prompt système est le texte d'instructions donné au modèle avant chaque question : il décrit
son rôle, les données disponibles, la démarche à suivre et les règles de réponse. Ce document
retrace ses versions successives, ce que chacune a changé et l'effet mesuré.

Chaque version a d'abord été testée sur les 10 questions de développement, les seules utilisées
pour mettre au point le prompt. Les 40 questions de test servent uniquement à la mesure finale.
Les mesures ont été faites avec qwen3:8b, sans mode réflexion, avec une température de 0 et une
fenêtre de contexte de 8 192 tokens.

Il faut garder en tête qu'un même prompt ne donne pas exactement le même score d'un passage à
l'autre. Sur 10 questions, un écart d'une ou deux questions entre deux versions peut donc venir
du hasard plutôt que du changement apporté.

## Version 1 : le prompt initial

La première version décrivait le rôle de l'agent, le périmètre des données, la démarche à suivre
(lister les tables, les décrire, exécuter une requête, vérifier le résultat) et les règles de
réponse. Elle a obtenu 7 bonnes réponses sur 10.

Les trois échecs avaient des causes différentes. Sur la question q012, l'agent s'est trompé de
niveau de détail, en calculant à partir des stations au lieu d'utiliser la série déjà agrégée.
Sur la question q024, il ne pouvait pas se corriger, car le prompt lui demandait de n'écrire
qu'une seule requête. Sur la question q046, qui était volontairement ambiguë, il a deviné une
interprétation au lieu de demander une précision.

## Version 2 : six changements à la fois, abandonnée

La deuxième version ajoutait six règles d'un coup : une correspondance entre chaque niveau de
détail et la table à utiliser, l'instruction de réutiliser les moyennes déjà calculées, celle de
ne garder que les années complètes, celle d'écrire une seule requête pour comparer plusieurs
périodes, une règle sur les superlatifs ambigus, et un message d'erreur plus utile en cas de
requête refusée.

Elle n'a obtenu que 5 sur 10. La question ambiguë q046 était désormais bien traitée, mais trois
questions qui réussissaient avant ont échoué. Le modèle associait l'expression « une station
d'Occitanie » aux tables par station, alors que la bonne réponse se trouvait dans une autre table.
Comme six changements avaient été faits en même temps, il était impossible de savoir lequel
causait cette régression. J'ai donc abandonné cette version, et j'ai retenu la leçon de ne
changer qu'une chose à la fois.

## Version 3 : une seule règle ajoutée

La troisième version reprenait la première et n'ajoutait qu'une seule règle : demander une
précision quand une question contient un superlatif sans dire selon quel critère. Le message
d'erreur amélioré a été conservé. Elle a obtenu 6 sur 10.

La question q019 a réussi grâce à une correction après une erreur SQL. La question q028 a
échoué alors qu'elle réussissait en version 1, mais elle avait déjà échoué en version 1 lors d'un
autre essai : elle change de verdict d'un passage à l'autre, indépendamment du prompt. Enfin, la
règle sur les superlatifs, pourtant identique à celle de la version 2, n'a pas été suivie cette
fois-ci sur la question q046.

Sur 10 questions et un seul passage par version, les écarts observés, d'une ou deux questions,
sont du même ordre que la variation naturelle. J'ai retenu la version 3 comme prompt de travail.

## Version 4 : le passage à DuckDB

La quatrième version est identique à la troisième. La seule différence est qu'elle parle d'une
« base DuckDB » au lieu d'un « entrepôt BigQuery », car le projet a changé de base de données. Elle
a été mesurée directement sur les 40 questions de test, puis sur les questions de développement
le 22 novembre, où elle a obtenu 5 sur 10. Elle sert de point de comparaison pour la version 5.

## Version 5 : le contrat de sortie

La cinquième version ajoute une seule règle, que l'on peut appeler un contrat de sortie : « ta
dernière requête doit renvoyer exactement la réponse, pas plus ». Par exemple, pour une question
qui demande le département le plus touché, la dernière requête doit renvoyer une seule ligne, et
non un classement complet.

Cette règle est née d'une observation. La notation compare le résultat de la dernière requête de
l'agent au résultat attendu, mais aucune version du prompt ne le disait. Un modèle commercial plus
puissant, branché sur le même serveur d'outils et testé avec la version 4, trouvait souvent la
bonne réponse mais la renvoyait au milieu d'un top 5, et la notation stricte la comptait donc
comme fausse. Ce modèle obtenait 62 % en notation stricte, mais 75 % avec la notation v2, qui
tolère les classements. Cet écart de 13 points indiquait que le problème venait de la forme des
réponses, pas du raisonnement.

Sur les questions de développement, la version 5 a obtenu 5 sur 10 puis 4 sur 10 avec qwen3:8b,
soit aucun effet mesurable. Ce résultat était attendu : les requêtes finales de qwen3:8b avaient
déjà presque toujours le bon nombre de lignes, et ses erreurs venaient de sa logique, qu'une règle
de forme ne corrige pas.

Sur les 40 questions de test, l'effet est en revanche très net pour le modèle plus puissant : son
score passe de 62 % à 82 % en notation stricte, et de 75 % à 82 % en notation v2. Les deux
notations donnent désormais le même chiffre, ce qui confirme que l'écart venait bien de la règle
manquante. Pour qwen3:8b, le score passe de 42 % à 48 % en notation stricte et de 45 % à 48 % en
notation v2. Ce gain de deux questions reste dans la marge de variation.

Deux des échecs restants du modèle plus puissant sont en réalité de bonnes réponses mal notées.
Sur la question q026, il a donné les bonnes valeurs, mais sur une seule ligne au lieu de deux. Sur
la question q048, il a répondu « je n'ai pas cette donnée », une formulation correcte que la
notation ne reconnaît pas. Je n'ai pas modifié la notation pour ces deux cas : la changer après
avoir vu les résultats aurait affaibli sa crédibilité.

La version 5 est devenue le prompt par défaut.

## Piste pour une version 6

La question q024 a révélé un autre manque du même type. Elle demande de comparer deux périodes.
Avec la version 5, qwen3:8b écrit deux requêtes, une par période, et donne les deux bons chiffres
dans sa réponse. Mais la notation ne regarde que la dernière requête, qui ne contient que la
seconde période, et la réponse est donc comptée comme fausse. Une version 6 pourrait préciser
qu'une seule requête finale doit contenir toute la réponse.
