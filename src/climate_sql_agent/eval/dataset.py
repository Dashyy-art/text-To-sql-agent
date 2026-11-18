"""Format du jeu d'évaluation (eval/questions.yaml) et chargement."""

from enum import StrEnum
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, model_validator


class Category(StrEnum):
    SIMPLE = "simple"
    AGGREGATION = "aggregation"
    TEMPORAL = "temporal"
    MULTI_TABLE = "multi_table"
    TRAP = "trap"


class Behavior(StrEnum):
    ANSWER = "answer"  # répondre avec des données
    REFUSE = "refuse"  # refuser : hors périmètre ou tentative d'écriture
    CLARIFY = "clarify"  # demander une précision : question ambiguë
    NO_DATA = "no_data"  # dire que la donnée n'existe pas


class Split(StrEnum):
    DEV = "dev"
    TEST = "test"


class EvalQuestion(BaseModel):
    id: str
    split: Split
    category: Category
    question: str
    expected_behavior: Behavior = Behavior.ANSWER
    reference_sql: str | None = None
    order_matters: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def check_sql_matches_behavior(self) -> Self:
        """Une question 'answer' a un SQL de référence ; un piège n'en a pas."""
        has_sql = bool(self.reference_sql)
        if self.expected_behavior == Behavior.ANSWER and not has_sql:
            raise ValueError(f"{self.id} : une question 'answer' doit avoir un reference_sql")
        if self.expected_behavior != Behavior.ANSWER and has_sql:
            raise ValueError(f"{self.id} : un piège ne doit pas avoir de reference_sql")
        return self


def load_questions(path: Path) -> list[EvalQuestion]:
    """Lit le fichier YAML et vérifie chaque question."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    questions = [EvalQuestion.model_validate(item) for item in data]

    ids = [q.id for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Identifiants en double dans le jeu d'évaluation")

    return questions
