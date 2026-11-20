"""Tests des contrôles de cohérence (outil check_result)."""

from climate_sql_agent.warehouse.checks import check_result


def test_empty_result_is_flagged():
    assert "vide" in check_result(["x"], [])[0]


def test_plausible_result_has_no_warning():
    assert check_result(["observation_year", "mean_tmax_anomaly_c"], [[2022, 2.21]]) == []


def test_out_of_bounds_values_are_flagged():
    warnings = check_result(["observation_year", "mean_tmax_c"], [[1890, 75.0]])
    assert len(warnings) == 2


def test_anomaly_rule_applies_before_temperature_rule():
    # 15 °C est une température plausible, mais pas une anomalie annuelle.
    warnings = check_result(["mean_tmax_anomaly_c"], [[15.0]])
    assert "anomalie" in warnings[0]


def test_null_values_are_flagged():
    assert "NULL" in check_result(["heat_days"], [[None]])[0]


def test_booleans_are_not_checked_as_numbers():
    assert check_result(["is_complete_year"], [[True]]) == []
