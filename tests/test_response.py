from database.seed import seed_faq_entries

from chatbot.faq import MIN_RELEVANCE_SCORE, retrieve_best_faq
from chatbot.response import FALLBACK_RESPONSE, select_response


def test_retrieval_selects_actual_faq_intents_for_representative_queries(tmp_path):
    database_path = tmp_path / "faq-response.db"
    seed_faq_entries(database_path)
    expected = {
        "Hello": "greeting",
        "Where is my order?": "order_status",
        "What shipping options are available?": "shipping",
        "My package hasn't arrived yet.": "delivery",
        "Can I cancel my order?": "cancellation",
        "Can I return this product?": "returns",
        "How long does a refund take?": "refunds",
        "Do you accept credit cards?": "payment",
        "I forgot my account password.": "account",
        "Is this item available?": "product_availability",
        "How can I contact support?": "support_contact",
    }

    for query, intent in expected.items():
        result = retrieve_best_faq(query, database_path)
        assert result.selected is not None, query
        assert result.intent == intent, query
        assert result.selected.intent == intent
        assert result.relevance_score >= MIN_RELEVANCE_SCORE


def test_retrieval_handles_supported_paraphrase_deterministically(tmp_path):
    database_path = tmp_path / "faq-response.db"
    seed_faq_entries(database_path)

    first = retrieve_best_faq("Can I send something back if I don't want it?", database_path)
    second = retrieve_best_faq("Can I send something back if I don't want it?", database_path)

    assert first.intent == "returns"
    assert first == second
    assert first.candidates[0].relevance_score >= first.candidates[-1].relevance_score


def test_unknown_and_empty_queries_use_safe_fallback(tmp_path):
    database_path = tmp_path / "faq-response.db"
    seed_faq_entries(database_path)

    for query in ("What is quantum entanglement?", "How do I bake bread?", "zxqv blorf", None, "   "):
        retrieval = retrieve_best_faq(query, database_path)
        response = select_response(query, database_path)
        assert retrieval.is_fallback
        assert response.source == "fallback"
        assert response.text == FALLBACK_RESPONSE
        assert response.response_confidence == 0.0


def test_controlled_complaint_response_uses_real_sentiment_and_faq_answer(tmp_path):
    database_path = tmp_path / "faq-response.db"
    seed_faq_entries(database_path)

    response = select_response("My item arrived damaged and I am very frustrated.", database_path)

    assert response.source == "faq"
    assert response.retrieval.intent == "complaint"
    assert response.sentiment is not None
    assert response.sentiment.label == "NEGATIVE"
    assert response.retrieval.selected is not None
    assert response.retrieval.selected.answer in response.text
    assert 0.0 <= response.response_confidence <= 1.0


def test_stronger_match_has_more_retrieval_evidence_than_weak_match(tmp_path):
    database_path = tmp_path / "faq-response.db"
    seed_faq_entries(database_path)

    strong = retrieve_best_faq("Where is my order?", database_path)
    weak = retrieve_best_faq("order", database_path)

    assert strong.retrieval_confidence > weak.retrieval_confidence
