# listings/models/__init__.py
#
# This file turns the `models/` directory into a Python package and
# explicitly re-exports every model class so that:
#
#   1. Django's migration engine can discover all models automatically
#      (it inspects the app's `models` namespace, not individual files).
#
#   2. All application code can import from the canonical short path:
#          from listings.models import Tool, Booking, Review ...
#      instead of reaching into sub-modules.
#
# ─── Import order follows dependency graph ────────────────────────────────────
#   Category  (no FK deps inside listings)
#   Tool      (depends on Category, users.User)
#   ToolImage (depends on Tool)
#   Booking   (depends on Tool, users.User)
#   Review    (depends on Booking, users.User)
# ─────────────────────────────────────────────────────────────────────────────

from listings.models.category   import Category
from listings.models.tool       import Tool, ConditionChoices
from listings.models.tool_image import ToolImage
from listings.models.booking    import Booking, BookingStatus
from listings.models.review     import Review, ReviewType
from listings.models.wishlist   import Wishlist
from .report import Report
from listings.models.notification import Notification, NotificationType
from listings.models.message      import Conversation, Message

__all__ = [
    # ── Core entities ──────────────────────────────────────────────
    "Category",
    "Tool",
    "ToolImage",
    "Booking",
    "Review",
    "Wishlist",
    "Notification",
    "Conversation",
    "Message",

    # ── Choices enums (re-exported for convenience in views/templates)
    "ConditionChoices",
    "BookingStatus",
    "ReviewType",
    "NotificationType",
]