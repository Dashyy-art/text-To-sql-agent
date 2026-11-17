"""Compare 3 modèles locaux sur 5 questions (étape 1 du projet).

Pour chaque modèle et chaque question, on vérifie :
- le modèle produit-il un appel d'outil (et pas du texte libre) ?
- le SQL proposé est-il lisible par sqlglot (dialecte BigQuery) ?
- combien de temps a pris la réponse ?
"""

import time

import ollama
import sqlglot
from sqlglot.errors import ParseError

# Chaque configuration = un modèle + le mode réflexion activé ou non.
# think=None : on ne précise rien (pour les modèles qui n'ont pas ce mode).
CONFIGS = [
    {"label": "qwen3:8b (réflexion)", "model": "qwen3:8b", "think": True},
    {"label": "qwen3:8b (sans réflexion)", "model": "qwen3:8b", "think": False},
    {"label": "qwen2.5:0.5b", "model": "qwen2.5:0.5b", "think": None},
]

SCHEMA = """
Table marts.mart_occitanie_yearly : une ligne par année, moyenne des stations du réseau fixe.
  - observation_year (INT64) : année, de 1991 à 2025
  - station_count (INT64) : nombre de stations utilisées
  - mean_tmax_anomaly_c (FLOAT64) : écart moyen de la température max à la normale 1991-2020 (°C)
  - mean_heat_days_per_station (FLOAT64) : jours à Tx >= 30 °C par station, en moyenne
  - mean_very_hot_days_per_station (FLOAT64) : jours à Tx >= 35 °C par station, en moyenne

Table marts.mart_department_yearly : une ligne par département et par année.
  - department_code (STRING) : code du département, ex. '34'
  - department_name (STRING) : nom du département, ex. 'Hérault'
  - observation_year (INT64)
  - station_count (INT64)
  - mean_tmax_anomaly_c (FLOAT64)
  - mean_heat_days_per_station (FLOAT64)
  - mean_very_hot_days_per_station (FLOAT64)
"""

SYSTEM_PROMPT = (
    "Tu es un assistant qui répond à des questions sur le climat en Occitanie. "
    "Pour obtenir des données, appelle l'outil run_sql avec UNE requête SQL BigQuery. "
    "Voici le schéma disponible :\n" + SCHEMA
)

RUN_SQL_TOOL = {
    "type": "function",
    "function": {
        "name": "run_sql",
        "description": "Exécute une requête SQL SELECT (dialecte BigQuery) et renvoie les lignes.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "La requête SQL à exécuter."},
            },
            "required": ["query"],
        },
    },
}

QUESTIONS = [
    "Quelle a été l'anomalie moyenne de température maximale en Occitanie en 2022 ?",
    "Quelles sont les 3 années les plus chaudes par rapport à la normale en Occitanie ?",
    "Combien de jours à 30 °C ou plus par station, en moyenne, dans l'Hérault en 2019 ?",
    "Quel département a eu le plus de jours à 35 °C par station en 2003 ?",
    "Quelle est l'anomalie moyenne en Occitanie sur les années 2015 à 2024 ?",
]


def test_question(config: dict, question: str) -> dict:
    """Pose une question avec une configuration et renvoie ce qu'on a observé."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    start = time.perf_counter()
    response = ollama.chat(
        model=config["model"],
        messages=messages,
        tools=[RUN_SQL_TOOL],
        think=config["think"],
    )
    duration_s = time.perf_counter() - start

    result = {
        "label": config["label"],
        "question": question,
        "duration_s": round(duration_s, 1),
        "output_tokens": response.eval_count,
        "tool_call": False,
        "sql": None,
        "sql_valid": False,
    }

    tool_calls = response.message.tool_calls
    if not tool_calls:
        # Le modèle a répondu en texte libre au lieu d'appeler l'outil.
        result["sql"] = f"(texte libre) {response.message.content[:200]}"
        return result

    call = tool_calls[0]
    result["tool_call"] = call.function.name == "run_sql"
    sql = call.function.arguments.get("query")
    result["sql"] = sql

    if sql:
        try:
            sqlglot.parse_one(sql, read="bigquery")
            result["sql_valid"] = True
        except ParseError:
            result["sql_valid"] = False

    return result


def main() -> None:
    results = []

    for config in CONFIGS:
        print(f"\n=== {config['label']} ===")
        # Appel « à vide » : charge le modèle sur le GPU avant de chronométrer.
        ollama.chat(model=config["model"], messages=[{"role": "user", "content": "Bonjour"}])

        for question in QUESTIONS:
            result = test_question(config, question)
            results.append(result)
            print(f"- {question}")
            print(
                f"  outil : {result['tool_call']} | SQL lisible : {result['sql_valid']}"
                f" | {result['duration_s']} s | {result['output_tokens']} tokens"
            )
            print(f"  SQL : {result['sql']}")

    print("\n=== Résumé ===")
    print("| Configuration | Appels d'outil OK | SQL lisibles | Temps moyen (s) | Tokens moyens |")
    print("|---|---|---|---|---|")
    for config in CONFIGS:
        rows = [r for r in results if r["label"] == config["label"]]
        ok_calls = sum(r["tool_call"] for r in rows)
        ok_sql = sum(r["sql_valid"] for r in rows)
        mean_time = sum(r["duration_s"] for r in rows) / len(rows)
        mean_tokens = sum(r["output_tokens"] for r in rows) / len(rows)
        print(
            f"| {config['label']} | {ok_calls}/{len(rows)} | {ok_sql}/{len(rows)}"
            f" | {mean_time:.1f} | {mean_tokens:.0f} |"
        )


if __name__ == "__main__":
    main()
