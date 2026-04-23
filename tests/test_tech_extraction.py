import pytest
from src.scraper import _extract_technologies


def test_extracts_single_tech():
    assert "Python" in _extract_technologies("Vaga para desenvolvedor Python")


def test_extracts_multiple_techs():
    techs = _extract_technologies("Precisa saber React, Node.js e PostgreSQL")
    assert "React" in techs
    assert "Node.js" in techs
    assert "PostgreSQL" in techs


def test_canonical_casing():
    techs = _extract_technologies("experiência com PYTHON e typescript")
    assert "Python" in techs
    assert "TypeScript" in techs


def test_no_partial_match_js_inside_nodejs():
    techs = _extract_technologies("Trabalha com Node.js no dia a dia")
    assert "Node.js" in techs
    # "JS" standalone should not appear as a separate match here
    assert techs.count("Node.js") == 1


def test_empty_string_returns_empty():
    assert _extract_technologies("") == []


def test_no_false_positives():
    techs = _extract_technologies("Vaga para motorista de caminhão")
    assert techs == []


def test_deduplicates():
    techs = _extract_technologies("Python Python Python")
    assert techs.count("Python") == 1


def test_framework_and_language_both_extracted():
    techs = _extract_technologies("Django e Python são obrigatórios")
    assert "Django" in techs
    assert "Python" in techs
