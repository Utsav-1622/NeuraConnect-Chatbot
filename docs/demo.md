# 3–5 Minute Demo Procedure

1. Activate the virtual environment and start the application with `python app.py`.
2. Open `http://127.0.0.1:5000/`.
3. Ask: **“What is your return policy?”** Explain that the answer is a controlled response from the returns FAQ.
4. Ask: **“What about electronics?”** Point out the **Context used** metadata: the conversation’s previous returns intent helps resolve this short follow-up.
5. Ask: **“Where is my order?”** Show that the chatbot selects order-status support instead of reusing the returns context.
6. Ask: **“My package still hasn't arrived and I am very frustrated.”** Show delivery support and the Transformer’s negative sentiment metadata.
7. Ask: **“What is quantum entanglement?”** Show the safe fallback because it is outside the support FAQ knowledge base.
8. Open `http://127.0.0.1:5000/dashboard`.
9. Show conversations, user messages, bot responses, average confidence, intent distribution, sentiment distribution, most-used FAQs, and recent conversations. Explain that these values come from SQLite records.
10. Return to the chatbot and select **New conversation**. Explain that a new conversation ID is created, so old context is not reused.

The demo intentionally presents controlled FAQ support, not generated policy text.
