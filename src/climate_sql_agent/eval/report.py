"""Calcul des métriques et rapport Markdown à partir des fichiers de résultats (JSONL)."""

import json
import statistics
from pathlib import Path

# Tarifs publics par million de tokens (entrée, sortie), relevés le 2026-11-03.
# Sert à estimer ce que coûterait l'agent sur une API payante : on ne paie rien ici.
PRICES_PER_MILLION = {
    "API entrée de gamme": (0.10, 0.50),
    "API haut de gamme": (2.00, 10.00),
}
CATEGORIES = ["simple", "aggregation", "temporal", "multi_table", "trap"]


def load_run(path: Path) -> list[dict]:
    """Un fichier JSONL = un passage complet, une ligne par question."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def percentile(values: list[float], fraction: float) -> float:
    """Percentile simple (p50 = médiane, p95 = 95 % des valeurs sont en dessous)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]


def summarize(lines: list[dict]) -> dict:
    """Métriques d'un passage."""
    done = [line for line in lines if "crash" not in line]
    durations = [line["duration_s"] for line in done]
    by_category = {}
    for category in CATEGORIES:
        rows = [line for line in lines if line["category"] == category]
        if rows:
            by_category[category] = sum(line["correct"] for line in rows) / len(rows)

    return {
        "questions": len(lines),
        "accuracy": sum(line["correct"] for line in lines) / len(lines),
        # Notation v2 (classement accepté pour les questions « le plus… ») ; anciens fichiers :
        # repli sur la notation stricte.
        "accuracy_tolerant": sum(line.get("correct_tolerant", line["correct"]) for line in lines)
        / len(lines),
        "by_category": by_category,
        "p50_s": percentile(durations, 0.50),
        "p95_s": percentile(durations, 0.95),
        "input_tokens": statistics.mean(line["input_tokens"] for line in done) if done else 0,
        "output_tokens": statistics.mean(line["output_tokens"] for line in done) if done else 0,
        "tool_calls": statistics.mean(len(line["steps"]) for line in done) if done else 0,
        "stopped_by_limit": sum(line.get("stopped_by_limit", False) for line in done),
        "crashes": len(lines) - len(done),
    }


def cost_per_question(input_tokens: float, output_tokens: float) -> dict[str, float]:
    """Coût estimé d'une question pour chaque tarif public."""
    return {
        name: (input_tokens * price_in + output_tokens * price_out) / 1_000_000
        for name, (price_in, price_out) in PRICES_PER_MILLION.items()
    }


def build_report(label: str, runs: list[list[dict]]) -> str:
    """Rapport Markdown d'une configuration (un ou plusieurs passages)."""
    summaries = [summarize(run) for run in runs]
    first = runs[0][0]
    accuracies = [s["accuracy"] for s in summaries]
    mean_accuracy = statistics.mean(accuracies)
    mean = {
        key: statistics.mean(s[key] for s in summaries)
        for key in summaries[0]
        if isinstance(summaries[0][key], int | float)
    }

    lines = [
        f"# Rapport d'évaluation : {label}",
        "",
        f"- Modèle : `{first['model']}` ; prompt : `{first['prompt_version']}`",
        f"- Questions : {summaries[0]['questions']} ; passages : {len(runs)}",
        "",
        "## Résultats",
        "",
        "| Métrique | Valeur |",
        "|---|---|",
        f"| Exactitude, notation stricte (moyenne des passages) | **{mean_accuracy:.0%}** |",
        f"| Exactitude, notation v2 tolérante (moyenne) | **{mean['accuracy_tolerant']:.0%}** |",
        f"| Exactitude par passage | {', '.join(f'{a:.0%}' for a in accuracies)} |",
        f"| Latence p50 / p95 | {mean['p50_s']:.1f} s / {mean['p95_s']:.1f} s |",
        f"| Tokens par question (entrée / sortie) | {mean['input_tokens']:.0f} / "
        f"{mean['output_tokens']:.0f} |",
        f"| Appels d'outils par question | {mean['tool_calls']:.1f} |",
        f"| Questions arrêtées par la limite d'étapes | {mean['stopped_by_limit']:.1f} |",
        f"| Échecs techniques | {mean['crashes']:.1f} |",
        "",
        "## Exactitude par catégorie (moyenne des passages)",
        "",
        "| Catégorie | Exactitude |",
        "|---|---|",
    ]
    for category in CATEGORIES:
        values = [s["by_category"][category] for s in summaries if category in s["by_category"]]
        if values:
            lines.append(f"| {category} | {statistics.mean(values):.0%} |")

    lines += [
        "",
        "## Coût estimé si l'agent tournait sur une API payante",
        "",
        "Tokens mesurés × tarifs publics (relevés le 2026-11-03). Le modèle local est gratuit.",
        "",
        "| Tarif appliqué | Par question | Pour 1 000 questions |",
        "|---|---|---|",
    ]
    for name, cost in cost_per_question(mean["input_tokens"], mean["output_tokens"]).items():
        lines.append(f"| {name} | {cost:.5f} $ | {cost * 1000:.2f} $ |")

    lines += ["", "## Questions en échec (nombre de passages ratés)", ""]
    failures: dict[str, int] = {}
    for run in runs:
        for line in run:
            if not line["correct"]:
                failures[line["id"]] = failures.get(line["id"], 0) + 1
    for question_id, count in sorted(failures.items()):
        line = next(item for item in runs[0] if item["id"] == question_id)
        lines.append(f"- {question_id} [{line['category']}] : {count}/{len(runs)}")
    return "\n".join(lines) + "\n"
