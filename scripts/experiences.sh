#!/usr/bin/env bash
# Toutes les mesures des étapes 6 et 7, sur les 40 questions de test.
# À lancer depuis la racine du projet (environ 1 h 15 avec qwen3:8b sur une RTX 4060).
# Avant : fermer les programmes lourds pour laisser la mémoire au modèle.
set -euo pipefail

run() { uv run climate-sql-eval --split test "$@"; }

run --runs 3 --label reference                       # étape 6 : 3 passages pour la variabilité
run --no-docs --label sans-doc-dbt                   # étape 7 : apport de la doc dbt
run --without-tool check_result --label sans-check   # étape 7 : apport de check_result
