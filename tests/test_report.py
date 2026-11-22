"""Tests du calcul des métriques."""

from climate_sql_agent.eval.report import cost_per_question, percentile, summarize


def line(question_id, category, correct, duration=10.0, crash=False):
    base = {"id": question_id, "category": category, "correct": correct}
    if crash:
        return {**base, "crash": "panne"}
    return {
        **base,
        "duration_s": duration,
        "input_tokens": 6000,
        "output_tokens": 200,
        "steps": [{}, {}, {}],
        "bytes_processed": 1000,
    }


def test_percentile():
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert percentile(values, 0.5) in (5, 6)
    assert percentile(values, 0.95) == 10


def test_summarize_counts_accuracy_by_category_and_crashes():
    lines = [
        line("q1", "simple", True),
        line("q2", "simple", False),
        line("q3", "trap", True),
        line("q4", "trap", False, crash=True),
    ]
    summary = summarize(lines)
    assert summary["accuracy"] == 0.5
    assert summary["by_category"] == {"simple": 0.5, "trap": 0.5}
    assert summary["crashes"] == 1
    assert summary["tool_calls"] == 3


def test_cost_estimate():
    costs = cost_per_question(1_000_000, 1_000_000)
    assert costs["API entrée de gamme"] == 0.60
