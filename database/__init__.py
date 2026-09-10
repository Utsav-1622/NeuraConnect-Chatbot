"""SQLite database package for the customer support chatbot."""

from database.db import init_db
from database.seed import seed_faq_entries

__all__ = ["init_db", "seed_faq_entries"]
