"""Focused robustness tests for the chat assistant.

Probes the pieces test_app.py only touches through the HTTP layer:
  * intent_model.classify() on held-out paraphrases (not in intents.json)
  * off-topic queries are rejected below the confidence threshold
  * chatbot.answer() routing across level-1 rules, level-2 model, and fallback

Run with: python -m pytest test_chatbot.py -v
"""
from unittest.mock import MagicMock

import pytest

import chatbot
import intent_model






HELD_OUT = {
    "low_stock": "anything we are short on",
    "item_quantity": "how many potatoes are left",
    "expiring_soon": "what is going to spoil soon",
    "cheapest_supplier": "lowest cost vendor for rice",
    "supplier_list": "show me all vendors",
    "waste_report": "how much food have we wasted",
    "sales_trend": "how well is beef selling",
    "items_by_category": "what is in the dairy category",
    "list_categories": "what categories are there",
    "count_items": "what is the total count of items",
    "list_items": "list all the stock",
    "greeting": "good day to you",
    "help": "how can you assist",
}

@pytest.mark.parametrize("intent,phrase", list(HELD_OUT.items()))
def test_classifier_handles_held_out_paraphrases(intent, phrase):
    """Novel phrasings still land on the right intent above the threshold."""
    got, score = intent_model.classify(phrase)
    assert got == intent, f"{phrase!r} -> {got} ({score:.2f}), expected {intent}"
    assert score >= intent_model.DEFAULT_THRESHOLD


OFF_TOPIC = [
    "tell me a joke",
    "what is the weather",
    "sing me a song",
    "play some music",
    "book a flight",
    "who won the game last night",
]

@pytest.mark.parametrize("phrase", OFF_TOPIC)
def test_classifier_rejects_off_topic(phrase):
    """Out-of-domain queries fall below the threshold and return None."""
    got, score = intent_model.classify(phrase)
    assert got is None, f"{phrase!r} unexpectedly matched {got} ({score:.2f})"


def test_classifier_empty_message():
    assert intent_model.classify("") == (None, 0.0)



# answer() routing: level-1 rules, level-2 model, and fallback


@pytest.fixture
def db():
    """A MagicMock db with just enough behaviour for the intent handlers."""
    mock = MagicMock()
    mock.inventory_items.find.return_value = [
        {"item_name": "Olive Oil", "item_id": 102, "quantity": 3,
         "minimum_threshold": 5, "category": "Groceries"},
        {"item_name": "Fresh Tomatoes", "item_id": 101, "quantity": 120,
         "minimum_threshold": 30, "category": "Produce"},
    ]
    mock.inventory_items.count_documents.return_value = 2
    mock.inventory_items.distinct.return_value = ["Groceries", "Produce"]
    mock.suppliers.find.return_value = [{"supplier_name": "Alpha"}]
    return mock

def test_answer_level_one_rules(db):
    """A keyword phrase is answered by the rules layer."""
    result = chatbot.answer(db, "what is running low?")
    assert result["source"] == "rules"
    assert "Olive Oil" in result["response"]

def test_answer_level_two_model(db):
    """A paraphrase the rules miss is answered by the model layer."""
    result = chatbot.answer(db, "which products are almost gone")
    assert result["source"] == "model"
    assert "Olive Oil" in result["response"]

def test_answer_fallback(db):
    """An off-topic message falls back instead of guessing."""
    result = chatbot.answer(db, "tell me a joke")
    assert result["source"] == "fallback"

def test_answer_empty_message(db):
    """An empty message falls back gracefully."""
    result = chatbot.answer(db, "")
    assert result["source"] == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
