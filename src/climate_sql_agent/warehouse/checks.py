"""Contrôles de cohérence d'un résultat de requête (outil check_result)."""

# (mode, motif, minimum, maximum, explication)
# mode "fin" : le nom de colonne se termine par le motif (mean_tmax_c, observation_year).
# mode "contient" : le motif apparaît dans le nom (mean_heat_days_per_station).
# La première règle qui correspond s'applique : l'ordre compte.
# Une colonne qu'aucune règle ne reconnaît n'est pas contrôlée (pas de faux positif).
RULES = [
    ("contient", "anomaly", -10, 10, "une anomalie annuelle dépasse rarement ±5 °C"),
    ("fin", "_c", -40, 50, "température en °C hors des bornes physiques en Occitanie"),
    ("contient", "precip", 0, 5000, "précipitations en mm hors des bornes plausibles"),
    ("fin", "month", 1, 12, "un mois est compris entre 1 et 12"),
    ("fin", "year", 1950, 2026, "l'entrepôt couvre 1950-2026"),
    ("contient", "days", 0, 366, "un nombre de jours par an est compris entre 0 et 366"),
]


def _is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _matches(column: str, mode: str, pattern: str) -> bool:
    if mode == "fin":
        return column.endswith(pattern)
    return pattern in column


def check_result(columns: list[str], rows: list[list]) -> list[str]:
    """Renvoie la liste des anomalies détectées (vide si tout semble cohérent)."""
    if not rows:
        return [
            "Résultat vide : vérifie les filtres (orthographe d'un nom, année hors période, "
            "valeur de texte exacte)."
        ]

    warnings = []
    for index, column in enumerate(columns):
        values = [row[index] for row in rows if index < len(row)]

        if any(value is None for value in values):
            warnings.append(f"Colonne {column} : contient des valeurs NULL.")

        numbers = [value for value in values if _is_number(value)]
        if not numbers:
            continue
        for mode, pattern, low, high, explanation in RULES:
            if _matches(column.lower(), mode, pattern):
                if min(numbers) < low or max(numbers) > high:
                    warnings.append(
                        f"Colonne {column} : valeurs entre {min(numbers)} et {max(numbers)}, "
                        f"attendu entre {low} et {high} ({explanation})."
                    )
                break  # une seule règle par colonne

    return warnings
