import pytest

from app import create_app
from database.db import create_conversation, insert_message


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": tmp_path / "dashboard.db"})
    return app.test_client(), app.config["DATABASE_PATH"]


def test_dashboard_and_analytics_empty_state(client):
    test_client, _ = client
    assert test_client.get("/dashboard").status_code == 200
    stats = test_client.get("/api/stats").get_json()
    conversations = test_client.get("/api/conversations").get_json()
    assert stats["total_conversations"] == stats["total_messages"] == 0
    assert stats["intent_distribution"] == stats["sentiment_distribution"] == {}
    assert stats["faq_usage"] == []
    assert conversations == {"conversations": []}


def test_dashboard_statistics_and_recent_conversations_use_real_rows(client):
    test_client, database_path = client
    first = create_conversation("dashboard-first", database_path)
    second = create_conversation("dashboard-second", database_path)
    insert_message(first["id"], "user", "Where is my order?", database_path=database_path)
    insert_message(first["id"], "assistant", "Order status answer", intent="order_status", intent_confidence=.8, sentiment="NEGATIVE", sentiment_confidence=.9, selected_faq_id=3, response_confidence=.7, database_path=database_path)
    insert_message(second["id"], "user", "Can I return this?", database_path=database_path)
    insert_message(second["id"], "assistant", "Return answer", intent="returns", intent_confidence=.6, sentiment="POSITIVE", sentiment_confidence=.8, selected_faq_id=15, response_confidence=.5, database_path=database_path)

    stats = test_client.get("/api/stats").get_json()
    recent = test_client.get("/api/conversations").get_json()["conversations"]
    assert stats["total_conversations"] == 2
    assert stats["total_user_messages"] == stats["total_assistant_messages"] == 2
    assert stats["total_messages"] == 4
    assert stats["intent_distribution"] == {"order_status": 1, "returns": 1}
    assert stats["sentiment_distribution"] == {"NEGATIVE": 1, "POSITIVE": 1}
    assert stats["average_response_confidence"] == pytest.approx(.6)
    assert stats["average_intent_confidence"] == pytest.approx(.7)
    assert {item["faq_id"] for item in stats["faq_usage"]} == {3, 15}
    assert {item["conversation_id"] for item in recent} == {first["id"], second["id"]}
    assert all(item["message_count"] == 2 for item in recent)


def test_existing_chat_still_updates_dashboard_data(client):
    test_client, _ = client
    chat = test_client.post("/chat", json={"message": "What is your return policy?"})
    stats = test_client.get("/api/stats").get_json()
    assert chat.status_code == 200
    assert stats["total_conversations"] == 1
    assert stats["total_user_messages"] == stats["total_assistant_messages"] == 1
    assert stats["intent_distribution"]["returns"] == 1
