from chatbot.context import (
    DEFAULT_CONTEXT_WINDOW,
    get_conversation_context,
    is_follow_up,
    resolve_contextual_query,
    retrieve_contextual_faq,
    select_contextual_response,
)
from chatbot.faq import retrieve_best_faq
from database.db import create_conversation, init_db, insert_message
from database.seed import seed_faq_entries


def _record_exchange(database_path, conversation_id, query):
    retrieval = retrieve_best_faq(query, database_path)
    assert retrieval.selected is not None
    insert_message(
        conversation_id, "user", query, intent=retrieval.intent,
        selected_faq_id=retrieval.selected.faq_id, database_path=database_path,
    )
    insert_message(
        conversation_id, "assistant", retrieval.selected.answer, intent=retrieval.intent,
        selected_faq_id=retrieval.selected.faq_id, database_path=database_path,
    )
    return retrieval


def test_empty_context_and_standalone_query(tmp_path):
    database_path = tmp_path / "context.db"
    seed_faq_entries(database_path)
    conversation = create_conversation("empty-context", database_path)

    context = get_conversation_context(conversation["id"], database_path)
    assert context.messages == ()
    assert context.previous_intent is None
    assert not is_follow_up("What about electronics?", context)
    assert resolve_contextual_query("Can I cancel my order?", context) == "Can I cancel my order?"


def test_returns_electronics_follow_up_uses_persisted_intent(tmp_path):
    database_path = tmp_path / "context.db"
    seed_faq_entries(database_path)
    conversation = create_conversation("returns-context", database_path)
    _record_exchange(database_path, conversation["id"], "What is your return policy?")

    context = get_conversation_context(conversation["id"], database_path)
    result = retrieve_contextual_faq("What about electronics?", conversation["id"], database_path)

    assert context.previous_intent == "returns"
    assert is_follow_up("What about electronics?", context)
    assert result.used_context
    assert result.resolved_query == "returns What about electronics?"
    assert result.retrieval.intent == "returns"
    assert not is_follow_up("Can I cancel my order?", context)
    assert resolve_contextual_query("Can I cancel my order?", context) == "Can I cancel my order?"


def test_order_and_refund_follow_ups_retain_their_own_topics(tmp_path):
    database_path = tmp_path / "context.db"
    seed_faq_entries(database_path)
    order_conversation = create_conversation("order-context", database_path)
    refund_conversation = create_conversation("refund-context", database_path)
    _record_exchange(database_path, order_conversation["id"], "Where is my order?")
    _record_exchange(database_path, refund_conversation["id"], "How long does a refund take?")

    order_result = retrieve_contextual_faq("How long will it take?", order_conversation["id"], database_path)
    refund_result = retrieve_contextual_faq("How long does that take?", refund_conversation["id"], database_path)

    assert order_result.used_context and order_result.retrieval.intent == "order_status"
    assert refund_result.used_context and refund_result.retrieval.intent == "refunds"


def test_payment_follow_up_and_conversation_isolation(tmp_path):
    database_path = tmp_path / "context.db"
    seed_faq_entries(database_path)
    payment_conversation = create_conversation("payment-context", database_path)
    returns_conversation = create_conversation("isolated-returns", database_path)
    _record_exchange(database_path, payment_conversation["id"], "Do you accept credit cards?")
    _record_exchange(database_path, returns_conversation["id"], "What is your return policy?")

    payment_result = retrieve_contextual_faq("What about PayPal?", payment_conversation["id"], database_path)
    returns_result = retrieve_contextual_faq("What about electronics?", returns_conversation["id"], database_path)

    assert payment_result.retrieval.intent == "payment"
    assert returns_result.retrieval.intent == "returns"
    assert payment_result.context.previous_intent == "payment"
    assert returns_result.context.previous_intent == "returns"


def test_recent_message_limit_and_standalone_topic_preservation(tmp_path):
    database_path = tmp_path / "context.db"
    init_db(database_path)
    conversation = create_conversation("window-context", database_path)
    for number in range(DEFAULT_CONTEXT_WINDOW + 3):
        insert_message(conversation["id"], "user", f"message {number}", database_path=database_path)

    context = get_conversation_context(conversation["id"], database_path, limit=4)
    previous_context = get_conversation_context(conversation["id"], database_path)
    assert len(context.messages) == 4
    assert context.messages[0].content == "message 5"
    assert not is_follow_up("Can I cancel my order?", previous_context)
    assert resolve_contextual_query("Can I cancel my order?", previous_context) == "Can I cancel my order?"


def test_context_to_retrieval_to_controlled_response_integration(tmp_path):
    database_path = tmp_path / "context.db"
    seed_faq_entries(database_path)
    conversation = create_conversation("response-context", database_path)
    _record_exchange(database_path, conversation["id"], "What is your return policy?")

    response = select_contextual_response("What about electronics?", conversation["id"], database_path)

    assert response.source == "faq"
    assert response.retrieval.intent == "returns"
    assert response.retrieval.selected is not None
    assert response.retrieval.selected.answer == response.text
    assert response.sentiment is not None
