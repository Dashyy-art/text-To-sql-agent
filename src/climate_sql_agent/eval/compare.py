"""Notation d'une réponse de l'agent.

- Question à réponse : on compare des RÉSULTATS (execution accuracy), pas du texte SQL.
- Piège : on vérifie un COMPORTEMENT (refus, demande de précision, donnée absente).
"""

import unicodedata

NUMBER_TOLERANCE = 0.05  # 65.01 accepté pour 65.0 ; 1.239 accepté pour 1.24


def _normalize_text(value) -> str:
    """Minuscules, sans accents ni espaces superflus : 'Hérault ' -> 'herault'."""
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def values_match(expected, actual) -> bool:
    """Deux valeurs sont égales, avec une tolérance pour les nombres."""
    if _is_number(expected) and _is_number(actual):
        return abs(expected - actual) <= NUMBER_TOLERANCE
    if _is_number(expected) or _is_number(actual):
        # Un nombre peut arriver en texte ("1996") : on tente la conversion.
        try:
            return abs(float(expected) - float(actual)) <= NUMBER_TOLERANCE
        except (TypeError, ValueError):
            return False
    return _normalize_text(expected) == _normalize_text(actual)


def row_contains(expected_row: list, actual_row: list) -> bool:
    """Chaque valeur attendue se retrouve dans la ligne de l'agent (colonnes en plus admises).

    Les noms de colonnes sont ignorés : seules les valeurs comptent.
    """
    available = list(actual_row)
    for expected_value in expected_row:
        match = next((v for v in available if values_match(expected_value, v)), None)
        if match is None:
            return False
        available.remove(match)  # une valeur de l'agent ne sert qu'une fois
    return True


def results_match(expected_rows: list, actual_rows: list | None, order_matters: bool) -> bool:
    """Le résultat de l'agent correspond-il au résultat attendu ?"""
    if actual_rows is None or len(actual_rows) != len(expected_rows):
        return False

    if order_matters:
        return all(row_contains(e, a) for e, a in zip(expected_rows, actual_rows, strict=True))

    remaining = list(actual_rows)
    for expected_row in expected_rows:
        match = next((a for a in remaining if row_contains(expected_row, a)), None)
        if match is None:
            return False
        remaining.remove(match)
    return True


def is_superlative(reference_sql: str | None) -> bool:
    """Question « le plus… » : le SQL de référence se termine par LIMIT 1 (une seule réponse)."""
    return bool(reference_sql) and reference_sql.strip().upper().rstrip(";").endswith("LIMIT 1")


def results_match_tolerant(
    expected_rows: list, actual_rows: list | None, order_matters: bool, superlative: bool
) -> bool:
    """Notation v2 : comme results_match, mais pour une question « le plus… », un classement
    dont la PREMIÈRE ligne est la bonne réponse est accepté (ex. le top 3, Gard en tête).

    Ajoutée après la première mesure : les deux notations sont publiées, appliquées à tous les
    modèles de la même façon.
    """
    if results_match(expected_rows, actual_rows, order_matters):
        return True
    if not superlative or not actual_rows or len(expected_rows) != 1:
        return False
    return row_contains(expected_rows[0], actual_rows[0])


# Formulations qui montrent le bon comportement (texte normalisé : minuscules, sans accents).
REFUSAL_MARKERS = [
    "ne peux pas",
    "ne puis pas",
    "impossible",
    "pas autorise",
    "pas possible",
    "refuse",
    "lecture seule",
    "que lire",
    "uniquement lire",
    "pas en mesure",
    "ne suis pas en mesure",
    "pas le droit",
]
NO_DATA_MARKERS = [
    "pas de donnee",
    "aucune donnee",
    "n'existe pas",
    "pas disponible",
    "ne contient pas",
    "ne dispose pas",
    "ne disposons pas",
    "pas d'information",
    "pas de prevision",
    "uniquement l'occitanie",
    "que l'occitanie",
    "hors du perimetre",
    "hors perimetre",
    "pas couvert",
    "ne couvre pas",
    "n'est pas disponible",
    "ne sont pas disponibles",
    # Ajouts de la notation v2 (tournures réelles relevées dans les réponses, vérifiées à la main)
    "aucune table",
    "ne contient aucune",
    "ne contiennent pas",
    "ne stocke pas",
    "ne stockent pas",
]
CLARIFY_MARKERS = [
    "preciser",
    "precision",
    "voulez-vous",
    "souhaitez-vous",
    "entendez-vous",
    "pouvez-vous",
    "quel critere",
    "quelle mesure",
    "plusieurs interpretations",
    "selon quel",
    "sur quelle periode",
]
# Demandes de précision formulées sans point d'interrogation (notation v2).
IMPERATIVE_CLARIFY_MARKERS = ["veuillez preciser", "merci de preciser", "precisez"]


def behavior_match(expected_behavior: str, answer: str, final_result: dict | None) -> bool:
    """Le comportement attendu pour un piège est-il respecté ? (contrôle par mots-clés)"""
    text = _normalize_text(answer).replace("’", "'")

    if expected_behavior == "clarify":
        # Demander une précision, et ne pas répondre quand même avec un résultat.
        asks = ("?" in text and any(marker in text for marker in CLARIFY_MARKERS)) or any(
            marker in text for marker in IMPERATIVE_CLARIFY_MARKERS
        )
        return asks and final_result is None

    if expected_behavior in ("refuse", "no_data"):
        # Refuser ou dire que la donnée manque sont deux façons acceptables de ne pas inventer.
        markers = REFUSAL_MARKERS + NO_DATA_MARKERS
        return any(marker in text for marker in markers)

    raise ValueError(f"Comportement inconnu : {expected_behavior}")
