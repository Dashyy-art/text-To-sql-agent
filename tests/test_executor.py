"""Tests des niveaux 1 et 3 des garde-fous, sur une vraie petite base DuckDB temporaire."""

import duckdb
import pytest

from climate_sql_agent.warehouse.executor import QueryError, make_connection, run_query


@pytest.fixture
def db_path(tmp_path):
    """Crée une base de test : un schéma marts et une table de 200 lignes."""
    path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA marts")
    con.execute("CREATE TABLE marts.t AS SELECT range AS n FROM range(200)")
    con.close()
    return path


@pytest.fixture
def con(db_path):
    """La connexion verrouillée, exactement celle utilisée par l'agent."""
    connection = make_connection(db_path)
    yield connection
    connection.close()


# --- Requêtes normales -----------------------------------------------------


def test_valid_query_returns_rows(con):
    result = run_query(con, "SELECT COUNT(*) AS total FROM marts.t")
    assert result.columns == ["total"]
    assert result.rows == [[200]]
    assert result.sql.endswith("LIMIT 1000")  # le SQL exécuté est le SQL validé


def test_rows_sent_to_model_are_truncated(con):
    result = run_query(con, "SELECT n FROM marts.t", max_rows=50)
    assert len(result.rows) == 50
    assert result.total_rows == 200
    assert result.truncated is True


def test_sql_error_gives_useful_message(con):
    with pytest.raises(QueryError, match="Erreur SQL"):
        run_query(con, "SELECT colonne_inconnue FROM marts.t")


def test_too_long_query_is_interrupted(con):
    sql = "SELECT COUNT(*) FROM marts.t a, marts.t b, marts.t c, marts.t d, marts.t e"
    with pytest.raises(QueryError, match="trop longue"):
        run_query(con, sql, timeout_s=0.5)


# --- Niveau 1 : le moteur lui-même refuse, même sans l'analyse SQL ---------
# On appelle con.execute directement, en contournant run_query et sql_guard.

ENGINE_LEVEL_ATTACKS = [
    "DROP TABLE marts.t",
    "DELETE FROM marts.t",
    "CREATE TABLE marts.x AS SELECT 1",
    "SELECT * FROM read_csv('/etc/passwd')",  # lecture d'un fichier de la machine
    "COPY (SELECT 1) TO '/tmp/fuite.csv'",  # écriture d'un fichier
    "ATTACH '/tmp/autre.duckdb' AS autre",  # ouverture d'une autre base
    "SET enable_external_access = true",  # tentative de réactiver l'accès
    "INSTALL httpfs",  # téléchargement d'une extension
]


@pytest.mark.parametrize("sql", ENGINE_LEVEL_ATTACKS)
def test_engine_refuses_attack_even_without_sql_guard(con, sql):
    with pytest.raises(duckdb.Error):
        con.execute(sql)


def test_database_file_is_unchanged_after_attacks(con, db_path):
    for sql in ENGINE_LEVEL_ATTACKS:
        try:
            con.execute(sql)
        except duckdb.Error:
            pass
    assert con.execute("SELECT COUNT(*) FROM marts.t").fetchone()[0] == 200
