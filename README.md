# Agent text-to-SQL sur les données climatiques d'Occitanie

Un agent qui répond **en français** à des questions sur 35 ans de climat en Occitanie, en
interrogeant une base **DuckDB en lecture seule**, avec un **modèle local** (qwen3:8b via
Ollama). Aucun compte cloud, aucune clé, aucun frais : on clone, et ça marche.

Les outils sont exposés par un serveur **MCP**, et l'agent est **évalué** sur 40 questions de
test écrites avant lui. Les données viennent du projet
[pipeline climat Météo-France](https://github.com/Dashyy-art/pipeline-climat-occitanie)
(Airflow, dbt), copiées une fois dans `data/climat.duckdb` (5 tables, 7 Mo).

## Démarrage rapide

Prérequis : [uv](https://docs.astral.sh/uv/) et [Ollama](https://ollama.com), avec un GPU
d'au moins 8 Go de mémoire (ou de la patience sur processeur).

```bash
git clone https://github.com/Dashyy-art/<nom-du-depot>.git && cd <nom-du-depot>
make install
ollama pull qwen3:8b
make ask Q="Quelle a été l'année la plus froide par rapport à la normale 1991-2020 en Occitanie ?"
```

Exemple de sortie (abrégée) :

```text
L'année la plus froide par rapport à la normale 1991-2020 en Occitanie a été **1996**,
avec une anomalie de **-1,18 °C**.
SELECT observation_year, mean_tmax_anomaly_c FROM marts.mart_occitanie_yearly
ORDER BY mean_tmax_anomaly_c ASC LIMIT 1

--- 4 appel(s) d'outils | list_tables > describe_table > run_sql > check_result
```

## Résultats

40 questions de test, jamais regardées pendant le réglage du prompt. Mesures des 21 et 22
novembre 2026, sur une RTX 4060 Laptop (8 Go), base DuckDB locale, mêmes outils.

| Configuration | Prompt | Exactitude (notation stricte) | Exactitude (notation v2) | Pièges de sécurité | Latence p50 | Tokens générés par question |
|---|---|---|---|---|---|---|
| **qwen3:8b** (défaut) | **v5** | 48 % | 48 % | 75 % | 20 s | 265 |
| qwen3:8b | v4 | 42 % | 45 % | 88 % | **13,5 s** | 297 |
| qwen3.5:9b | v4 | 42 % | 52 % | 75 % | 37 s | 528 |
| qwen3:8b + mode réflexion (`--think`) | v4 | **52 %** | **57 %** | **100 %** | 72 s | 1 855 |

Le prompt v5 ajoute une seule règle, le « contrat de sortie » : la dernière requête doit renvoyer
exactement la réponse, pas un classement ni toute la série. La notation compare ce résultat, mais
la v4 ne le disait pas. Avec la v5, l'écart entre notation stricte et v2 disparaît. Sur un modèle
plus puissant testé sur le même serveur MCP, qui renvoyait souvent un top 5 au lieu d'une réponse
unique, l'effet est net : de 62 % à 82 % en notation stricte
([détails](docs/iterations_prompt.md)).

- **Notation stricte** : le résultat de l'agent doit avoir exactement les lignes attendues.
  **Notation v2** : pour une question « le plus… », un classement dont la première ligne est la
  bonne réponse est accepté, et deux tournures de refus ou de demande de précision mal reconnues
  par la v1 le sont désormais. La v2 a été ajoutée après la première mesure : les deux chiffres
  sont publiés, et la même règle est appliquée à tous les modèles.
- **Le mode réflexion est le levier le plus efficace** (mesuré en v4) : +10 à +12 points, et
  100 % sur les pièges, avec le même modèle. Son prix : 5 fois plus lent et 6 fois plus de tokens générés.
- **qwen3.5:9b** raisonne un peu mieux que qwen3:8b, mais il déborde des 8 Go de mémoire
  graphique (21 % du modèle passe sur le processeur), d'où une latence presque triplée.
- **Variabilité** : entre deux passages de la même configuration, environ 2 questions sur 40
  changent de verdict. Un écart de moins de 5 points n'est donc pas significatif : le gain de la
  v5 sur qwen3:8b (+2 questions) est dans le bruit, et la latence plus élevée du passage v5
  (même nombre de tokens générés) reste à remesurer.
- **Coût** : 0 € (tout est local). Estimation sur une API payante pour 1 000 questions avec la
  configuration par défaut : 0,95 $ (API à 0,10 $ / 0,50 $ par million de tokens) ou 19,07 $
  (API à 2 $ / 10 $).

**Lecture honnête.** L'agent est sûr (il refuse les écritures et l'injection, et dit quand la
donnée n'existe pas). Ses erreurs viennent du raisonnement, pas de la syntaxe : mauvaise
granularité (calcul sur les stations au lieu de la série régionale déjà agrégée), logique SQL
incorrecte, et surtout les questions qui demandent de relier plusieurs tables (0 à 12 %).
Rapports complets : [`eval/results/`](eval/results/). La première version, sur l'entrepôt BigQuery
du projet 1, donnait le même score que la configuration par défaut (archive :
[`eval/results/archive_bigquery/`](eval/results/archive_bigquery/)).

## Architecture

```text
Question ──▶ Agent (boucle écrite à la main, ~100 lignes, modèle local qwen3:8b)
               │  appels d'outils
               ▼
             Client MCP ──stdio──▶ Serveur MCP
                                     ├─ list_tables     tables et descriptions (doc dbt)
                                     ├─ describe_table  colonnes, types, exemples
                                     ├─ run_sql         SELECT unique, contrôlé, plafonné
                                     └─ check_result    contrôles de cohérence
                                            │ connexion verrouillée en lecture seule
                                            ▼
                                     data/climat.duckdb (schéma marts)
```

- **La sécurité est côté outil, pas côté prompt** : le serveur porte les garde-fous, quel que
  soit le client. On peut le tester à la main avec MCP Inspector :
  `npx @modelcontextprotocol/inspector uv run climate-sql-mcp`.
- **Pas de framework d'agent** : la boucle est courte et entièrement explicable.
- **Simple à lancer** : la base est un fichier livré avec le dépôt.

## Garde-fous

Trois niveaux indépendants, chacun testé ([détails](docs/securite.md)) :

1. **Le moteur** : base ouverte en lecture seule, accès aux fichiers et aux extensions coupé,
   configuration verrouillée. `DROP`, `DELETE`, la lecture de `/etc/passwd`, `COPY`, `ATTACH`
   ou une tentative de réactiver l'accès sont refusés par DuckDB lui-même (testé sans passer
   par le code de l'agent).
2. **Analyse du SQL** (sqlglot) : une seule instruction, `SELECT` uniquement, tables du schéma
   `marts` uniquement, `LIMIT` ajouté. Liste blanche sur l'arbre syntaxique, pas liste noire de
   mots.
3. **Plafonds** : requête interrompue au-delà de 30 s, mémoire limitée, 50 lignes renvoyées au
   modèle, 8 appels au modèle au plus par question.

## Méthode d'évaluation

- 50 questions en français, écrites **avant** l'agent : 5 catégories de 10, dont 10 pièges dont la
  bonne réponse est un comportement (refuser, demander une précision, dire que la donnée manque).
- 10 questions de développement pour régler le prompt, 40 de test pour mesurer.
- Résultats attendus obtenus en exécutant un SQL de référence, figés et versionnés ; ils
  retrouvent à l'identique les chiffres publiés du projet 1 (+0,59 °C par décennie, etc.).
- *Execution accuracy* : on compare les résultats, avec tolérance numérique, colonnes en plus
  admises, ordre vérifié seulement si la question le demande. La notation a ses propres tests et
  a été validée contre une notation manuelle.
- Historique des versions du prompt et de leurs scores, y compris une version qui faisait
  baisser le score : [`docs/iterations_prompt.md`](docs/iterations_prompt.md).

## Limites

- Petit modèle local : confusion de granularité, faiblesse sur les tendances et les comparaisons
  de périodes. Piste : une couche sémantique exposant les métriques déjà calculées.
- Un seul passage complet par configuration ; la mesure à 3 passages et les expériences (sans doc
  dbt, sans `check_result`) sont prêtes (`scripts/experiences.sh`).
- Pièges notés par mots-clés ; jeu d'éval écrit par l'auteur (biais possible, atténué par le
  recoupement avec les chiffres publiés du projet 1).
- Données figées à la date de la copie (novembre 2026) ; le nom des stations n'existe que dans la
  table des vagues de chaleur.

## Commandes

```bash
make ask Q="..."         # une question (qwen3:8b, environ 15 s)
make ask-precis Q="..."  # mode réflexion : plus juste, environ 70 s
make test            # 79 tests : garde-fous, attaques contre la base, serveur MCP, notation
make eval            # évaluation officielle : 40 questions de test, 3 passages
make eval-dev        # 10 questions de développement
make experiments     # évaluation + expériences (environ 1 h 15)
make serve           # serveur MCP seul (stdio), pour un client MCP
```

## Structure

```text
data/climat.duckdb  les 5 tables du projet 1 (schéma marts), copiées une fois
src/climate_sql_agent/
├── warehouse/   accès à la base : sql_guard (analyse SQL), executor (verrouillage, plafonds),
│                catalog, checks
├── mcp_server/  serveur MCP et ses 4 outils
├── agent/       boucle, prompt système versionné, réglages du modèle, commande
└── eval/        jeu de questions, figeage des résultats, notation, rapport, commande d'éval
eval/            questions.yaml, expected_results.json, results/
docs/            choix du modèle, sécurité, itérations du prompt, journal du projet
tests/           79 tests
```

## Stack

Python 3.13 · uv · Ollama (qwen3:8b) · SDK MCP · DuckDB · sqlglot · Pydantic · pytest · ruff ·
GitHub Actions
