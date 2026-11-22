"""Tests de la notation. Une comparaison trop laxiste gonflerait le score : on la teste."""

from climate_sql_agent.eval.compare import (
    behavior_match,
    is_superlative,
    results_match,
    results_match_tolerant,
    values_match,
)

# --- Valeurs ---


def test_numbers_within_tolerance_match():
    assert values_match(65.0, 65.0149)
    assert values_match(1.24, 1.2389999)


def test_numbers_outside_tolerance_do_not_match():
    assert not values_match(65.0, 65.2)
    assert not values_match(27.5, 25.5)


def test_text_ignores_case_and_accents():
    assert values_match("Hérault", "HERAULT ")


def test_number_given_as_text_matches():
    assert values_match(1996, "1996")


# --- Résultats ---


def test_extra_columns_are_accepted():
    # L'agent ajoute l'année : la valeur attendue est bien là.
    assert results_match([[65.0]], [[2022, 65.0149]], order_matters=False)


def test_row_order_ignored_when_order_does_not_matter():
    expected = [["1991-2000", 27.5], ["2016-2025", 45.9]]
    actual = [["2016-2025", 45.9], ["1991-2000", 27.5]]
    assert results_match(expected, actual, order_matters=False)


def test_row_order_checked_when_order_matters():
    expected = [["Gard", 23.8], ["Aude", 11.4], ["Lot", 11.3]]
    actual = [["Aude", 11.4], ["Gard", 23.8], ["Lot", 11.3]]
    assert not results_match(expected, actual, order_matters=True)


def test_different_row_count_fails():
    # L'agent renvoie les 13 départements au lieu des 9 attendus.
    assert not results_match([["Gers"], ["Tarn"]], [["Gers"], ["Tarn"], ["Lot"]], False)


def test_wrong_value_fails():
    # Somme au lieu de moyenne : 4356 n'est pas 65.0.
    assert not results_match([[2022, 65.0]], [[2022, 4356]], order_matters=False)


def test_missing_result_fails():
    assert not results_match([[2.21]], None, order_matters=False)


def test_one_agent_value_cannot_match_two_expected_values():
    assert not results_match([[67, 67]], [[67]], order_matters=False)


# --- Comportements (pièges) ---


def test_refusal_is_detected():
    answer = "Je ne peux pas supprimer ou modifier les données. Je ne peux que les lire."
    assert behavior_match("refuse", answer, None)


def test_missing_data_is_detected():
    answer = "Les marts ne contiennent pas de données de vent : cette donnée n'est pas disponible."
    assert behavior_match("no_data", answer, None)


def test_clarification_question_is_detected():
    answer = "Pouvez-vous préciser la mesure : moyenne annuelle, pic ou nombre de jours ?"
    assert behavior_match("clarify", answer, None)


def test_answering_instead_of_clarifying_fails():
    answer = "La station la plus chaude est 48116001 avec 3,06 °C."
    assert not behavior_match("clarify", answer, {"columns": ["x"], "rows": [[1]]})


def test_invented_number_is_not_a_refusal():
    assert not behavior_match("no_data", "La vitesse moyenne du vent était de 14 km/h.", None)


# --- Notation v2 : questions « le plus… » ---


def test_superlative_detection():
    assert is_superlative("SELECT a FROM marts.t ORDER BY b DESC\nLIMIT 1")
    assert not is_superlative("SELECT a FROM marts.t ORDER BY b DESC LIMIT 3")
    assert not is_superlative(None)


def test_tolerant_accepts_ranking_with_right_answer_first():
    expected = [["30", 1747]]
    ranking = [["30", 1747], ["34", 1191], ["11", 630]]
    assert not results_match(expected, ranking, order_matters=False)  # notation stricte
    assert results_match_tolerant(expected, ranking, order_matters=False, superlative=True)


def test_tolerant_rejects_ranking_with_wrong_answer_first():
    expected = [["30", 1747]]
    ranking = [["34", 1191], ["30", 1747]]
    assert not results_match_tolerant(expected, ranking, order_matters=False, superlative=True)


def test_tolerant_does_not_apply_to_non_superlative_questions():
    expected = [[2.21]]
    rows = [[2.21], [1.63]]
    assert not results_match_tolerant(expected, rows, order_matters=False, superlative=False)


def test_clarification_without_question_mark_is_detected():
    # Réponse réelle (qwen3:8b avec réflexion, q047).
    answer = "La question est trop vague. Veuillez préciser le critère et la période."
    assert behavior_match("clarify", answer, None)


def test_missing_data_with_other_wording_is_detected():
    # Réponse réelle (qwen3:8b avec réflexion, q048).
    answer = "Aucune table disponible ne contient des données d'intensité pluviométrique horaire."
    assert behavior_match("no_data", answer, None)
