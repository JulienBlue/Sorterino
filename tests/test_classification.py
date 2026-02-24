import pytest

from usecases.classify_document import apply_rules


def test_lohnsteuer_rule_match():
    text = "Dies ist eine Lohnsteuerbescheinigung für 2018"
    rules = [
        {
            "category": "Steuer",
            "document_type": "Lohnsteuerbescheinigung",
            "keywords": ["lohnsteuerbescheinigung"]
        }
    ]

    category, doc_type = apply_rules(text.lower(), rules)

    assert category == "Steuer"
    assert doc_type == "Lohnsteuerbescheinigung"


def test_no_match_returns_none():
    text = "Komplett irrelevanter Text"
    rules = [
        {
            "category": "Steuer",
            "document_type": "Lohnsteuerbescheinigung",
            "keywords": ["lohnsteuerbescheinigung"]
        }
    ]

    category, doc_type = apply_rules(text.lower(), rules)

    assert category is None
    assert doc_type is None