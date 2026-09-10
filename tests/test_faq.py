from database.db import get_faq_entries, get_faq_entries_by_intent, search_faq_entries
from database.seed import FAQ_ENTRIES, seed_faq_entries


REQUIRED_INTENTS = {
    "greeting", "order_status", "shipping", "delivery", "cancellation", "returns",
    "refunds", "payment", "account", "product_availability", "policies",
    "support_contact", "thanks", "goodbye", "complaint", "unknown",
}


def test_seed_populates_complete_non_empty_faq_knowledge_base(tmp_path):
    database_path = tmp_path / "faq-test.db"
    count = seed_faq_entries(database_path)
    entries = get_faq_entries(database_path, active_only=False)

    assert count == len(FAQ_ENTRIES)
    assert len(entries) == len(FAQ_ENTRIES)
    assert REQUIRED_INTENTS.issubset({entry["intent"] for entry in entries})
    assert all(entry["question"].strip() and entry["answer"].strip() for entry in entries)
    assert all(entry["seed_key"] for entry in entries)


def test_seeding_is_idempotent_and_retrieval_works(tmp_path):
    database_path = tmp_path / "faq-test.db"
    first_count = seed_faq_entries(database_path)
    second_count = seed_faq_entries(database_path)

    returns_entries = get_faq_entries_by_intent("returns", database_path)
    search_results = search_faq_entries("password", database_path)

    assert first_count == second_count == len(FAQ_ENTRIES)
    assert len(returns_entries) >= 3
    assert all(entry["intent"] == "returns" for entry in returns_entries)
    assert search_results
    assert any(entry["intent"] == "account" for entry in search_results)


def test_search_uses_values_as_data_not_sql_syntax(tmp_path):
    database_path = tmp_path / "faq-test.db"
    seed_faq_entries(database_path)

    assert search_faq_entries("' OR 1=1 --", database_path) == []
