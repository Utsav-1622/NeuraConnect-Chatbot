"""Controlled response selection using FAQ retrieval and real sentiment evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chatbot.faq import FAQRetrievalResult, retrieve_best_faq
from chatbot.transformers import TransformerAnalysis, analyze_text


FALLBACK_RESPONSE = (
    "I’m sorry, but I don’t have a reliable answer for that. Please rephrase your "
    "question or contact support with the relevant order or account details."
)


@dataclass(frozen=True)
class ResponseResult:
    """A controlled FAQ answer or explicit fallback, ready for later orchestration."""

    text: str
    source: str
    retrieval: FAQRetrievalResult
    response_confidence: float
    sentiment: TransformerAnalysis | None


def select_response(
    query: str | None, database_path: str | Path | None = None
) -> ResponseResult:
    """Return a traceable controlled answer; never generate policy outside the FAQ set."""
    retrieval = retrieve_best_faq(query, database_path)
    return select_response_from_retrieval(query, retrieval)


def select_response_from_retrieval(
    query: str | None, retrieval: FAQRetrievalResult
) -> ResponseResult:
    """Build a controlled response from an already-computed FAQ retrieval result."""
    if retrieval.is_fallback or retrieval.selected is None:
        return ResponseResult(
            text=FALLBACK_RESPONSE,
            source="fallback",
            retrieval=retrieval,
            response_confidence=0.0,
            sentiment=None,
        )

    sentiment = analyze_text(query)
    response_text = retrieval.selected.answer
    if retrieval.intent == "complaint" and sentiment.label == "NEGATIVE":
        response_text = f"I’m sorry this has been frustrating. {response_text}"
    return ResponseResult(
        text=response_text,
        source="faq",
        retrieval=retrieval,
        response_confidence=retrieval.retrieval_confidence,
        sentiment=sentiment,
    )
