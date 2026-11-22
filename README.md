# Agent text-to-SQL sur les données climatiques d'Occitanie

Ce projet est un agent conversationnel qui répond en français à des questions sur le climat
observé en Occitanie depuis 1950. Pour répondre, l'agent écrit lui-même des requêtes SQL, les
exécute sur une base de données, vérifie le résultat, puis rédige une réponse en langage
naturel.

L'agent fonctionne entièrement sur votre machine. Le modèle de langage (qwen3:8b) tourne en
local grâce à Ollama, et les données sont stockées dans un fichier DuckDB livré avec le dépôt.
Il n'y a donc besoin d'aucun compte cloud, d'aucune clé d'API, et l'utilisation ne coûte rien.

Les données proviennent de mon projet précédent,
[un pipeline de données climatiques Météo-France](https://github.com/Dashyy-art/pipeline-climat-occitanie)
construit avec Airflow et dbt. Les cinq tables finales de ce pipeline ont été copiées une seule
fois dans `data/climat.duckdb`, un fichier de 7 Mo.

Deux points distinguent ce projet d'une simple démonstration. D'abord, l'agent est évalué de
façon chiffrée sur 40 questions de test écrites avant lui. Ensuite, il est sécurisé : il ne peut
que lire les données, et cette garantie ne repose pas sur la bonne volonté du modèle mais sur
trois niveaux de protection indépendants.

## Démarrage rapide

Il faut installer au préalable [uv](https://docs.astral.sh/uv/), le gestionnaire de projets
Python, et [Ollama](https://ollama.com), qui fait tourner le modèle en local. Une carte
graphique d'au moins 8 Go de mémoire est recommandée. Sans carte graphique, l'agent fonctionne
quand même sur le processeur, mais beaucoup plus lentement.

```bash
git clone https://github.com/Dashyy-art/text-To-sql-agent.git && cd text-To-sql-agent
make install
ollama pull qwen3:8b
make ask Q="Quelle a été l'année la plus froide par rapport à la normale 1991-2020 en Occitanie ?"
```

La commande `make install` installe les dépendances Python. La commande `ollama pull`
télécharge le modèle, environ 5 Go, une seule fois. La dernière commande pose une question à
l'agent. Voici un exemple de réponse, légèrement abrégé :

```text
L'année la plus froide par rapport à la normale 1991-2020 en Occitanie a été **1996**,
avec une anomalie de **-1,18 °C**.
SELECT observation_year, mean_tmax_anomaly_c FROM marts.mart_occitanie_yearly
ORDER BY mean_tmax_anomaly_c ASC LIMIT 1

--- 4 appel(s) d'outils | list_tables > describe_table > run_sql > check_result
```

La dernière ligne montre le cheminement de l'agent. Il a d'abord demandé la liste des tables,
puis la description de la table utile, il a ensuite exécuté sa requête, et il a enfin vérifié
la cohérence du résultat avant de répondre.

## Résultats

L'agent a été mesuré sur 40 questions de test. Ces questions n'ont jamais été utilisées pendant
la mise au point du prompt, ce qui évite de surestimer le score. Les mesures ont été faites les
21 et 22 novembre 2026, sur un ordinateur portable équipé d'une carte graphique RTX 4060 de
8 Go.

| Configuration | Version du prompt | Exactitude (notation stricte) | Exactitude (notation v2) | Pièges réussis | Temps médian par question | Tokens générés par question |
|---|---|---|---|---|---|---|
| **qwen3:8b** (configuration par défaut) | **v5** | 48 % | 48 % | 75 % | 20 s | 265 |
| qwen3:8b | v4 | 42 % | 45 % | 88 % | **13,5 s** | 297 |
| qwen3.5:9b | v4 | 42 % | 52 % | 75 % | 37 s | 528 |
| qwen3:8b avec mode réflexion | v4 | **52 %** | **57 %** | **100 %** | 72 s | 1 855 |

### Comment lire ce tableau

L'exactitude est la part des questions auxquelles l'agent a répondu correctement. Pour une
question qui attend des données, la réponse est jugée juste si le résultat de la dernière
requête SQL de l'agent contient exactement les lignes attendues, avec une petite tolérance sur
les nombres. Pour un piège, la réponse est jugée juste si l'agent a eu le bon comportement : par
exemple refuser de supprimer des données, ou dire qu'une information n'existe pas au lieu
d'inventer un chiffre.

Deux notations sont publiées. La notation stricte exige le nombre exact de lignes attendu. La
notation v2 est un peu plus tolérante : pour une question du type « quel est le département le
plus touché ? », elle accepte un classement si la bonne réponse arrive en premier, et elle
reconnaît quelques formulations de refus que la première version ne détectait pas. Cette
notation v2 a été écrite après avoir lu les premières réponses. Pour rester transparent, les
deux chiffres sont donc publiés, et la même règle est appliquée à tous les modèles.

Le temps médian signifie que la moitié des questions ont reçu une réponse plus rapidement que
cette durée. Les tokens générés mesurent la quantité de texte que le modèle a produite pour
répondre, raisonnement compris.

### Ce que montrent ces résultats

Le mode réflexion, où le modèle raisonne longuement avant de répondre, est ce qui améliore le
plus les résultats. Avec le même modèle, il fait gagner 10 à 12 points et réussit tous les
pièges. En contrepartie, il rend l'agent environ cinq fois plus lent, ce qui le réserve à un
usage où l'on peut attendre plus d'une minute.

Le modèle qwen3.5:9b, plus récent, raisonne un peu mieux que qwen3:8b. Mais il est trop gros
pour tenir entièrement dans les 8 Go de la carte graphique : une partie du modèle tourne sur le
processeur, ce qui triple presque le temps de réponse.

Les résultats varient légèrement d'un passage à l'autre : environ deux questions sur quarante
changent de verdict quand on relance la même configuration. Un écart de moins de cinq points
entre deux configurations ne permet donc pas de conclure que l'une est meilleure que l'autre.
Le passage avec le prompt v5 a aussi été plus lent que celui avec le prompt v4, alors que le
modèle a produit autant de texte. Cette différence vient probablement de l'état de la machine
pendant la mesure, et elle reste à vérifier.

### Le prompt v5 et le contrat de sortie

La version 5 du prompt ajoute une seule règle : la dernière requête de l'agent doit renvoyer
exactement la réponse demandée, et non un classement complet ou toute une série d'années.
Cette règle peut sembler évidente, mais les versions précédentes ne la formulaient pas, alors
que la notation la supposait.

Ce manque a été découvert en branchant un modèle commercial plus puissant sur le même serveur
d'outils. Ce modèle avait souvent la bonne réponse, mais il renvoyait un top 5 au lieu d'une
réponse unique, et la notation stricte comptait donc sa réponse comme fausse. Avec la règle
ajoutée, son score est passé de 62 % à 82 %. Sur qwen3:8b, le gain est faible (de 42 % à 48 %,
ce qui reste dans la marge de variation), car ses erreurs viennent de son raisonnement et non de
la forme de ses réponses. Le détail de chaque version du prompt est dans
[docs/iterations_prompt.md](docs/iterations_prompt.md).

### Ce qui marche et ce qui ne marche pas encore

L'agent est fiable sur le plan de la sécurité. Il refuse les demandes d'écriture et les
tentatives de manipulation, et il dit clairement quand une donnée n'existe pas. Ses erreurs
viennent du raisonnement, pas de la syntaxe SQL. Il lui arrive par exemple de recalculer une
moyenne à partir des stations alors qu'une table régionale contient déjà ce chiffre, ou
d'écrire une logique SQL incorrecte. Les questions qui demandent de croiser plusieurs tables
restent son principal point faible, avec 0 à 12 % de réussite selon la configuration.

Les rapports détaillés de chaque évaluation sont dans [eval/results/](eval/results/). Une
première version du projet utilisait une base BigQuery dans le cloud. Elle obtenait le même
score, et ses résultats sont archivés dans
[eval/results/archive_bigquery/](eval/results/archive_bigquery/).

Le coût d'utilisation est nul, puisque tout tourne en local. À titre de comparaison, faire
traiter 1 000 questions par une API payante avec le même volume de texte coûterait environ
0,95 $ avec une API d'entrée de gamme (0,10 $ par million de tokens en entrée et 0,50 $ en
sortie), et environ 19 $ avec une API haut de gamme (2 $ et 10 $ par million de tokens).

## Architecture

```text
Question ──▶ Agent (boucle écrite à la main, modèle local qwen3:8b)
               │  appels d'outils
               ▼
             Client MCP ──stdio──▶ Serveur MCP
                                     ├─ list_tables     liste des tables et leur description
                                     ├─ describe_table  colonnes, types et lignes d'exemple
                                     ├─ run_sql         exécution d'une requête SELECT contrôlée
                                     └─ check_result    contrôles de cohérence du résultat
                                            │ connexion verrouillée en lecture seule
                                            ▼
                                     data/climat.duckdb (schéma marts)
```

Le projet est découpé en deux parties qui communiquent par le protocole MCP (*Model Context
Protocol*), un standard qui permet à un modèle de langage d'utiliser des outils fournis par un
programme séparé.

La première partie est le serveur MCP. Il donne accès à la base de données à travers quatre
outils, et c'est lui qui porte toutes les protections. Ce choix est important : la sécurité ne
dépend pas du modèle ni du programme qui l'utilise. N'importe quel client compatible MCP peut se
brancher sur ce serveur et sera soumis aux mêmes règles. On peut d'ailleurs tester le serveur à
la main avec l'outil MCP Inspector, grâce à la commande
`npx @modelcontextprotocol/inspector uv run climate-sql-mcp`.

La seconde partie est l'agent lui-même. C'est une boucle d'une centaine de lignes : elle envoie
la question au modèle, exécute les outils que le modèle demande, lui renvoie les résultats, et
recommence jusqu'à ce que le modèle donne sa réponse finale, dans la limite de huit étapes. Je
n'ai pas utilisé de framework d'agent comme LangChain, pour que chaque étape reste visible et
explicable.

## Sécurité

L'agent ne peut que lire les données. Cette garantie repose sur trois niveaux de protection
indépendants : si l'un d'eux était contourné, les deux autres continueraient de protéger la
base. Chaque niveau est couvert par des tests automatiques, et le détail est expliqué dans
[docs/securite.md](docs/securite.md).

Le premier niveau est le moteur de base de données lui-même. La base est ouverte en lecture
seule, l'accès aux fichiers de l'ordinateur est désactivé, et ces réglages sont verrouillés
pour qu'une requête ne puisse pas les modifier. Même si une commande dangereuse arrivait
jusqu'à DuckDB, celui-ci la refuserait. Les tests le vérifient en envoyant directement à la base
des commandes comme `DROP TABLE` ou une lecture du fichier système `/etc/passwd`, sans passer
par le code de l'agent.

Le deuxième niveau est une analyse de chaque requête avant son exécution, avec la bibliothèque
sqlglot. La requête est décomposée en arbre syntaxique, et seules sont acceptées les requêtes
composées d'une seule instruction `SELECT` qui ne lit que les tables autorisées. Cette méthode
par liste blanche est plus sûre qu'une liste de mots interdits, qu'il est facile de contourner.
Une limite de 1 000 lignes est aussi ajoutée automatiquement.

Le troisième niveau impose des plafonds : une requête est interrompue au bout de 30 secondes, la
mémoire utilisée est limitée, le modèle ne reçoit jamais plus de 50 lignes de résultat, et il ne
peut pas faire plus de huit appels par question.

## Méthode d'évaluation

Le jeu d'évaluation compte 50 questions en français, que j'ai écrites avant de construire
l'agent pour ne pas l'adapter à ce qu'il savait déjà faire. Elles sont réparties en cinq
catégories de dix : questions simples, agrégations, questions temporelles, questions qui
croisent plusieurs tables, et pièges. Pour un piège, la bonne réponse n'est pas un chiffre mais
un comportement : refuser une modification des données, demander une précision quand la
question est ambiguë, ou dire qu'une donnée n'existe pas.

Dix questions servent à la mise au point du prompt, et les quarante autres sont réservées à la
mesure finale. Pour chaque question, la réponse attendue a été obtenue en exécutant une requête
SQL de référence, puis enregistrée dans un fichier versionné. Ces réponses retrouvent à
l'identique les chiffres publiés par le projet précédent, par exemple un réchauffement de
0,59 °C par décennie, ce qui confirme qu'elles sont justes.

La notation compare les résultats et non le texte des requêtes, car deux requêtes écrites
différemment peuvent donner le même résultat correct. Cette méthode s'appelle l'exactitude
d'exécution (*execution accuracy*) et c'est celle des bancs d'essai de référence du domaine.
La comparaison tolère de petites différences sur les nombres et accepte des colonnes en plus.
Elle ne vérifie l'ordre des lignes que si la question le demande. La notation a ses propres
tests, et ses verdicts ont été comparés à une notation faite à la main.

L'historique des versions du prompt, avec leurs scores, est dans
[docs/iterations_prompt.md](docs/iterations_prompt.md). Il inclut une version qui faisait baisser
le score et qui a été abandonnée.

## Limites

Le modèle local reste petit. Il se trompe parfois de niveau de détail, par exemple en
travaillant sur les stations au lieu de la série régionale, et il a du mal avec les tendances
et les comparaisons entre périodes. Une piste d'amélioration serait de lui fournir directement
les indicateurs déjà calculés, au lieu de lui faire tout recalculer en SQL.

Chaque configuration n'a été mesurée qu'une seule fois sur les 40 questions. Le protocole à trois
passages et des expériences complémentaires, par exemple l'agent privé de la documentation des
tables, sont prêts à être lancés avec `scripts/experiences.sh`.

Les pièges sont notés par la recherche de mots-clés dans la réponse, ce qui peut laisser passer
une formulation imprévue. Le jeu d'évaluation a été écrit par moi-même, ce qui peut introduire un
biais. Ce risque est atténué par la comparaison avec les chiffres publiés du projet précédent.

Enfin, les données sont figées à la date de la copie, en novembre 2026, et le nom des stations
météo n'est disponible que dans la table des vagues de chaleur.

## Commandes utiles

```bash
make ask Q="..."         # pose une question à l'agent (environ 15 secondes)
make ask-precis Q="..."  # même chose avec le mode réflexion : plus juste, environ 70 secondes
make test                # lance les 79 tests automatiques
make eval                # évaluation officielle : 40 questions de test, 3 passages
make eval-dev            # évaluation sur les 10 questions de mise au point
make experiments         # évaluation et expériences complémentaires (environ 1 h 15)
make serve               # lance le serveur MCP seul, pour un autre client MCP
```

Les 79 tests couvrent les protections, des attaques réelles contre la base, le serveur MCP et la
notation.

## Organisation du dépôt

```text
data/climat.duckdb   la base de données (les 5 tables du projet précédent)
src/climate_sql_agent/
├── warehouse/       accès à la base : analyse du SQL, connexion verrouillée, catalogue des tables
├── mcp_server/      le serveur MCP et ses 4 outils
├── agent/           la boucle de l'agent, le prompt système et la connexion au modèle
└── eval/            le jeu de questions, la notation et les rapports d'évaluation
eval/                les questions, les réponses attendues et les résultats des évaluations
docs/                choix du modèle, sécurité, versions du prompt et journal du projet
tests/               les tests automatiques
```

## Technologies

Python 3.13, uv, Ollama avec le modèle qwen3:8b, le SDK officiel MCP, DuckDB, sqlglot, Pydantic,
pytest, ruff et GitHub Actions pour l'intégration continue.
