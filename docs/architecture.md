# Architecture

## Overview

The project combines controlled FAQ retrieval with NLP preprocessing and Transformer sentiment analysis. This hybrid design keeps support answers predictable while still demonstrating practical NLP and Transformer integration.

```text
Browser chatbot or dashboard
        ↓
Flask routes
        ↓
Conversation context (recent SQLite messages)
        ↓
NLTK preprocessing
        ↓
SQLite FAQ retrieval and relevance ranking
        ↓
Transformer sentiment analysis (when an FAQ is selected)
        ↓
Controlled FAQ response or safe fallback
        ↓
SQLite interaction logging → dashboard API → dashboard browser view
```

## Components

### Browser interface

`templates/index.html` and `static/js/chat.js` provide the chatbot interface. The browser stores the current conversation ID in session storage, sends JSON to `/chat`, shows controlled responses and metadata, and can create a new conversation through `/reset`. The dashboard uses `templates/dashboard.html` and `static/js/dashboard.js` to read local API data.

### Flask application

`app.py` creates the Flask application, initializes and seeds SQLite, renders the two pages, and exposes `/chat`, `/reset`, `/api/stats`, and `/api/conversations`. The chat route validates JSON, creates or finds a conversation, records the user message, selects a response, and records assistant metadata.

### Conversation context

`chatbot/context.py` reads up to six recent messages from the current conversation only. Obvious referential follow-ups such as “What about electronics?” can be expanded with the previous support intent. A new conversation therefore does not reuse earlier context.

### NLTK preprocessing

`chatbot/preprocessing.py` lowercases and normalizes whitespace, tokenizes with NLTK, removes English stopwords, and applies Porter stemming. The stemmed tokens support deterministic lexical matching.

### FAQ retrieval and controlled responses

`chatbot/faq.py` ranks active SQLite FAQ entries using stem overlap across FAQ questions, keywords, and answers, with inverse-frequency weighting and a minimum relevance threshold. The highest acceptable FAQ supplies the intent and answer. `chatbot/response.py` returns that stored answer; unsupported questions receive a fixed safe fallback. The retrieval confidence is evidence-based and is not a calibrated probability.

### Transformer sentiment analysis

`chatbot/transformers.py` lazily loads `distilbert/distilbert-base-uncased-finetuned-sst-2-english` once per process on CPU. It produces SST-2 `POSITIVE` or `NEGATIVE` labels and softmax confidence. It does not identify returns, refunds, payment, or any other custom support intent. For a selected complaint FAQ with negative sentiment, the controlled response adds an acknowledgement before the stored FAQ answer.

### SQLite persistence and dashboard

`database/schema.sql` defines `conversations`, `messages`, and `faq_entries`. Foreign keys link messages to conversations and selected FAQs. `database/seed.py` provides 43 idempotently seeded FAQ records. `database/db.py` also aggregates assistant-side intent, sentiment, confidence, FAQ usage, and recent conversations for the dashboard.

## Why a hybrid FAQ approach?

- Stored FAQ answers are predictable and easy to review.
- The system has modest local CPU requirements.
- It is straightforward to run and inspect locally.
- Controlled responses reduce hallucination risk compared with generated policy answers.
- NLTK and the Transformer are used for clearly defined, demonstrable NLP tasks.
