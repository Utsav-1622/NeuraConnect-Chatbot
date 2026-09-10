# AI-Powered Customer Support Chatbot Using NLP and Transformers

## Overview

This is a hybrid customer-support chatbot for common support questions. It uses a controlled SQLite FAQ knowledge base, NLTK lexical preprocessing, basic conversation context, and a Hugging Face Transformer for sentiment analysis. Flask supplies the web/API layer and SQLite records interactions for the dashboard. It is not a generative LLM chatbot: answers are controlled responses selected from the FAQ data or a safe fallback.

## Features

- FAQ-based customer support with support intent/category metadata
- NLTK normalization, tokenization, stopword filtering, and Porter stemming
- Real CPU Transformer sentiment analysis
- Simple contextual follow-up handling within a conversation
- SQLite conversation and response metadata logging
- Retrieval/relevance and response confidence values
- Safe fallback for unsupported questions
- Browser chatbot interface and SQLite-backed analytics dashboard

## Supported categories

The 43 seeded FAQ records cover: greeting, order status, shipping, delivery, cancellation, returns, refunds, payment, account, product availability, policies, support contact, thanks, goodbye, complaint, and unknown/fallback guidance.

## Technology stack

- Python, Flask, SQLite
- NLTK
- Hugging Face Transformers and PyTorch
- HTML, CSS, vanilla JavaScript
- pytest

## Project structure

```text
.
├── app.py                    # Flask application and routes
├── config.py                 # Project-relative configuration
├── chatbot/                  # NLP, retrieval, response, and context modules
├── database/                 # SQLite helpers, schema, and FAQ seed data
├── templates/                # Chatbot and dashboard HTML pages
├── static/                   # CSS and browser JavaScript
├── tests/                    # pytest unit and integration tests
├── docs/                     # Architecture, testing, demo, and project notes
└── requirements.txt
```

## Installation

From the project directory on Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

The first use of NLTK can download its English stopword resource, and the first Transformer inference can download the public model if it is not already cached.

## Running

With the environment activated, run:

```bash
python app.py
```

Open `http://127.0.0.1:5000/` in a browser. The SQLite database is initialized and the FAQ knowledge base is seeded automatically.

## Usage

Ask a support question on the chatbot page. Use **New conversation** to create a separate conversation and avoid reusing earlier context. Open `http://127.0.0.1:5000/dashboard` to see locally stored interaction analytics.

## Testing

Run the complete suite with:

```bash
.venv/bin/python -m pytest -q
```

Final verified result: **46 passed**.

## Main routes

| Route | Purpose |
| --- | --- |
| `GET /` | Renders the browser chatbot. |
| `POST /chat` | Validates a JSON message, handles the support interaction, logs it, and returns JSON. |
| `POST /reset` | Creates a new conversation and returns its ID. |
| `GET /dashboard` | Renders the analytics dashboard. |
| `GET /api/stats` | Returns SQLite-derived aggregate statistics. |
| `GET /api/conversations` | Returns recent conversation summaries. |

## Database

SQLite contains `conversations`, `messages`, and `faq_entries`. `conversations` identifies chat sessions; `messages` stores user and assistant content plus retrieval/sentiment metadata; `faq_entries` holds the controlled knowledge base. Schema initialization and idempotent FAQ seeding happen at application startup.

## AI and NLP behavior

NLTK performs lexical preprocessing for retrieval. The model `distilbert/distilbert-base-uncased-finetuned-sst-2-english` runs on CPU and classifies text with SST-2 `POSITIVE` or `NEGATIVE` sentiment labels and softmax confidence. Custom support intents such as `returns` or `payment` come from the selected FAQ retrieval metadata, not from the Transformer. The answer remains a controlled FAQ answer or fallback.

## Limitations

- English-focused lexical matching and preprocessing
- Controlled local FAQ knowledge base; not a generative LLM
- Simple recent-message context only
- Local CPU model inference
- SST-2 provides positive/negative sentiment only

See the architecture documentation, testing notes, and demo procedure for more details
