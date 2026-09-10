"""Flask bootstrap for the customer support chatbot."""

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from chatbot.context import retrieve_contextual_faq
from chatbot.response import select_response_from_retrieval
from config import Config
from database.db import (
    create_conversation,
    get_dashboard_stats,
    get_conversation,
    get_recent_conversations,
    init_db,
    insert_message,
    update_message_metadata,
)
from database.seed import seed_faq_entries


def _json_error(message: str, status_code: int):
    return jsonify({"error": message}), status_code


def _parse_conversation_id(value):
    if isinstance(value, bool):
        return None
    try:
        conversation_id = int(value)
    except (TypeError, ValueError):
        return None
    return conversation_id if conversation_id > 0 else None


def create_app(test_config: dict | None = None) -> Flask:
    """Create the basic Flask application and its SQLite-backed chat API."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    init_db(app.config["DATABASE_PATH"])
    seed_faq_entries(app.config["DATABASE_PATH"])

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/api/stats")
    def stats():
        return jsonify(get_dashboard_stats(app.config["DATABASE_PATH"]))

    @app.get("/api/conversations")
    def conversations():
        return jsonify({"conversations": get_recent_conversations(app.config["DATABASE_PATH"])})

    @app.post("/chat")
    def chat():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _json_error("Request body must be valid JSON.", 400)
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            return _json_error("'message' must be a non-empty string.", 400)

        database_path = Path(app.config["DATABASE_PATH"])
        supplied_id = payload.get("conversation_id")
        if supplied_id is None:
            conversation = create_conversation(database_path=database_path)
        else:
            conversation_id = _parse_conversation_id(supplied_id)
            if conversation_id is None:
                return _json_error("'conversation_id' must be a positive integer.", 400)
            conversation = get_conversation(conversation_id, database_path)
            if conversation is None:
                return _json_error("Conversation not found.", 404)

        user_message = insert_message(conversation["id"], "user", message, database_path=database_path)
        contextual = retrieve_contextual_faq(message, conversation["id"], database_path)
        response_result = select_response_from_retrieval(message, contextual.retrieval)
        selected = response_result.retrieval.selected
        sentiment = response_result.sentiment
        metadata = {
            "intent": response_result.retrieval.intent,
            "intent_confidence": response_result.retrieval.retrieval_confidence,
            "sentiment": sentiment.label if sentiment else None,
            "sentiment_confidence": sentiment.confidence if sentiment else None,
            "selected_faq_id": selected.faq_id if selected else None,
            "response_confidence": response_result.response_confidence,
        }
        update_message_metadata(user_message["id"], database_path=database_path, **metadata)
        insert_message(
            conversation["id"], "assistant", response_result.text, database_path=database_path,
            **metadata,
        )
        selected_faq = (
            {"id": selected.faq_id, "question": selected.question} if selected else None
        )
        return jsonify({
            "conversation_id": conversation["id"],
            "user_message": message,
            "response": response_result.text,
            "intent": response_result.retrieval.intent,
            "sentiment": sentiment.label if sentiment else None,
            "selected_faq": selected_faq,
            "response_confidence": response_result.response_confidence,
            "context_used": contextual.used_context,
            "is_fallback": response_result.source == "fallback",
        })

    @app.post("/reset")
    def reset():
        payload = request.get_json(silent=True)
        if payload is not None and not isinstance(payload, dict):
            return _json_error("Request body must be a JSON object.", 400)
        supplied_id = (payload or {}).get("conversation_id")
        database_path = Path(app.config["DATABASE_PATH"])
        if supplied_id is not None:
            conversation_id = _parse_conversation_id(supplied_id)
            if conversation_id is None:
                return _json_error("'conversation_id' must be a positive integer.", 400)
            if get_conversation(conversation_id, database_path) is None:
                return _json_error("Conversation not found.", 404)
        conversation = create_conversation(database_path=database_path)
        return jsonify({
            "conversation_id": conversation["id"],
            "reset": True,
            "message": "A new conversation has been created.",
        })

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
