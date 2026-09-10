import sqlite3

import pytest

from database.db import (
    connection,
    create_conversation,
    get_connection,
    get_messages,
    init_db,
    insert_message,
    touch_conversation,
)


def table_names(database_path):
    with get_connection(database_path) as conn:
        return {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }


def test_initialization_creates_database_and_required_tables(tmp_path):
    database_path = tmp_path / "nested" / "chatbot-test.db"

    init_db(database_path)

    assert database_path.exists()
    assert {"conversations", "messages", "faq_entries"}.issubset(table_names(database_path))


def test_foreign_keys_are_enabled(tmp_path):
    database_path = tmp_path / "chatbot-test.db"
    init_db(database_path)

    with get_connection(database_path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (999, 'user', 'Hello')"
            )


def test_initialization_is_idempotent_and_preserves_data(tmp_path):
    database_path = tmp_path / "chatbot-test.db"
    init_db(database_path)
    with connection(database_path) as conn:
        conn.execute("INSERT INTO conversations (session_id, status) VALUES ('preserve-test', 'active')")
        conversation_id = conn.execute("SELECT id FROM conversations").fetchone()[0]

    init_db(database_path)

    with get_connection(database_path) as conn:
        assert conn.execute("SELECT id FROM conversations").fetchone()[0] == conversation_id


def test_conversation_message_crud_and_timestamp_update(tmp_path):
    database_path = tmp_path / "chatbot-test.db"
    init_db(database_path)
    conversation = create_conversation("session-test-001", database_path)

    first = insert_message(
        conversation["id"], "user", "Where is my order?", intent="order_status",
        intent_confidence=0.95, sentiment="neutral", sentiment_confidence=0.88,
        database_path=database_path,
    )
    second = insert_message(
        conversation["id"], "assistant", "Please check your tracking details.",
        selected_faq_id=None, response_confidence=0.91, database_path=database_path,
    )
    messages = get_messages(conversation["id"], database_path)

    assert [message["id"] for message in messages] == [first["id"], second["id"]]
    assert messages[0]["intent"] == "order_status"
    assert messages[1]["role"] == "assistant"

    with connection(database_path) as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = '2000-01-01 00:00:00' WHERE id = ?",
            (conversation["id"],),
        )
    touch_conversation(conversation["id"], database_path)
    with get_connection(database_path) as conn:
        updated_at = conn.execute(
            "SELECT updated_at FROM conversations WHERE id = ?", (conversation["id"],)
        ).fetchone()["updated_at"]
    assert updated_at != "2000-01-01 00:00:00"
