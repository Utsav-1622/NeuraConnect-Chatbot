import nltk
import pytest

from chatbot.preprocessing import (
    NLTK_DATA_DIR,
    PreprocessingResult,
    ensure_nltk_resources,
    preprocess_text,
)


def test_resources_are_initialized_and_usable():
    ensure_nltk_resources()
    assert str(NLTK_DATA_DIR) in nltk.data.path
    assert nltk.data.find("corpora/stopwords")


def test_normal_customer_support_text_uses_nltk_representations():
    result = preprocess_text("Where is my order?")

    assert isinstance(result, PreprocessingResult)
    assert result.normalized_text == "where is my order?"
    assert result.tokens == ("where", "is", "my", "order", "?")
    assert result.filtered_tokens == ("order",)
    assert result.stemmed_tokens == ("order",)
    assert result.normalized_tokens == result.stemmed_tokens


def test_case_whitespace_and_punctuation_are_normalized_without_losing_tokens():
    result = preprocess_text("  I HAVEN'T   received — my PACKAGE yet!  ")

    assert result.normalized_text == "i haven't received - my package yet!"
    assert "received" in result.tokens
    assert "package" in result.filtered_tokens
    assert "!" in result.tokens
    assert "!" not in result.filtered_tokens


@pytest.mark.parametrize("value", ["", "   ", None])
def test_empty_and_none_input_are_safe(value):
    result = preprocess_text(value)

    assert result.normalized_text == ""
    assert result.tokens == ()
    assert result.filtered_tokens == ()
    assert result.stemmed_tokens == ()


def test_stopwords_and_stemming_are_applied():
    result = preprocess_text("Can I return this product?")

    assert "can" not in result.filtered_tokens
    assert result.filtered_tokens == ("return", "product")
    assert result.stemmed_tokens == ("return", "product")


def test_preprocessing_is_deterministic_for_refund_question():
    text = "How long does a refund take?"

    assert preprocess_text(text) == preprocess_text(text)


def test_invalid_input_type_is_rejected_clearly():
    with pytest.raises(TypeError, match="string or None"):
        preprocess_text(123)  # type: ignore[arg-type]
