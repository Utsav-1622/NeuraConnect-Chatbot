"""Small SQLite utility layer used by the Flask application."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from config import DATABASE_PATH


SCHEMA_PATH = Path(__file__).resolve().with_name("schema.sql")


def get_connection(database_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with foreign-key enforcement enabled."""
    path = Path(database_path) if database_path is not None else DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection(database_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Provide a transaction-aware SQLite connection and close it reliably."""
    conn = get_connection(database_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(database_path: str | Path | None = None) -> None:
    """Create or non-destructively upgrade the database schema."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with connection(database_path) as conn:
        conn.executescript(schema)
        _migrate_existing_schema(conn)


def _column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}


def _migrate_existing_schema(conn: sqlite3.Connection) -> None:
    """Add Phase 2 fields to databases created by the Phase 1 schema."""
    conversation_columns = _column_names(conn, "conversations")
    if "session_id" not in conversation_columns:
        conn.execute("ALTER TABLE conversations ADD COLUMN session_id TEXT")
        conn.execute("UPDATE conversations SET session_id = 'legacy-' || id WHERE session_id IS NULL")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_session_id_unique "
        "ON conversations(session_id) WHERE session_id IS NOT NULL"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)")

    faq_columns = _column_names(conn, "faq_entries")
    if "intent" not in faq_columns:
        conn.execute("ALTER TABLE faq_entries ADD COLUMN intent TEXT")
        conn.execute("UPDATE faq_entries SET intent = category WHERE intent IS NULL")
    if "seed_key" not in faq_columns:
        conn.execute("ALTER TABLE faq_entries ADD COLUMN seed_key TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_faq_entries_seed_key_unique "
        "ON faq_entries(seed_key) WHERE seed_key IS NOT NULL"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_faq_entries_intent ON faq_entries(intent)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_faq_entries_active_intent ON faq_entries(is_active, intent)")


def create_conversation(
    session_id: str | None = None, database_path: str | Path | None = None
) -> sqlite3.Row:
    """Create and return a conversation, assigning a session ID if omitted."""
    resolved_session_id = session_id or str(uuid4())
    with connection(database_path) as conn:
        cursor = conn.execute(
            "INSERT INTO conversations (session_id) VALUES (?)", (resolved_session_id,)
        )
        return conn.execute("SELECT * FROM conversations WHERE id = ?", (cursor.lastrowid,)).fetchone()


def get_conversation(
    conversation_id: int, database_path: str | Path | None = None
) -> sqlite3.Row | None:
    """Return one conversation or ``None`` when its ID does not exist."""
    with connection(database_path) as conn:
        return conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()


def touch_conversation(conversation_id: int, database_path: str | Path | None = None) -> None:
    """Refresh a conversation's update timestamp."""
    with connection(database_path) as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,)
        )


def insert_message(
    conversation_id: int,
    role: str,
    content: str,
    *,
    intent: str | None = None,
    intent_confidence: float | None = None,
    sentiment: str | None = None,
    sentiment_confidence: float | None = None,
    selected_faq_id: int | None = None,
    response_confidence: float | None = None,
    database_path: str | Path | None = None,
) -> sqlite3.Row:
    """Persist a message and its optional NLP metadata."""
    values = (conversation_id, role, content, intent, intent_confidence, sentiment,
              sentiment_confidence, selected_faq_id, response_confidence)
    with connection(database_path) as conn:
        cursor = conn.execute(
            """INSERT INTO messages (
                conversation_id, role, content, intent, intent_confidence, sentiment,
                sentiment_confidence, selected_faq_id, response_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
        conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,)
        )
        return conn.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()


def update_message_metadata(
    message_id: int,
    *,
    intent: str | None,
    intent_confidence: float | None,
    sentiment: str | None,
    sentiment_confidence: float | None,
    selected_faq_id: int | None,
    response_confidence: float | None,
    database_path: str | Path | None = None,
) -> None:
    """Attach actual analysis metadata after a previously persisted user message is processed."""
    with connection(database_path) as conn:
        conn.execute(
            """UPDATE messages SET intent = ?, intent_confidence = ?, sentiment = ?,
            sentiment_confidence = ?, selected_faq_id = ?, response_confidence = ? WHERE id = ?""",
            (intent, intent_confidence, sentiment, sentiment_confidence, selected_faq_id,
             response_confidence, message_id),
        )


def get_messages(conversation_id: int, database_path: str | Path | None = None) -> list[sqlite3.Row]:
    """Return a conversation's messages in insertion order."""
    with connection(database_path) as conn:
        return conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)
        ).fetchall()


def get_recent_messages(
    conversation_id: int, limit: int = 6, database_path: str | Path | None = None
) -> list[sqlite3.Row]:
    """Return at most ``limit`` recent messages in chronological order."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    with connection(database_path) as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
    return list(reversed(rows))


def insert_faq_entry(
    *, intent: str, question: str, answer: str, keywords: str, seed_key: str | None = None,
    category: str | None = None, is_active: bool = True,
    database_path: str | Path | None = None,
) -> sqlite3.Row:
    """Insert an FAQ entry safely; an existing seed key is left unchanged."""
    with connection(database_path) as conn:
        conn.execute(
            """INSERT OR IGNORE INTO faq_entries (intent, category, question, answer, keywords, seed_key, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (intent, category or intent, question, answer, keywords, seed_key, int(is_active)),
        )
        if seed_key is not None:
            return conn.execute("SELECT * FROM faq_entries WHERE seed_key = ?", (seed_key,)).fetchone()
        return conn.execute("SELECT * FROM faq_entries WHERE id = last_insert_rowid()").fetchone()


def get_faq_entries(database_path: str | Path | None = None, active_only: bool = True) -> list[sqlite3.Row]:
    """Return FAQ entries, optionally limited to enabled content."""
    query = "SELECT * FROM faq_entries"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY intent, id"
    with connection(database_path) as conn:
        return conn.execute(query).fetchall()


def get_faq_entries_by_intent(
    intent: str, database_path: str | Path | None = None
) -> list[sqlite3.Row]:
    """Return active FAQ entries for a single intent."""
    with connection(database_path) as conn:
        return conn.execute(
            "SELECT * FROM faq_entries WHERE intent = ? AND is_active = 1 ORDER BY id", (intent,)
        ).fetchall()


def search_faq_entries(
    search_term: str, database_path: str | Path | None = None
) -> list[sqlite3.Row]:
    """Search active FAQs using parameterized text matching."""
    pattern = f"%{search_term}%"
    with connection(database_path) as conn:
        return conn.execute(
            """SELECT * FROM faq_entries
            WHERE is_active = 1 AND (question LIKE ? OR answer LIKE ? OR keywords LIKE ?)
            ORDER BY intent, id""",
            (pattern, pattern, pattern),
        ).fetchall()


def get_dashboard_stats(database_path: str | Path | None = None) -> dict:
    """Aggregate real chatbot usage metrics from persisted SQLite interactions."""
    with connection(database_path) as conn:
        total_conversations = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        role_counts = {
            row["role"]: row["count"]
            for row in conn.execute("SELECT role, COUNT(*) AS count FROM messages GROUP BY role")
        }
        intent_distribution = {
            row["intent"]: row["count"]
            for row in conn.execute(
                "SELECT intent, COUNT(*) AS count FROM messages "
                "WHERE role = 'assistant' AND intent IS NOT NULL GROUP BY intent ORDER BY count DESC, intent"
            )
        }
        sentiment_distribution = {
            row["sentiment"]: row["count"]
            for row in conn.execute(
                "SELECT sentiment, COUNT(*) AS count FROM messages "
                "WHERE role = 'assistant' AND sentiment IS NOT NULL "
                "GROUP BY sentiment ORDER BY count DESC, sentiment"
            )
        }
        confidence = conn.execute(
            """SELECT AVG(response_confidence) AS response, AVG(intent_confidence) AS intent
            FROM messages WHERE role = 'assistant'"""
        ).fetchone()
        faq_usage = [
            {
                "faq_id": row["faq_id"], "question": row["question"],
                "intent": row["intent"], "count": row["count"],
            }
            for row in conn.execute(
                """SELECT f.id AS faq_id, f.question, f.intent, COUNT(*) AS count
                FROM messages AS m JOIN faq_entries AS f ON f.id = m.selected_faq_id
                WHERE m.role = 'assistant' GROUP BY f.id, f.question, f.intent
                ORDER BY count DESC, f.id LIMIT 5"""
            )
        ]
    user_count = role_counts.get("user", 0)
    assistant_count = role_counts.get("assistant", 0)
    return {
        "total_conversations": total_conversations,
        "total_user_messages": user_count,
        "total_assistant_messages": assistant_count,
        "total_messages": sum(role_counts.values()),
        "intent_distribution": intent_distribution,
        "sentiment_distribution": sentiment_distribution,
        "average_response_confidence": confidence["response"],
        "average_intent_confidence": confidence["intent"],
        "faq_usage": faq_usage,
    }


def get_recent_conversations(
    database_path: str | Path | None = None, limit: int = 10
) -> list[dict]:
    """Return compact recent conversation summaries for the local dashboard."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    with connection(database_path) as conn:
        rows = conn.execute(
            """SELECT c.id AS conversation_id, c.created_at, c.updated_at, COUNT(m.id) AS message_count,
                (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) AS latest_message,
                (SELECT intent FROM messages WHERE conversation_id = c.id AND intent IS NOT NULL ORDER BY id DESC LIMIT 1) AS latest_intent,
                (SELECT sentiment FROM messages WHERE conversation_id = c.id AND sentiment IS NOT NULL ORDER BY id DESC LIMIT 1) AS latest_sentiment,
                (SELECT response_confidence FROM messages WHERE conversation_id = c.id AND response_confidence IS NOT NULL ORDER BY id DESC LIMIT 1) AS latest_response_confidence
            FROM conversations AS c LEFT JOIN messages AS m ON m.conversation_id = c.id
            GROUP BY c.id ORDER BY c.updated_at DESC, c.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
