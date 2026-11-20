"""Tests du niveau 2 des garde-fous : validation du SQL."""

from pathlib import Path

import pytest

from climate_sql_agent.eval.dataset import load_questions
from climate_sql_agent.warehouse.sql_guard import UnsafeSQLError, validate_sql

ACCEPTED = [
    "SELECT mean_tmax_anomaly_c FROM marts.mart_occitanie_yearly WHERE observation_year = 2022",
    "WITH t AS (SELECT station_id FROM marts.mart_heatwaves) SELECT COUNT(*) FROM t",
    "SELECT station_id FROM marts.mart_station_yearly "
    "UNION ALL SELECT station_id FROM marts.mart_heatwaves",
    "SELECT 1;",  # un seul ';' final : c'est toujours une seule requête
    "SELECT 1 /* ; DROP TABLE marts.mart_heatwaves */",  # le ';' est dans un commentaire
]

REJECTED = [
    # (requête, morceau attendu dans le message d'erreur)
    ("DELETE FROM marts.mart_occitanie_yearly WHERE true", "lecture"),
    ("DROP TABLE marts.mart_heatwaves", "lecture"),
    ("INSERT INTO marts.mart_heatwaves (station_id) VALUES ('x')", "lecture"),
    ("UPDATE marts.mart_occitanie_yearly SET mean_tmax_anomaly_c = 0 WHERE true", "lecture"),
    ("MERGE marts.a USING marts.b ON a.id = b.id WHEN MATCHED THEN DELETE", "lecture"),
    ("CREATE TABLE marts.t AS SELECT 1 AS x", "lecture"),
    ("TRUNCATE TABLE marts.mart_heatwaves", "lecture"),
    ("SELECT 1; DROP TABLE marts.mart_heatwaves", "Une seule requête"),
    ("SELECT 1; -- commentaire\nDROP TABLE marts.mart_heatwaves", "Une seule requête"),
    ("SELECT * FROM raw.precipitation_temperature_vent_31", "non autorisée"),
    ("SELECT * FROM mart_heatwaves", "non autorisée"),
    ("SELECT * FROM `autre-projet.marts.mart_heatwaves`", "non autorisée"),
    ("SELECT * FROM marts.mart_heatwaves JOIN raw.t USING (station_id)", "non autorisée"),
    ("SELECT * FROM (SELECT * FROM raw.t)", "non autorisée"),
    ("SELEC * FROM", "illisible"),
]


@pytest.mark.parametrize("sql", ACCEPTED)
def test_accepts_read_only_queries(sql):
    validate_sql(sql)  # ne doit lever aucune erreur


@pytest.mark.parametrize(("sql", "message"), REJECTED)
def test_rejects_unsafe_queries(sql, message):
    with pytest.raises(UnsafeSQLError, match=message):
        validate_sql(sql)


def test_adds_limit_when_missing():
    result = validate_sql("SELECT * FROM marts.mart_heatwaves")
    assert result.endswith("LIMIT 1000")


def test_keeps_existing_limit():
    result = validate_sql("SELECT * FROM marts.mart_heatwaves LIMIT 5")
    assert result.endswith("LIMIT 5")


def test_all_reference_sql_are_accepted():
    """Le garde-fou ne doit bloquer aucune requête légitime du jeu d'éval."""
    questions = load_questions(Path("eval/questions.yaml"))
    for question in questions:
        if question.reference_sql:
            validate_sql(question.reference_sql)
