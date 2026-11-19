"""Tests du niveau 3 des garde-fous, avec un faux client BigQuery (aucun appel réseau)."""

import pytest

from climate_sql_agent.warehouse.executor import QueryError, run_query


class FakeField:
    def __init__(self, name):
        self.name = name


class FakeRow:
    def __init__(self, values):
        self._values = values

    def values(self):
        return self._values


class FakeResult:
    def __init__(self, columns, rows, max_results):
        self.schema = [FakeField(c) for c in columns]
        self.total_rows = len(rows)
        self._rows = [FakeRow(r) for r in rows[:max_results]]

    def __iter__(self):
        return iter(self._rows)


class FakeJob:
    def __init__(self, bytes_processed, columns, rows):
        self.total_bytes_processed = bytes_processed
        self._columns = columns
        self._rows = rows

    def result(self, timeout=None, max_results=None):
        return FakeResult(self._columns, self._rows, max_results)


class FakeClient:
    """Imite bigquery.Client : enregistre chaque appel et renvoie des données fixes."""

    def __init__(self, bytes_processed=1_000, columns=("x",), rows=((1,),)):
        self.bytes_processed = bytes_processed
        self.columns = list(columns)
        self.rows = [list(r) for r in rows]
        self.calls = []  # liste de (sql, dry_run)

    def query(self, sql, job_config=None):
        self.calls.append((sql, bool(job_config.dry_run)))
        return FakeJob(self.bytes_processed, self.columns, self.rows)


def test_unsafe_sql_never_reaches_bigquery():
    client = FakeClient()
    with pytest.raises(QueryError, match="lecture"):
        run_query(client, "DROP TABLE marts.mart_heatwaves")
    assert client.calls == []  # refusé AVANT tout appel à BigQuery


def test_too_expensive_query_is_stopped_after_dry_run():
    client = FakeClient(bytes_processed=500 * 1024 * 1024)  # 500 Mo
    with pytest.raises(QueryError, match="trop coûteuse"):
        run_query(client, "SELECT * FROM marts.mart_station_monthly")
    assert len(client.calls) == 1  # seulement le dry run
    assert client.calls[0][1] is True  # ... et c'était bien un dry run


def test_valid_query_runs_dry_run_then_execution():
    client = FakeClient(columns=["mean_tmax_anomaly_c"], rows=[[2.21]])
    result = run_query(client, "SELECT mean_tmax_anomaly_c FROM marts.mart_occitanie_yearly")
    assert [dry for _, dry in client.calls] == [True, False]
    assert result.rows == [[2.21]]
    assert result.sql.endswith("LIMIT 1000")  # le SQL exécuté est le SQL validé


def test_rows_sent_to_model_are_truncated():
    client = FakeClient(columns=["n"], rows=[[i] for i in range(200)])
    result = run_query(client, "SELECT n FROM marts.t", max_rows=50)
    assert len(result.rows) == 50
    assert result.total_rows == 200
    assert result.truncated is True
