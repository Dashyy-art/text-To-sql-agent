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


## Étape 2 : le jeu d'évaluation

**Ce qu'on a fait.** J'ai écrit le jeu d'évaluation **avant** l'agent, pour ne pas l'adapter
à ce qu'il sait déjà faire : 50 questions en français réparties en 5 catégories de 10
(simple, agrégation, temporel, plusieurs tables, pièges), séparées en 10 questions de
développement (les seules que je regarde pour régler le prompt) et 40 de test. Chaque
question a un SQL de référence, exécuté une fois sur BigQuery ; les 40 résultats sont
figés et datés dans `eval/expected_results.json`, versionné. Les 10 pièges n'ont pas de
SQL : leur bonne réponse est un **comportement** (refuser une écriture ou une injection
de prompt, demander une précision, dire que la donnée n'existe pas).

**Choix techniques.** Le fichier de questions est validé par un modèle Pydantic
(catégories fermées, SQL obligatoire pour une question à réponse et interdit pour un
piège, identifiants uniques) : une faute de frappe fait échouer le chargement au lieu de
fausser les scores en silence. Les questions précisent la période, l'unité et l'ordre
attendu (« du premier au troisième »), pour que la comparaison des résultats soit
juste envers l'agent. Les résultats sont figés plutôt que recalculés à chaque passage :
l'éval reste reproductible même si l'entrepôt est reconstruit.

**Ce que j'en retiens.** Le jeu d'éval a ses propres bugs. Mes SQL de référence
retrouvent à l'identique les cinq chiffres publiés du projet 1 (+0,59 °C par décennie,
jours de chaleur, vagues de chaleur, années au-dessus de la normale depuis 2014), ce qui
valide à la fois l'entrepôt et le jeu. Mais la relecture des résultats figés a aussi
révélé une note fausse (6 départements annoncés, 9 réels), et l'écriture des questions a
fait apparaître des limites de l'entrepôt : le nom des stations n'existe que dans la
table des vagues de chaleur, et une station relocalisée change d'identifiant. Ces
limites sont notées pour le README.


## Étape 3 : accès BigQuery en lecture seule et garde-fous

**Ce qu'on a fait.** J'ai construit une couche d'accès à BigQuery qui ne peut **que lire**
le dataset `marts`, protégée par trois niveaux indépendants, chacun testé. Toute requête
de l'agent suit le même chemin : validation du SQL, estimation du coût, exécution
plafonnée, puis renvoi d'un résultat tronqué accompagné de ses métadonnées (SQL réellement
exécuté, nombre total de lignes, octets lus, durée). En cas de refus ou d'échec, l'agent
reçoit une seule erreur, au message court et explicite, pour pouvoir se corriger.

**Niveau 1 : IAM (le plus fort).** Un compte de service dédié à l'agent, créé avec
Terraform dans le dépôt du projet, n'a que deux rôles : `bigquery.dataViewer` sur le seul
dataset `marts`, et `bigquery.jobUser` pour lancer des requêtes. J'ai vérifié ces droits
**pour de vrai**, en envoyant directement à BigQuery, avec ce compte et sans aucun
garde-fou applicatif, un `DELETE`, un `DROP TABLE`, un `CREATE TABLE` et une lecture de
`raw` : les quatre sont refusés par BigQuery, seule la lecture de `marts` passe. J'ai
utilisé `iam_member` et non `iam_policy` dans Terraform, pour ajouter un droit sans
écraser ceux du compte du pipeline, géré par l'autre projet.

**Niveau 2 : analyse du SQL.** Plutôt qu'une liste de mots interdits, fragile dans les deux
sens (faux refus sur un mot dans un commentaire, oubli de `TRUNCATE`), j'analyse la requête
avec `sqlglot` en dialecte BigQuery et j'applique une liste blanche : une seule
instruction, de type `SELECT`, qui ne lit que des tables `marts.<table>`, avec un
`LIMIT 1000` ajouté s'il manque. Le SQL exécuté est celui régénéré à partir de l'arbre
analysé, pour que ce qui tourne soit exactement ce qui a été vérifié. Les tests couvrent
les deux sens : 15 attaques refusées (écritures, requêtes enchaînées par `;`, écriture
cachée derrière un commentaire, tables d'un autre dataset ou d'un autre projet) et des
lectures légitimes acceptées, dont les 40 SQL de référence du jeu d'éval, pour prouver
que le garde-fou ne dégrade pas l'agent.

**Niveau 3 : plafonds BigQuery.** Un *dry run* estime gratuitement le volume lu avant
toute exécution, et la requête est refusée au-delà de 100 Mo. L'exécution réelle est
ensuite plafonnée par BigQuery lui-même (`maximum_bytes_billed`, délai de 30 s appliqué
côté serveur et côté client), et seules 50 lignes sont renvoyées au modèle, avec le total
et un indicateur de troncature. Ces règles sont testées sans réseau grâce à un faux
client BigQuery passé en paramètre (injection de dépendance) : une requête dangereuse
n'atteint jamais BigQuery, une requête trop coûteuse s'arrête au dry run.

**Ce que j'en retiens.** « Lecture seule » doit être une garantie, pas une consigne dans
un prompt : un prompt peut être contourné par une injection, des permissions non. Chaque
niveau a un rôle propre. L'IAM est la barrière infranchissable, l'analyse du SQL donne au
modèle une erreur immédiate et utile, et les plafonds protègent le coût, le temps et le
contexte du modèle. J'ai aussi appris à vérifier une hypothèse de configuration avant de
chercher un bug : les datasets étaient en région US et non EU comme je le supposais, et
une variable non enregistrée dans `.env` m'a fait perdre du temps. Enfin, le cache de
BigQuery rend gratuites les requêtes identiques récentes, ce qui réduira encore le coût
réel de l'évaluation.
