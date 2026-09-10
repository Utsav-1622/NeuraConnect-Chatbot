import pytest

from chatbot.transformers import (
    MODEL_ID,
    ClassificationScore,
    TransformerAnalysis,
    analyze_text,
    get_analyzer,
)


@pytest.fixture(scope="module")
def analyzer():
    return get_analyzer()


def test_model_and_tokenizer_initialize_on_cpu(analyzer):
    assert analyzer.model_id == MODEL_ID
    assert analyzer.device.type == "cpu"
    assert analyzer.tokenizer is not None
    assert analyzer.model is not None
    assert analyzer.load_seconds >= 0


def test_real_sentiment_inference_returns_probabilities(analyzer):
    result = analyzer.analyze("I am very happy with my order.")

    assert isinstance(result, TransformerAnalysis)
    assert result.model_id == MODEL_ID
    assert result.task == "sentiment_analysis"
    assert result.device == "cpu"
    assert result.label in {"POSITIVE", "NEGATIVE"}
    assert 0.0 <= result.confidence <= 1.0
    assert result.ranked_labels
    assert all(isinstance(item, ClassificationScore) for item in result.ranked_labels)
    assert sum(item.score for item in result.ranked_labels) == pytest.approx(1.0)
    assert result.ranked_labels[0].label == result.label


def test_second_inference_reuses_cached_model(analyzer):
    first = analyze_text("My package still has not arrived and I am frustrated.")
    second = analyze_text("How can I get a refund?")

    assert get_analyzer() is analyzer
    assert first.model_id == second.model_id == MODEL_ID
    assert first.input_text != second.input_text


@pytest.mark.parametrize("value", [None, "", "   "])
def test_empty_input_is_rejected_deterministically(value):
    with pytest.raises(ValueError, match="non-whitespace"):
        analyze_text(value)
