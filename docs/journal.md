# Journal du projet

## Étape 1 : mise en place et choix du modèle

**Ce qu'on a fait.** J'ai initialisé le projet avec `uv` (Python 3.13, structure `src/`,
fichier `uv.lock` pour un environnement reproductible), ajouté `ruff` et `pre-commit` pour
contrôler la qualité du code à chaque commit, et séparé la configuration des secrets
(`.env.example` versionné, `.env` et clés ignorés par git). J'ai ensuite choisi le modèle
local par une mesure plutôt que par intuition : un script pose 5 questions en français, avec
le schéma de deux tables et un outil `run_sql`, et relève pour chaque réponse si le modèle
appelle l'outil, si le SQL est lisible (`sqlglot`), s'il est juste (vérifié à la main),
la durée et le nombre de tokens générés.

**Choix techniques.** Ma connexion (4G) ne permettait pas de télécharger trois modèles de
5 Go ; j'ai donc comparé trois configurations : qwen3:8b avec et sans mode réflexion, et
qwen2.5:0.5b comme référence basse. Résultats : 5/5, 4/5 et 1/5 SQL justes. J'ai retenu
**qwen3:8b sans réflexion** par défaut : la réflexion gagne une question sur cinq mais coûte
7× plus de temps (11,6 s contre 1,6 s) et 8× plus de tokens. Elle reste un paramètre, mesuré
sur les 50 questions à l'étape 7.

**Ce que j'en retiens.** Un SQL syntaxiquement correct n'est pas forcément juste : le petit
modèle produisait des requêtes acceptées par l'analyseur mais avec des colonnes inexistantes.
C'est pourquoi l'évaluation du projet compare les résultats d'exécution, pas le texte SQL.
Cinq questions servent à éliminer et à choisir un point de départ, pas à conclure.
