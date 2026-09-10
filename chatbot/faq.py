"""Deterministic retrieval over the controlled SQLite FAQ knowledge base."""

from __future__ import annotations

from dataclasses import dataclass
from math import log
from pathlib import Path

from chatbot.preprocessing import PreprocessingResult, preprocess_text
from database.db import get_faq_entries


# A compact lexical bridge for common wording variants.  It expands queries,
# never chooses an answer: all intents and answers still come from SQLite FAQs.
_PHRASE_EXPANSIONS = {
    "send back": "return",
    "send something back": "return policy eligible",
    "give back": "return",
    "has not arrived": "delivery late",
    "haven't arrived": "delivery late",
    "did not arrive": "delivery late",
    "forgot password": "reset password",
    "credit card": "payment card",
    "return": "return policy eligible",
    "available": "stock",
}
_RETRIEVAL_GENERIC_STEMS = frozenset(
    preprocess_text("item something thing want need help please tell").stemmed_tokens
)
MIN_RELEVANCE_SCORE = 0.25


@dataclass(frozen=True)
class FAQCandidate:
    """A database FAQ record together with transparent retrieval evidence."""

    faq_id: int
    intent: str
    question: str
    answer: str
    relevance_score: float
    matched_stems: tuple[str, ...]


@dataclass(frozen=True)
class FAQRetrievalResult:
    """Ranked FAQ results; confidence is an uncalibrated retrieval-evidence score."""

    input_text: str | None
    normalized_text: str
    selected: FAQCandidate | None
    intent: str | None
    candidates: tuple[FAQCandidate, ...]
    relevance_score: float
    retrieval_confidence: float
    is_fallback: bool


def _expanded_preprocessing(text: str | None) -> PreprocessingResult:
    normalized = preprocess_text(text).normalized_text
    for phrase, expansion in _PHRASE_EXPANSIONS.items():
        if phrase in normalized:
            normalized = f"{normalized} {expansion}"
    return preprocess_text(normalized)


def _weighted_coverage(
    query_stems: set[str], source_stems: set[str], term_weights: dict[str, float]
) -> float:
    total_weight = sum(term_weights[term] for term in query_stems)
    if not total_weight:
        return 0.0
    return sum(term_weights[term] for term in query_stems & source_stems) / total_weight


def _score_candidate(
    query: PreprocessingResult, row, term_weights: dict[str, float]
) -> FAQCandidate:
    """Score evidence from query-stem coverage in FAQ question, keywords, and answer.

    Keyword matches are weighted most strongly, then question matches, then answer
    matches. Corpus inverse-frequency weighting downweights generic terms such as
    "item". The result is deterministic, bounded, and not calibrated.
    """
    query_stems = set(query.stemmed_tokens) - _RETRIEVAL_GENERIC_STEMS
    question_stems = set(preprocess_text(row["question"]).stemmed_tokens)
    keyword_stems = set(preprocess_text(row["keywords"] or "").stemmed_tokens)
    answer_stems = set(preprocess_text(row["answer"]).stemmed_tokens)
    if not query_stems:
        score = 0.0
        matches: set[str] = set()
    else:
        question_matches = query_stems & question_stems
        keyword_matches = query_stems & keyword_stems
        answer_matches = query_stems & answer_stems
        score = (
            0.35 * _weighted_coverage(query_stems, question_stems, term_weights)
            + 0.45 * _weighted_coverage(query_stems, keyword_stems, term_weights)
            + 0.15 * _weighted_coverage(query_stems, answer_stems, term_weights)
        )
        if query.normalized_text == row["question"].lower():
            score += 0.10
        matches = question_matches | keyword_matches | answer_matches
    return FAQCandidate(
        faq_id=row["id"],
        intent=row["intent"],
        question=row["question"],
        answer=row["answer"],
        relevance_score=min(1.0, score),
        matched_stems=tuple(sorted(matches)),
    )


def retrieve_faqs(
    query: str | None, database_path: str | Path | None = None
) -> FAQRetrievalResult:
    """Rank actual active FAQ records for a query using transparent lexical evidence."""
    query_representation = _expanded_preprocessing(query)
    rows = get_faq_entries(database_path)
    document_stem_sets = [
        set(preprocess_text(f"{row['question']} {row['keywords'] or ''} {row['answer']}").stemmed_tokens)
        for row in rows
    ]
    document_count = len(document_stem_sets)
    query_stems = set(query_representation.stemmed_tokens) - _RETRIEVAL_GENERIC_STEMS
    term_weights = {
        stem: log((document_count + 1) / (1 + sum(stem in document for document in document_stem_sets))) + 1
        for stem in query_stems
    }
    candidates = sorted(
        (_score_candidate(query_representation, row, term_weights) for row in rows),
        key=lambda candidate: (-candidate.relevance_score, candidate.faq_id),
    )
    ranked = tuple(candidates)
    top = ranked[0] if ranked else None
    accepted = top if top is not None and top.relevance_score >= MIN_RELEVANCE_SCORE else None
    margin = (top.relevance_score - ranked[1].relevance_score) if len(ranked) > 1 and top else 0.0
    # This 0..1 score expresses strength and separation of retrieval evidence;
    # it is intentionally not presented as a statistically calibrated probability.
    confidence = min(1.0, top.relevance_score * 0.85 + max(0.0, margin) * 0.15) if accepted else 0.0
    return FAQRetrievalResult(
        input_text=query,
        normalized_text=query_representation.normalized_text,
        selected=accepted,
        intent=accepted.intent if accepted else None,
        candidates=ranked,
        relevance_score=top.relevance_score if top else 0.0,
        retrieval_confidence=confidence,
        is_fallback=accepted is None,
    )


def retrieve_best_faq(
    query: str | None, database_path: str | Path | None = None
) -> FAQRetrievalResult:
    """Convenience name for the standard controlled FAQ retrieval operation."""
    return retrieve_faqs(query, database_path)
