"""Small SQLite-backed conversation context for obvious customer-support follow-ups."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chatbot.faq import FAQRetrievalResult, retrieve_best_faq
from chatbot.preprocessing import preprocess_text
from chatbot.response import ResponseResult, select_response_from_retrieval
from database.db import get_recent_messages


DEFAULT_CONTEXT_WINDOW = 6
_FOLLOW_UP_PHRASES = ("what about", "how about", "what happens then")
_FOLLOW_UP_STARTS = ("and ", "also ", "that", "this", "it ", "they", "those", "how long")
_STANDALONE_TOPIC_STEMS = frozenset(
    preprocess_text(
        "return refund cancel shipping delivery payment card account password order product stock support complaint policy"
    ).stemmed_tokens
)


@dataclass(frozen=True)
class ContextMessage:
    """The useful, compact portion of a persisted message for context resolution."""

    message_id: int
    role: str
    content: str
    intent: str | None
    selected_faq_id: int | None


@dataclass(frozen=True)
class ConversationContext:
    """Recent context derived only from one SQLite conversation."""

    conversation_id: int
    messages: tuple[ContextMessage, ...]
    previous_user_message: str | None
    previous_assistant_message: str | None
    previous_intent: str | None
    previous_selected_faq_id: int | None


@dataclass(frozen=True)
class ContextualRetrievalResult:
    """Original and resolved query forms alongside the standard FAQ result."""

    original_query: str | None
    resolved_query: str | None
    used_context: bool
    context: ConversationContext
    retrieval: FAQRetrievalResult


def get_conversation_context(
    conversation_id: int,
    database_path: str | Path | None = None,
    limit: int = DEFAULT_CONTEXT_WINDOW,
) -> ConversationContext:
    """Load a deliberately small, chronological context window for one conversation."""
    rows = get_recent_messages(conversation_id, limit, database_path)
    messages = tuple(
        ContextMessage(
            message_id=row["id"], role=row["role"], content=row["content"],
            intent=row["intent"], selected_faq_id=row["selected_faq_id"],
        )
        for row in rows
    )
    previous_user = next((message.content for message in reversed(messages) if message.role == "user"), None)
    previous_assistant = next(
        (message.content for message in reversed(messages) if message.role == "assistant"), None
    )
    previous_with_intent = next(
        (message for message in reversed(messages) if message.intent), None
    )
    return ConversationContext(
        conversation_id=conversation_id,
        messages=messages,
        previous_user_message=previous_user,
        previous_assistant_message=previous_assistant,
        previous_intent=previous_with_intent.intent if previous_with_intent else None,
        previous_selected_faq_id=(
            previous_with_intent.selected_faq_id if previous_with_intent else None
        ),
    )


def is_follow_up(query: str | None, context: ConversationContext) -> bool:
    """Identify short referential follow-ups only when a previous intent exists."""
    if not context.previous_intent:
        return False
    normalized = preprocess_text(query).normalized_text
    if not normalized:
        return False
    stems = set(preprocess_text(normalized).stemmed_tokens)
    has_explicit_topic = bool(stems & _STANDALONE_TOPIC_STEMS)
    has_follow_up_cue = normalized.startswith(_FOLLOW_UP_STARTS) or any(
        phrase in normalized for phrase in _FOLLOW_UP_PHRASES
    )
    return has_follow_up_cue and not has_explicit_topic


def resolve_contextual_query(query: str | None, context: ConversationContext) -> str | None:
    """Add the previous FAQ intent to obvious follow-ups for existing retrieval."""
    if query is None:
        return None
    if is_follow_up(query, context):
        return f"{context.previous_intent.replace('_', ' ')} {query.strip()}"
    return query


def retrieve_contextual_faq(
    query: str | None, conversation_id: int, database_path: str | Path | None = None
) -> ContextualRetrievalResult:
    """Resolve a query from one conversation then reuse the standard FAQ retriever."""
    context = get_conversation_context(conversation_id, database_path)
    resolved_query = resolve_contextual_query(query, context)
    return ContextualRetrievalResult(
        original_query=query,
        resolved_query=resolved_query,
        used_context=resolved_query != query,
        context=context,
        retrieval=retrieve_best_faq(resolved_query, database_path),
    )


def select_contextual_response(
    query: str | None, conversation_id: int, database_path: str | Path | None = None
) -> ResponseResult:
    """Use contextual FAQ retrieval while retaining the user's natural text for sentiment."""
    contextual = retrieve_contextual_faq(query, conversation_id, database_path)
    return select_response_from_retrieval(query, contextual.retrieval)
