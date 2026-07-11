import re

from django.db import models
from django.utils.translation import gettext_lazy as _


# ─────────────────────────────────────────────
#  Choices
# ─────────────────────────────────────────────

class ConditionChoices(models.TextChoices):
    EXCELLENT = "excellent", _("Excellent")
    GOOD      = "good",      _("Good")
    FAIR      = "fair",      _("Fair")


# ─────────────────────────────────────────────
#  Manager
# ─────────────────────────────────────────────

class ToolManager(models.Manager):

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _is_positive_decimal(value, field_name, errors, label):
        """
        Coerces *value* to float and confirms it is strictly positive.
        Populates *errors[field_name]* on failure and returns None.
        Returns the coerced float on success.
        """
        try:
            amount = float(value)
        except (TypeError, ValueError):
            errors[field_name] = f"{label} must be a valid number."
            return None

        if amount <= 0:
            errors[field_name] = f"{label} must be greater than zero."
            return None

        return amount

    # ── public API ────────────────────────────────────────────────────────────

    def register_validator(self, post_data, owner):
        """
        Validates all incoming data for Tool creation/update.

        Parameters
        ----------
        post_data : dict
            Raw POST payload (or equivalent mapping).
        owner : users.User
            The authenticated user who owns this listing.

        Returns
        -------
        dict
            Field-keyed error messages. Empty dict means validation passed.
        """
        errors = {}

        title       = post_data.get("title",       "").strip()
        description = post_data.get("description", "").strip()
        daily_rate  = post_data.get("daily_rate")
        deposit     = post_data.get("deposit")
        location    = post_data.get("location",    "").strip()
        condition   = post_data.get("condition",   "").strip()
        category_id = post_data.get("category_id")

        # ── title ─────────────────────────────────────────────────────────────
        if not title:
            errors["title"] = "Tool title is required."
        elif len(title) < 3:
            errors["title"] = "Tool title must be at least 3 characters."
        elif len(title) > 120:
            errors["title"] = "Tool title must not exceed 120 characters."

        # ── description ───────────────────────────────────────────────────────
        if not description:
            errors["description"] = "A description is required."
        elif len(description) < 20:
            errors["description"] = "Description must be at least 20 characters."
        elif len(description) > 2000:
            errors["description"] = "Description must not exceed 2000 characters."

        # ── daily_rate ────────────────────────────────────────────────────────
        self._is_positive_decimal(daily_rate, "daily_rate", errors, "Daily rate")

        # ── deposit ───────────────────────────────────────────────────────────
        self._is_positive_decimal(deposit, "deposit", errors, "Deposit amount")

        # ── location ──────────────────────────────────────────────────────────
        if not location:
            errors["location"] = "Location is required."
        elif len(location) < 2:
            errors["location"] = "Location must be at least 2 characters."
        elif len(location) > 100:
            errors["location"] = "Location must not exceed 100 characters."

        # ── condition ─────────────────────────────────────────────────────────
        valid_conditions = {c.value for c in ConditionChoices}
        if not condition:
            errors["condition"] = "Condition is required."
        elif condition not in valid_conditions:
            errors["condition"] = (
                f"Condition must be one of: {', '.join(valid_conditions)}."
            )

        # ── category ──────────────────────────────────────────────────────────
        if not category_id:
            errors["category_id"] = "Category is required."
        else:
            from listings.models.category import Category  # local import to avoid circular refs
            if not Category.objects.filter(pk=category_id).exists():
                errors["category_id"] = "Selected category does not exist."

        # ── owner sanity check ────────────────────────────────────────────────
        if owner is None or not getattr(owner, "pk", None):
            errors["owner"] = "A valid authenticated owner is required."

        return errors

    def create_tool(self, post_data, owner):
        """
        Persists a new Tool listing.
        Callers must run register_validator() first and guard on errors.
        """
        from listings.models.category import Category

        return self.create(
            owner=owner,
            category=Category.objects.get(pk=post_data["category_id"]),
            title=post_data["title"].strip(),
            description=post_data["description"].strip(),
            daily_rate=float(post_data["daily_rate"]),
            deposit=float(post_data["deposit"]),
            location=post_data["location"].strip(),
            condition=post_data["condition"].strip(),
            is_available=True,
        )

    def available(self):
        """Convenience queryset: only active, available listings."""
        return self.filter(is_available=True)

    def owned_by(self, user):
        """All tools listed by a specific owner."""
        return self.filter(owner=user)


# ─────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────

class Tool(models.Model):
    """
    Core listing entity — a physical tool or piece of equipment
    offered for peer-to-peer rental on the Rentora platform.
    """

    owner = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="tools",
        help_text="The platform member who owns and manages this listing.",
    )
    category = models.ForeignKey(
        "listings.Category",
        on_delete=models.SET_NULL,
        null=True,
        related_name="tools",
        help_text="Top-level grouping used for discovery and filtering.",
    )
    title = models.CharField(
        max_length=120,
        help_text="Short, descriptive name shown on listing cards.",
    )
    description = models.TextField(
        help_text="Full details: use-case, brand, accessories included, etc.",
    )
    daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Rental price charged per calendar day (local currency).",
    )
    deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Refundable security deposit collected before rental begins.",
    )
    location = models.CharField(
        max_length=100,
        help_text="City or district where the tool is available for pickup.",
    )
    condition = models.CharField(
        max_length=20,
        choices=ConditionChoices.choices,
        default=ConditionChoices.GOOD,
        help_text="Owner-declared (or AI-suggested) physical condition of the tool.",
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Controls whether this listing appears in search results.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ToolManager()

    class Meta:
        verbose_name = "Tool"
        verbose_name_plural = "Tools"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.owner} ({self.get_condition_display()})"