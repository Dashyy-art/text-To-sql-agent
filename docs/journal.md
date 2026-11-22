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


## Étape 4 : le serveur MCP

**Ce qu'on a fait.** J'ai exposé l'entrepôt sous forme de serveur MCP (*Model Context
Protocol*), en transport stdio, avec quatre outils en lecture seule : `list_tables` (les
cinq marts, leur description et leur volume), `describe_table` (colonnes, types,
descriptions issues de la documentation dbt du projet 1, et trois lignes d'exemple),
`run_sql` (qui passe par les trois niveaux de garde-fous de l'étape 3) et `check_result`
(contrôles de cohérence : résultat vide, valeurs NULL, valeurs hors bornes physiques).
Je l'ai testé à la main avec MCP Inspector, y compris avec de mauvaises entrées, puis
interrogé comme le ferait un client MCP du marché : il a répondu juste aux deux questions de
développement posées et a refusé une demande de suppression.

**Choix techniques.** Séparer le serveur de l'agent : le serveur porte les outils et les
garde-fous, indépendamment du modèle, et n'importe quel client MCP en profite. Le schéma
est servi par un outil plutôt que copié dans le prompt : le modèle ne lit que les tables
utiles à la question, ce qui économise des tokens et passe à l'échelle. Les descriptions
des outils et de leurs paramètres sont écrites comme des prompts (quand appeler l'outil,
avec quelles règles), et chaque erreur est un message court qui aide le modèle à se
corriger (« Table inconnue, tables disponibles : … »). Les métadonnées et les lignes
d'exemple sont lues par l'API de BigQuery sans lancer de requête, donc gratuitement. En
stdio, la sortie standard porte le protocole : aucun `print`, les journaux vont sur la
sortie d'erreur, et les chemins de fichiers sont calculés depuis l'emplacement du code,
car le client lance le serveur depuis un dossier inconnu. Le SDK `mcp` étant passé en
version 2 (`FastMCP` renommé `MCPServer`), j'ai borné sa version majeure. Les tests
passent par un client MCP en mémoire : ils vérifient le protocole complet (outils
exposés, décrits, déclarés en lecture seule) et prouvent qu'un `DROP` est refusé sans
aucun appel à BigQuery, en remplaçant le client par un objet vide. 39 tests, sans réseau
ni secret.

**Ce que j'en retiens.** La démo a trouvé un bug que mes tests n'avaient pas vu :
`check_result` prenait toute colonne contenant `_c` pour une température, si bien que
`station_count = 67` déclenchait une alerte ; sur les 40 réponses de référence, il
produisait 9 faux positifs. J'ai corrigé la reconnaissance des colonnes (par suffixe ou
par mot contenu) et ajouté un test qui fait passer les 40 bonnes réponses dans le
contrôle : un garde-fou se teste dans les deux sens, car un faux positif pousse le modèle
à « corriger » une réponse juste. La démo a aussi montré qu'un garde-fou ne protège que
le canal qu'il contrôle : dans un assistant de code généraliste, le modèle dispose aussi d'un terminal avec
mes identifiants. C'est pourquoi mon agent n'aura accès qu'aux outils MCP (risque
d'« agentivité excessive » de l'OWASP).


## Étape 5 : la boucle agent

**Ce qu'on a fait.** J'ai écrit à la main la boucle qui fait dialoguer le modèle local
(qwen3:8b via Ollama) avec le serveur MCP, en une centaine de lignes, sans framework.
L'agent lance lui-même le serveur MCP en sous-processus (stdio), récupère la liste des
quatre outils et la traduit au format d'appel d'outils d'Ollama. Ensuite, à chaque tour :
le modèle reçoit le prompt système, la question et tout l'historique ; s'il demande un
outil, mon code l'exécute via le client MCP et lui renvoie le résultat ; s'il répond en
texte, c'est la réponse finale. Une commande `climate-sql-agent "question"` affiche la
réponse, les outils appelés, les tokens consommés et la durée, et enregistre une trace
JSON complète : chaque appel d'outil avec ses arguments et son résultat, le SQL final et
son résultat (qui servira à la comparaison de l'étape 6), les tokens, le nombre d'appels
au modèle, et si la limite d'étapes a été atteinte. Un script fait tourner les 10
questions de développement et produit un résumé lisible « attendu / obtenu / outils ».

**Choix techniques.** Un agent plutôt qu'un workflow fixe : le modèle choisit ses
outils, lit le schéma des seules tables utiles et peut se corriger après une erreur SQL,
ce que j'ai observé (une requête refusée, puis réécrite correctement). La boucle est
bornée à 8 appels au modèle, avec un échec explicite au-delà, contre les boucles
infinies. L'agent n'a accès qu'aux quatre outils MCP : ni terminal ni fichiers, pour
que la question « que peut faire l'agent ? » ait une réponse nette. La température est
fixée à 0 pour rendre les passages plus reproductibles. La fenêtre de contexte est
portée à 8 192 tokens : par défaut, Ollama la limite à 4 096, alors qu'un seul passage
dépassait déjà 2 900 tokens au cinquième appel ; au-delà, Ollama coupe silencieusement
le début de la conversation, c'est-à-dire le prompt système et ses règles. Je l'ai
détecté en mesurant les tokens à chaque appel. Le prompt système est versionné
(`PROMPT_VERSION`), chaque trace enregistre sa version, et un carnet
(`docs/iterations_prompt.md`) garde l'historique des versions et de leurs scores. Le
script de développement enregistre chaque panne comme un échec technique et passe à la
question suivante, au lieu d'interrompre tout le passage.

**Résultats.** Sur les 10 questions de développement : 7/10 avec le prompt v1 (le
critère de l'étape demandait au moins 6), 5/10 avec v2, 6/10 avec v3. Une question
simple coûte environ 6 500 tokens en entrée et 15 à 20 secondes ; une question où
l'agent tâtonne, jusqu'à 24 000 tokens. Les erreurs se rangent en trois familles :
mauvais choix de granularité (calcul sur les tables par station au lieu de la série
régionale, qui donne une réponse fausse mais plausible, affirmée avec assurance),
auto-correction bloquée (le message d'erreur disait ce qui était interdit sans dire
comment faire autrement : je l'ai corrigé côté outil, pour tous les clients), et
exploration coûteuse (cinq tables décrites quand une suffit).

**Ce que j'en retiens.** Plus d'instructions n'améliore pas forcément un petit modèle.
Ma version v2 ajoutait six règles d'un coup et a fait baisser le score de 7 à 5 : l'une
d'elles, « une station précise → table par station », a été appliquée dès que le mot
« station » apparaissait, y compris dans « une station d'Occitanie en moyenne », qui
demande la série régionale. Changer six choses à la fois empêchait aussi de savoir
laquelle avait aidé ou nui ; je suis revenu à v1 avec une seule règle de plus. Surtout,
la variabilité est du même ordre que les écarts mesurés : la même règle sur les questions
ambiguës a été suivie en v2 et ignorée en v3, et une même question a répondu 1951 puis
1996 selon le passage. J'ai donc arrêté de retoucher le prompt sur 10 questions et un
seul passage : la comparaison se fera sur le jeu complet, avec plusieurs passages. Enfin,
le matériel compte : WSL ne recevait que la moitié des 16 Go de la machine, et le noyau
a tué Ollama en plein passage, faute de mémoire (diagnostic dans les journaux système,
puis plus de mémoire et de swap allouées à WSL, et Airflow arrêté pendant les mesures).
Une faute de frappe dans le `.gitignore` (une ligne collée à la précédente) a aussi
failli faire versionner un fichier de configuration : je vérifie désormais les fichiers
sensibles avec `git check-ignore` après chaque modification.


## Étapes 6 à 8 : mesure, résultats et publication

**Ce qu'on a fait.** Une commande `climate-sql-eval` fait tourner l'agent sur le jeu choisi
(dev ou test), note chaque réponse, écrit un fichier de résultats par passage et un rapport
Markdown : exactitude globale et par catégorie, latence p50/p95, tokens, coût estimé aux tarifs
publics, appels d'outils, pannes, octets BigQuery. La notation compare les résultats (tolérance
numérique, colonnes en plus admises, ordre vérifié seulement si demandé) et, pour les pièges, le
comportement ; elle a ses propres tests et donne le même verdict que ma notation manuelle sur un
passage de développement. Le modèle est préchauffé avant de chronométrer, et une panne est comptée
sans interrompre le passage. Ensuite : CI GitHub Actions (style et 62 tests, sans LLM, BigQuery ni
secret), Makefile, README avec les vrais chiffres.

**Résultats (40 questions de test, un passage complet).** 42 % d'exactitude (17/40) : 88 % sur
les pièges, 62 % sur les questions simples, 38 % en agrégation, 25 % sur plusieurs tables, 0 % en
temporel. 23 s de latence médiane, environ 8 300 tokens en entrée par question, 0 € de coût réel
(58 Mo lus dans BigQuery), environ 0,96 $ pour 1 000 questions au tarif d'une API d'entrée de gamme (0,10 $ / 0,50 $ par million de tokens). Sur
14 questions rejouées, verdict identique 14 fois sur 14. Les 23 erreurs sont classées : mauvaise
granularité (6), logique SQL incorrecte (7), résultat vide (4), auto-correction épuisée (2),
jointure manquante (1), piège raté (1), et 2 cas limites de notation comptés faux.

**Ce que j'en retiens.** L'agent écrit du SQL valide mais pas toujours le bon : aucune panne,
aucun arrêt par la limite d'étapes, mais des confusions de granularité et un raisonnement
temporel faible, que seule une mesure sur des questions jamais vues pouvait révéler (le jeu de
développement donnait 6 à 7 sur 10). Le profil est clair : sûr, mais limité en analyse ; la
prochaine étape serait une couche sémantique exposant les métriques déjà définies dans dbt, puis
le mode réflexion de qwen3 sur le jeu complet. Les expériences (trois passages, sans doc dbt, sans
`check_result`) sont prêtes mais n'ont pas été menées jusqu'au bout : je l'indique plutôt que
d'avancer des chiffres que je n'ai pas.


## Étape 9 : passage de BigQuery à DuckDB

**Ce qu'on a fait.** La première version interrogeait l'entrepôt BigQuery du projet 1. Elle
fonctionnait, mais personne d'autre ne pouvait la lancer : il fallait un compte GCP, une clé de
compte de service et le pipeline du projet 1 en ligne. J'ai choisi un projet simple et utilisable
par d'autres plutôt qu'une démonstration de technologies : les 5 tables (474 695 lignes au total)
ont été copiées une fois dans un fichier DuckDB de 7 Mo, livré avec le dépôt. On clone, on lance
`make ask`, et ça marche, sans compte, sans clé et sans frais. Le Terraform, le compte de service
et la dépendance à BigQuery ont été supprimés (le compte de service aussi côté GCP).

**Choix techniques.** Les trois niveaux de sécurité ont été transposés, pas abandonnés. Le niveau 1
devient une connexion DuckDB en lecture seule, sans accès aux fichiers ni aux extensions, avec la
configuration verrouillée ; le niveau 3, un minuteur qui interrompt une requête au-delà de 30 s et
une limite de mémoire ; le niveau 2 (sqlglot) change seulement de dialecte. Les tests attaquent
désormais une vraie base temporaire, directement, sans passer par mon code : 8 attaques refusées
par le moteur seul, base intacte après.

**Vérification.** Même nombre de lignes dans chaque table ; les 40 résultats de référence
recalculés sur DuckDB sont identiques à ceux de BigQuery (40/40) ; un seul SQL de référence a dû
être adapté (`DIV` devient `//`) ; 73 tests. Nouvelle mesure sur les 40 questions de test :
42 % d'exactitude, comme sur BigQuery. Quatre questions ont changé de verdict (2 gagnées, 2
perdues), aucune à cause du moteur : c'est la variabilité du modèle. La latence médiane passe
de 23 s à 13,5 s, car la base est locale.

**Ce que j'en retiens.** Changer de moteur, c'est changer de surface d'attaque : en lecture seule,
je pensais DuckDB inoffensif, mais il sait lire n'importe quel fichier de la machine avec
`read_csv`. Je l'ai découvert en testant les attaques une par une avant d'écrire le code, puis
fermé et couvert par des tests. Et le plus simple est souvent le meilleur choix de produit : un
projet que n'importe qui peut lancer en une commande vaut mieux qu'une architecture cloud que
personne ne peut essayer.


## Étape 10 : comparaison de modèles et notation v2

**Ce qu'on a fait.** Avec le même prompt, les mêmes outils et les mêmes 40 questions de test, j'ai
comparé trois configurations locales : qwen3:8b (la référence), qwen3.5:9b (une génération plus
récente, un peu plus grosse) et qwen3:8b avec son mode réflexion. Le harnais permet maintenant de
reprendre un passage interrompu (`--resume`), utile pour les passages longs.

**Résultats.** Notation stricte / notation v2 : qwen3:8b 42 % / 45 % en 13,5 s par question ;
qwen3.5:9b 42 % / 52 % en 37 s ; qwen3:8b avec réflexion 52 % / 57 % en 72 s, avec 100 % sur les
pièges. Le mode réflexion est le levier le plus efficace, au prix d'une latence 5 fois plus grande
et de 6 fois plus de tokens générés. qwen3.5:9b raisonne un peu mieux, mais déborde de la mémoire
graphique (21 % sur le processeur), ce qui triple presque la latence.

**La notation v2.** En lisant les réponses, j'ai vu des réponses justes comptées fausses : un
classement renvoyé avec la bonne réponse en tête (« le Gard, 1 747 épisodes », mais avec le top 3),
une demande de précision sans point d'interrogation, une absence de donnée formulée autrement que
prévu. J'ai ajouté une notation v2 (classement accepté pour les questions « le plus… », règles des
pièges élargies), avec des tests construits à partir de ces réponses réelles, et vérifié à la main
chaque verdict qui changeait. Comme cette règle a été écrite après avoir vu des résultats, les deux
chiffres sont publiés et la même règle est appliquée à toutes les configurations.

**Ce que j'en retiens.** Un score ne vaut que par sa notation : avant d'interpréter un écart entre
modèles, il faut lire les réponses. Une notation trop stricte pénalisait surtout le modèle qui
présente ses réponses sous forme de classement, et aurait fait conclure à tort que qwen3.5:9b
n'apportait rien. Et le choix d'une configuration est un compromis, pas un classement : la plus
juste est aussi la plus lente.

## Étape 11 : le contrat de sortie (prompt v5)

**Le constat.** Un modèle plus puissant, branché sur le même serveur MCP avec le même prompt,
obtenait 62 % en notation stricte mais 75 % en v2 : il renvoyait souvent un top 5 ou une série
complète, avec la bonne réponse dedans. La notation n'était pas en cause : elle compare le
résultat de la dernière requête, et le prompt ne l'avait jamais dit. Le contrat de sortie n'était
pas écrit.

**Ce qu'on a fait.** Une seule règle ajoutée (v5) : « ta dernière requête run_sql doit renvoyer
exactement la réponse, pas plus ». Mesure d'abord sur les 10 questions de dev (qwen3:8b : v4
5/10, v5 5/10 puis 4/10, pas de régression nette), puis une seule fois sur les 40 de test.

**Résultats.** Modèle plus puissant : 62 % → 82 % en notation stricte, 75 % → 82 % en v2 ; les
deux notations se rejoignent, et deux des échecs restants sont des faux négatifs de la notation
(bonnes valeurs en une ligne au lieu de deux, tournure d'absence de donnée non reconnue), laissés
tels quels. qwen3:8b : 42 % → 48 % (stricte), 45 % → 48 % (v2) ; +2 questions, dans le bruit, car
ses échecs sont des erreurs de logique et non de format. Un piège (q048) a atteint la limite de
8 étapes.

**Ce que j'en retiens.** Un écart entre deux notations est un symptôme à expliquer, pas une
raison d'assouplir la notation : ici, il révélait une spécification incomplète du prompt. Et une
règle de format aide un modèle qui raisonne juste, pas un modèle qui raisonne faux. Piste v6 :
« une seule requête finale contenant toute la réponse » (q024 : deux requêtes, une par période,
seule la dernière est notée).
