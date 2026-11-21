# Itérations du prompt système (jeu de développement, 10 questions)

Modèle : qwen3:8b, sans réflexion, température 0, contexte 8 192 tokens.
Un seul passage par version : un écart de 1 ou 2 questions peut venir de la variabilité.

| Version | Changement | Score dev | Observations |
|---|---|---|---|
| v1 | Prompt initial : rôle, périmètre, démarche, règles | 7/10 | Échecs : granularité (q012), auto-correction bloquée par « une seule requête » (q024), devine au lieu de demander (q046) |
| v2 | + carte « niveau → table », réutiliser les moyennes, années complètes, une requête pour plusieurs périodes, superlatif ambigu ; message d'erreur de `sql_guard` plus utile | 5/10 | q046 corrigé. Régressions : « une station d'Occitanie » associé aux tables par station (q002, q012, q024). 6 changements à la fois : impossible d'attribuer l'effet. Abandonné. |
| v3 | v1 + la seule règle du superlatif ambigu (message d'erreur `sql_guard` conservé) | 6/10 | q019 auto-corrigée après une erreur SQL. q028 échoue (tables par station) alors qu'elle réussissait en v1 : la même question avait déjà échoué en v1 en ligne de commande, elle bascule d'un passage à l'autre. q046 : la règle du superlatif, identique à v2, n'a pas été suivie. |
| v4 | v3, avec « base DuckDB » au lieu d'« entrepôt BigQuery » (passage à DuckDB, aucune autre modification) | 5/10 (mesuré le 22/11 sur DuckDB) | Base de comparaison pour v5 |
| v5 | v4 + contrat de sortie : « ta dernière requête run_sql doit renvoyer exactement la réponse, pas plus » | 5/10 et 4/10 (2 passages) | Aucun effet mesurable sur qwen3:8b, dont les requêtes finales avaient déjà le bon nombre de lignes : ses échecs sont logiques. Effet net sur un modèle plus puissant qui renvoyait des classements au lieu d'une réponse unique (voir ci-dessous). q024 révèle un autre défaut de contrat : deux requêtes (une par période), seule la dernière est notée. |

**Conclusion de l'étape 5.** Sur 10 questions et un seul passage, les écarts entre versions
(1 à 2 questions) sont du même ordre que la variabilité : la même règle sur les questions
ambiguës a réussi en v2 et échoué en v3, et q028 bascule d'un passage à l'autre. v3 est
retenu comme prompt de travail ; la comparaison v1 / v3 sera refaite avec plusieurs passages.

**Prompt v5 : contrat de sortie (22/11).** La notation compare le résultat de la dernière
requête au résultat attendu, mais le prompt ne le disait pas. Un modèle plus puissant, testé
sur le même serveur MCP, renvoyait souvent un top 5 avec la bonne réponse en tête, compté
faux en notation stricte. La v5 rend ce contrat explicite. Sur ce modèle et les 40 questions
de test : notation stricte de 62 % à 82 %, notation v2 de 75 % à 82 % : l'écart entre les
deux notations disparaît. Deux échecs restants de la v5 sont des faux négatifs de la notation
(q026 : bonnes valeurs en une ligne au lieu de deux ; q048 : « je n'ai pas cette donnée »,
tournure non reconnue), non corrigés pour ne pas modifier la notation après coup.
Piste v6 : « une seule requête finale qui contient toute la réponse ».
Sur qwen3:8b et les 40 questions de test, la v5 donne 48 % (stricte) et 48 % (v2), contre 42 % et
45 % en v4 : +2 questions, dans le bruit. La v5 devient le prompt par défaut.
