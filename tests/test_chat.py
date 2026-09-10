import pytest

from app import create_app
from database.db import get_messages


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": tmp_path / "chat-api.db"})
    return app.test_client(), app.config["DATABASE_PATH"]


def test_root_and_valid_chat_persist_complete_interaction(client):
    test_client, database_path = client
    assert test_client.get("/").status_code == 200

    response = test_client.post("/chat", json={"message": "What is your return policy?"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["conversation_id"]
    assert payload["intent"] == "returns"
    assert payload["selected_faq"] is not None
    assert payload["sentiment"] in {"POSITIVE", "NEGATIVE"}
    assert 0.0 <= payload["response_confidence"] <= 1.0
    messages = get_messages(payload["conversation_id"], database_path)
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert all(message["intent"] == "returns" for message in messages)
    assert all(message["selected_faq_id"] == payload["selected_faq"]["id"] for message in messages)
    assert all(message["sentiment"] == payload["sentiment"] for message in messages)


@pytest.mark.parametrize("payload", [None, {}, {"message": None}, {"message": ""}, {"message": "   "}])
def test_chat_rejects_missing_or_empty_message(client, payload):
    test_client, _ = client
    response = test_client.post("/chat", json=payload)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_malformed_and_invalid_conversation_requests_are_clean(client):
    test_client, _ = client
    malformed = test_client.post("/chat", data="{", content_type="application/json")
    invalid = test_client.post("/chat", json={"message": "Hello", "conversation_id": "bad"})
    missing = test_client.post("/chat", json={"message": "Hello", "conversation_id": 99999})

    assert malformed.status_code == invalid.status_code == 400
    assert missing.status_code == 404
    assert all("error" in response.get_json() for response in (malformed, invalid, missing))


def test_existing_conversation_context_and_isolation_through_http(client):
    test_client, _ = client
    first = test_client.post("/chat", json={"message": "What is your return policy?"}).get_json()
    follow_up = test_client.post("/chat", json={
        "message": "What about electronics?", "conversation_id": first["conversation_id"],
    }).get_json()
    other = test_client.post("/chat", json={"message": "Where is my order?"}).get_json()
    other_follow_up = test_client.post("/chat", json={
        "message": "How long will it take?", "conversation_id": other["conversation_id"],
    }).get_json()

    assert follow_up["conversation_id"] == first["conversation_id"]
    assert follow_up["context_used"] is True
    assert follow_up["intent"] == "returns"
    assert other["conversation_id"] != first["conversation_id"]
    assert other_follow_up["context_used"] is True
    assert other_follow_up["intent"] == "order_status"


def test_unknown_complaint_and_reset_behavior(client):
    test_client, _ = client
    unknown = test_client.post("/chat", json={"message": "How do I bake bread?"}).get_json()
    complaint = test_client.post("/chat", json={
        "message": "My item arrived damaged and I am very frustrated."
    }).get_json()
    original = test_client.post("/chat", json={"message": "What is your return policy?"}).get_json()
    reset = test_client.post("/reset", json={"conversation_id": original["conversation_id"]})
    reset_payload = reset.get_json()
    after_reset = test_client.post("/chat", json={
        "message": "What about electronics?", "conversation_id": reset_payload["conversation_id"],
    }).get_json()

    assert unknown["is_fallback"] is True
    assert unknown["intent"] is None
    assert complaint["intent"] == "complaint"
    assert complaint["sentiment"] == "NEGATIVE"
    assert reset.status_code == 200 and reset_payload["reset"] is True
    assert reset_payload["conversation_id"] != original["conversation_id"]
    assert after_reset["context_used"] is False


def test_reset_validates_known_conversation(client):
    test_client, _ = client
    assert test_client.post("/reset", json={"conversation_id": "invalid"}).status_code == 400
    assert test_client.post("/reset", json={"conversation_id": 99999}).status_code == 404
