# Testing

The project uses `pytest` for unit and integration testing. Run the suite from the project root with:

```bash
.venv/bin/python -m pytest -q
```

Final verified result: **46 passed**.

## Automated testing areas

- **Database:** schema initialization, foreign-key enforcement, idempotent initialization, CRUD behavior, and conversation timestamps.
- **FAQ data and retrieval:** complete seeding, idempotent seeding, deterministic supported retrieval, fallback behavior, relevance evidence, and safe search handling.
- **NLTK preprocessing:** resource initialization, normalization, tokenization, stopword filtering, Porter stemming, deterministic output, empty input, and type validation.
- **Transformer:** CPU model/tokenizer initialization, real sentiment probabilities, cached reuse, and empty-input handling.
- **Response selection:** controlled FAQ answers, paraphrase retrieval, safe fallback, complaint handling, and confidence behavior.
- **Conversation context:** recent-message limits, follow-up resolution, topic preservation, conversation isolation, and contextual retrieval/response integration.
- **Chat API:** root rendering, valid persisted interactions, request validation, contextual behavior, unknown/complaint behavior, and reset validation.
- **Dashboard:** empty state, SQLite-derived statistics and recent conversations, and updates from real chat interactions.

## Manual end-to-end verification

The completed application was also checked through the browser/API workflow: a return-policy request, contextual follow-up, order-support request, negative complaint, unsupported-question fallback, reset, dashboard rendering, and SQLite/API statistic cross-check. The final validation also compiled application, chatbot, database, and test modules.

No coverage percentage is claimed; the result above is the actual final test-suite outcome.
