"""Lazy CPU-only Hugging Face sentiment inference for later chatbot stages."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
from time import perf_counter

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from chatbot.preprocessing import preprocess_text


LOGGER = logging.getLogger(__name__)
MODEL_ID = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"


@dataclass(frozen=True)
class ClassificationScore:
    """One label probability produced directly from the sequence classifier."""

    label: str
    score: float


@dataclass(frozen=True)
class TransformerAnalysis:
    """Immutable result from real pretrained sentiment classification."""

    input_text: str
    normalized_text: str
    model_id: str
    task: str
    label: str
    confidence: float
    ranked_labels: tuple[ClassificationScore, ...]
    device: str


class TransformerAnalyzer:
    """Own a reusable tokenizer and sequence-classification model on CPU."""

    def __init__(self, model_id: str = MODEL_ID) -> None:
        self.model_id = model_id
        self.device = torch.device("cpu")
        started_at = perf_counter()
        LOGGER.info("Loading Transformer model %s on CPU", model_id)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_id)
        except Exception as error:
            raise RuntimeError(
                f"Unable to initialize Hugging Face model '{model_id}'. "
                "Check network access or the local Hugging Face cache."
            ) from error
        self.model.to(self.device)
        self.model.eval()
        self.load_seconds = perf_counter() - started_at
        LOGGER.info("Loaded Transformer model %s in %.2fs", model_id, self.load_seconds)

    def analyze(self, text: str | None) -> TransformerAnalysis:
        """Analyze non-empty customer text and return actual softmax probabilities."""
        preprocessing = preprocess_text(text)
        if not preprocessing.normalized_text:
            raise ValueError("text must contain non-whitespace characters")

        encoded = self.tokenizer(
            preprocessing.normalized_text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        encoded = {name: value.to(self.device) for name, value in encoded.items()}
        with torch.inference_mode():
            logits = self.model(**encoded).logits[0]
            probabilities = torch.softmax(logits, dim=-1)

        label_scores = tuple(
            ClassificationScore(
                label=str(self.model.config.id2label[index]), score=float(probabilities[index].item())
            )
            for index in range(probabilities.shape[0])
        )
        ranked_labels = tuple(sorted(label_scores, key=lambda item: item.score, reverse=True))
        best = ranked_labels[0]
        return TransformerAnalysis(
            input_text=text if text is not None else "",
            normalized_text=preprocessing.normalized_text,
            model_id=self.model_id,
            task="sentiment_analysis",
            label=best.label,
            confidence=best.score,
            ranked_labels=ranked_labels,
            device=str(self.device),
        )


@lru_cache(maxsize=1)
def get_analyzer() -> TransformerAnalyzer:
    """Return the process-wide analyzer, loading and caching it on first use."""
    return TransformerAnalyzer()


def analyze_text(text: str | None) -> TransformerAnalysis:
    """Analyze customer text with the cached CPU sentiment classifier."""
    return get_analyzer().analyze(text)
