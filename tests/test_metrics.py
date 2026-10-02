import pytest
from src.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    is_item_relevant,
)


def test_is_item_relevant():
    spec = {"target_types": ["Dress"], "color": "Red", "gender": "Women"}
    item_match = {"articleType": "Dress", "baseColour": "Red", "gender": "Women"}
    item_wrong_color = {"articleType": "Dress", "baseColour": "Blue", "gender": "Women"}
    item_wrong_type = {"articleType": "Shirts", "baseColour": "Red", "gender": "Women"}

    assert is_item_relevant(item_match, spec) is True
    assert is_item_relevant(item_wrong_color, spec) is False
    assert is_item_relevant(item_wrong_type, spec) is False


def test_precision_at_k():
    spec = {"target_types": ["Jeans"], "color": "Blue"}
    items = [
        {"articleType": "Jeans", "baseColour": "Blue"},
        {"articleType": "Jeans", "baseColour": "Blue"},
        {"articleType": "Jeans", "baseColour": "Black"},
        {"articleType": "Shirts", "baseColour": "Blue"},
    ]
    # In top 2: 2/2 = 1.0
    assert precision_at_k(items, spec, k=2) == 1.0
    # In top 4: 2/4 = 0.5
    assert precision_at_k(items, spec, k=4) == 0.5


def test_recall_at_k():
    spec = {"target_types": ["Jeans"], "color": "Blue"}
    items = [
        {"articleType": "Jeans", "baseColour": "Blue"},
        {"articleType": "Shirts", "baseColour": "Blue"},
        {"articleType": "Jeans", "baseColour": "Blue"},
        {"articleType": "Jeans", "baseColour": "Black"},
    ]
    total_relevant = 4  # Total relevant items in corpus pool

    # In top 1: 1 match / 4 total = 0.25
    assert recall_at_k(items, spec, total_relevant=total_relevant, k=1) == 0.25

    # In top 3: 2 matches / 4 total = 0.50
    assert recall_at_k(items, spec, total_relevant=total_relevant, k=3) == 0.50

    # In top 4: 2 matches / 4 total = 0.50
    assert recall_at_k(items, spec, total_relevant=total_relevant, k=4) == 0.50

    # Edge cases
    assert recall_at_k(items, spec, total_relevant=0, k=3) == 0.0
    assert recall_at_k([], spec, total_relevant=5, k=3) == 0.0
