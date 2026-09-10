"""Curated, repeatable FAQ seed data for the fictional support service."""

from pathlib import Path

from database.db import get_faq_entries, init_db, insert_faq_entry


FAQ_ENTRIES = (
    ("greeting", "Hello", "Hello! How can our support team help you today?", "hello hi hey greeting"),
    ("greeting", "Good morning", "Good morning! Please tell us what you need help with.", "good morning hello greeting"),
    ("order_status", "Where is my order?", "You can check your order status from your order confirmation or account order history. Contact support with the order number if it needs review.", "where order tracking status"),
    ("order_status", "My order is still processing", "Orders may remain processing while payment and stock are confirmed. If the status does not change after a reasonable time, contact support with your order number.", "order processing pending"),
    ("order_status", "Can I track my purchase?", "When tracking is available, we send the tracking details after the order is dispatched.", "track purchase shipment order"),
    ("shipping", "What shipping options are available?", "Available delivery options are shown at checkout and can vary by item and destination.", "shipping options checkout"),
    ("shipping", "How much does shipping cost?", "Shipping charges, if any, are calculated and displayed before you place the order.", "shipping cost charge fee"),
    ("shipping", "Do you ship internationally?", "Delivery availability is shown at checkout after you select a destination. Some items may have location restrictions.", "international shipping countries"),
    ("delivery", "When will my package arrive?", "Estimated delivery information appears at checkout and in dispatch updates. Estimates can change due to carrier or destination conditions.", "delivery arrival estimate package"),
    ("delivery", "My delivery is late", "Please check the latest tracking update first. If it appears stalled, contact support with your order number and delivery details.", "late delayed delivery tracking"),
    ("delivery", "What if I missed a delivery?", "Use the carrier notice or tracking page for available next steps. Support can help review the order if no option is shown.", "missed delivery carrier"),
    ("cancellation", "Can I cancel my order?", "You may request cancellation before an order is dispatched. We will confirm whether the request can still be completed.", "cancel order cancellation"),
    ("cancellation", "How do I cancel an order?", "Contact support promptly with your order number and cancellation request. Dispatch status determines whether cancellation is possible.", "how cancel order"),
    ("cancellation", "I accidentally ordered the wrong item", "Request cancellation as soon as possible. If the item has already shipped, you can review the return options after delivery.", "wrong item cancel"),
    ("returns", "What is your return policy?", "Eligible unused items may be returned within the return window shown with the order. Items must be in their original condition and include supplied accessories.", "return policy eligible condition"),
    ("returns", "How do I return an item?", "Contact support with your order number and the item you want to return. We will provide the applicable return instructions.", "how return item instructions"),
    ("returns", "Can I return electronics?", "Electronics may be returned when eligible and in original condition with all accessories. Contact support for the item-specific return instructions.", "return electronics accessories"),
    ("refunds", "When will I receive my refund?", "Refunds are started after an eligible return is received and reviewed. Your payment provider may need additional processing time.", "refund status processing"),
    ("refunds", "Where is my refund?", "Check your return confirmation and payment method first. If the expected processing period has passed, contact support with the order number.", "missing refund return"),
    ("refunds", "How are refunds issued?", "Approved refunds are sent to the original payment method whenever possible.", "refund original payment method"),
    ("payment", "Which payment methods do you accept?", "Available payment methods are displayed securely at checkout and may depend on your location.", "payment methods card checkout"),
    ("payment", "Why was my payment declined?", "Confirm the billing details and available funds, then try again. Your bank or payment provider can explain a declined authorization.", "payment declined card"),
    ("payment", "Was I charged twice?", "Please compare the transaction entries with your order confirmations. Contact support with the order number and transaction details for review.", "charged twice duplicate payment"),
    ("account", "How do I reset my password?", "Use the password reset option on the sign-in page. We will send reset instructions to the email address on the account.", "reset password account login"),
    ("account", "How do I update my account details?", "Sign in and open your account settings to update available profile details.", "update account profile email"),
    ("account", "I cannot sign in", "Check your email address and password, then use password reset if needed. Contact support if access is still unavailable.", "cannot login sign in"),
    ("product_availability", "Is this product in stock?", "Current availability is shown on the product page. Availability can change before checkout is completed.", "product stock available"),
    ("product_availability", "When will an item be back in stock?", "We cannot promise a restock date unless one is shown on the product page. Check the page again for the latest availability.", "back in stock restock"),
    ("product_availability", "Can I reserve an unavailable item?", "Reservations are only available if the product page explicitly offers that option.", "reserve unavailable product"),
    ("policies", "Where can I find your policies?", "Our applicable purchase, privacy, delivery, and returns policies are available through the policy links on the service.", "policies privacy returns delivery"),
    ("policies", "How is my personal information handled?", "We handle account and order information according to the privacy policy available through the service.", "privacy personal information data"),
    ("policies", "Can policy terms change?", "Policies may be updated when necessary. The current version available through the service applies to new activity.", "policy changes terms"),
    ("support_contact", "How can I contact support?", "Use the support contact option in the service and include your order number when your request concerns an order.", "contact support help"),
    ("support_contact", "What information should I provide?", "Please include relevant order, account, or product details, but never send payment card numbers or passwords.", "support order number security"),
    ("support_contact", "Can I speak to a support agent?", "Use the support contact option to submit your request and the team will respond through the available support channel.", "agent human support contact"),
    ("thanks", "Thank you", "You are welcome! Let us know if there is anything else we can help with.", "thanks thank you"),
    ("thanks", "That helped", "Glad to help. Please reach out again if you need anything else.", "helped appreciate thanks"),
    ("goodbye", "Goodbye", "Goodbye! We are here whenever you need support.", "goodbye bye"),
    ("goodbye", "See you later", "Take care, and feel free to contact support again when needed.", "see you later bye"),
    ("complaint", "I want to make a complaint", "We are sorry your experience was disappointing. Please contact support with the relevant order or account details so we can review it.", "complaint unhappy dissatisfied"),
    ("complaint", "My item arrived damaged", "We are sorry to hear that. Contact support with your order number and clear details of the issue so we can review the available resolution.", "damaged item complaint"),
    ("complaint", "The service was poor", "We appreciate the feedback and are sorry we fell short. Please share the relevant details with support so the issue can be reviewed.", "poor service feedback complaint"),
    ("unknown", "I need help with something else", "I can help with orders, delivery, returns, refunds, payments, accounts, and product availability. Please describe what you need.", "help other unknown fallback"),
)


def seed_faq_entries(database_path: str | Path | None = None) -> int:
    """Initialize and idempotently seed the FAQ knowledge base; return its entry count."""
    init_db(database_path)
    for index, (intent, question, answer, keywords) in enumerate(FAQ_ENTRIES, start=1):
        insert_faq_entry(
            intent=intent,
            question=question,
            answer=answer,
            keywords=keywords,
            seed_key=f"faq-{index:03d}",
            database_path=database_path,
        )
    return len(get_faq_entries(database_path, active_only=False))
