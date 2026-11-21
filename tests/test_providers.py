"""Tests de la création du modèle (sans appel à Ollama)."""

import pytest

from climate_sql_agent.agent.providers import OllamaProvider, make_provider


def test_ollama_spec_keeps_full_model_name():
    provider = make_provider("ollama:qwen3:8b")
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "qwen3:8b"  # le ':' du nom de modèle est conservé


def test_think_option_is_passed():
    assert make_provider("ollama:qwen3:8b", think=True).think is True


def test_other_provider_is_rejected():
    with pytest.raises(ValueError, match="ollama"):
        make_provider("autre:modele")


def test_spec_without_model_is_rejected():
    with pytest.raises(ValueError, match="ollama"):
        make_provider("ollama")
