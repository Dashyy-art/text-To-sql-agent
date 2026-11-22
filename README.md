# Agent text-to-SQL sur les données climatiques d'Occitanie

Cet agent répond en français à des questions sur le climat observé en Occitanie depuis 1950.
Il écrit lui-même ses requêtes SQL, les exécute sur une base DuckDB, vérifie le résultat, puis
rédige sa réponse. Tout tourne en local avec le modèle qwen3:8b via Ollama : aucun compte cloud,
aucune clé d'API, aucun coût.

Les données viennent de mon projet précédent,
[un pipeline climatique Météo-France](https://github.com/Dashyy-art/pipeline-climat-occitanie)
(Airflow, dbt), copiées une fois dans `data/climat.duckdb`. L'agent est évalué sur 40 questions
de test écrites avant lui, et il ne peut que lire les données, grâce à trois niveaux de
protection indépendants.

## Démarrage rapide

Il faut [uv](https://docs.astral.sh/uv/) et [Ollama](https://ollama.com). Une carte graphique de
8 Go est recommandée, sinon l'agent tourne plus lentement sur le processeur.

```bash
git clone https://github.com/Dashyy-art/text-To-sql-agent.git && cd text-To-sql-agent
make install
ollama pull qwen3:8b
make ask Q="Quelle a été l'année la plus froide par rapport à la normale 1991-2020 en Occitanie ?"
```

```text
L'année la plus froide par rapport à la normale 1991-2020 en Occitanie a été **1996**,
avec une anomalie de **-1,18 °C**.
SELECT observation_year, mean_tmax_anomaly_c FROM marts.mart_occitanie_yearly
ORDER BY mean_tmax_anomaly_c ASC LIMIT 1

--- 4 appel(s) d'outils | list_tables > describe_table > run_sql > check_result
```

## Résultats

Mesures sur les 40 questions de test, jamais utilisées pour mettre au point le prompt, avec une
carte graphique RTX 4060 de 8 Go.

| Configuration | Exactitude (stricte) | Exactitude (v2) | Pièges réussis | Temps médian |
|---|---|---|---|---|
| **qwen3:8b**, prompt v5 (par défaut) | 48 % | 48 % | 75 % | 20 s |
| qwen3:8b, prompt v4 | 42 % | 45 % | 88 % | 13,5 s |
| qwen3.5:9b, prompt v4 | 42 % | 52 % | 75 % | 37 s |
| qwen3:8b avec mode réflexion, prompt v4 | **52 %** | **57 %** | **100 %** | 72 s |

Une réponse est juste quand le résultat de la dernière requête de l'agent correspond à la
réponse attendue. La notation v2 accepte en plus un classement dont la première ligne est la
bonne réponse, et elle a été ajoutée après la première mesure : les deux chiffres sont donc
publiés. Un écart de moins de cinq points n'est pas significatif.

Le mode réflexion donne les meilleurs résultats mais rend l'agent cinq fois plus lent. Le prompt
v5 précise que la dernière requête doit renvoyer exactement la réponse : un modèle commercial
plus puissant, branché sur le même serveur, passe ainsi de 62 % à 82 %. Les questions qui
croisent plusieurs tables restent le point faible de toutes les configurations.

La méthode, la lecture détaillée des résultats et le coût estimé sont expliqués dans
[docs/evaluation.md](docs/evaluation.md).

## Fonctionnement

```text
Question ──▶ Agent (boucle écrite à la main, modèle local qwen3:8b)
               │  appels d'outils
               ▼
             Client MCP ──stdio──▶ Serveur MCP
                                     ├─ list_tables     liste des tables
                                     ├─ describe_table  colonnes et exemples
                                     ├─ run_sql         requête SELECT contrôlée
                                     └─ check_result    contrôle de cohérence
                                            │ lecture seule
                                            ▼
                                     data/climat.duckdb
```

L'agent est une boucle d'une centaine de lignes, sans framework : il envoie la question au
modèle, exécute les outils demandés, lui renvoie les résultats, et recommence jusqu'à la réponse
finale, en huit étapes au plus. Les outils sont fournis par un serveur MCP (*Model Context
Protocol*), un standard qui permet à n'importe quel client compatible d'utiliser ces outils avec
les mêmes protections.

## Sécurité

La sécurité ne dépend pas du prompt. La base est ouverte en lecture seule, avec l'accès aux
fichiers coupé et la configuration verrouillée. Chaque requête est analysée avant exécution et
seul un `SELECT` sur les tables autorisées est accepté. Des plafonds limitent la durée des
requêtes à 30 secondes et le résultat envoyé au modèle à 50 lignes. Les détails et les attaques
testées sont dans [docs/securite.md](docs/securite.md).

## Limites

Le modèle local est petit : il se trompe parfois de niveau de détail et peine sur les tendances
et les comparaisons de périodes. Chaque configuration n'a été mesurée qu'une fois. Les pièges
sont notés par mots-clés, et le jeu de questions a été écrit par moi-même, ce qui peut
introduire un biais. Les données sont figées à novembre 2026.

## Commandes

```bash
make ask Q="..."         # pose une question (environ 15 secondes)
make ask-precis Q="..."  # avec le mode réflexion : plus juste, environ 70 secondes
make test                # lance les 79 tests automatiques
make eval                # évaluation sur les 40 questions de test
make serve               # lance le serveur MCP seul, pour un autre client
```

## Documentation

- [docs/evaluation.md](docs/evaluation.md) : méthode d'évaluation et lecture des résultats
- [docs/securite.md](docs/securite.md) : les trois niveaux de protection
- [docs/iterations_prompt.md](docs/iterations_prompt.md) : les versions du prompt et leurs scores
- [docs/choix_modele.md](docs/choix_modele.md) : le choix du modèle
- [docs/journal.md](docs/journal.md) : le journal du projet, étape par étape

Technologies : Python 3.13, uv, Ollama, SDK MCP, DuckDB, sqlglot, Pydantic, pytest, ruff, GitHub
Actions.
