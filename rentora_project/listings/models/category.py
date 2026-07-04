import re

from django.db import models


# ─────────────────────────────────────────────
#  Manager
# ─────────────────────────────────────────────

class CategoryManager(models.Manager):

    def register_validator(self, post_data):
        """
        Validates all incoming data for Category creation/update.
        Returns a dictionary of field-level error messages.
        """
        errors = {}

        name = post_data.get("name", "").strip()
        icon = post_data.get("icon", "").strip()

        # ── name ──────────────────────────────────────────────────────────────
        if not name:
            errors["name"] = "Category name is required."
        elif len(name) < 2:
            errors["name"] = "Category name must be at least 2 characters."
        elif len(name) > 50:
            errors["name"] = "Category name must not exceed 50 characters."
        elif not re.match(r"^[\w\s\-&()]+$", name):
            errors["name"] = (
                "Category name may only contain letters, digits, spaces, "
                "hyphens, ampersands, and parentheses."
            )
        elif self.filter(name__iexact=name).exists():
            errors["name"] = f"A category named '{name}' already exists."

        # ── icon (optional – validate only when provided) ─────────────────────
        if icon and not re.match(r"^[\w\-\/]+$", icon):
            errors["icon"] = (
                "Icon value must be a valid CSS class or relative path "
                "(letters, digits, hyphens, underscores, and forward slashes only)."
            )

        return errors

    def create_category(self, post_data):
        """
        Creates and persists a new Category after successful validation.
        Callers must run register_validator() first and guard on errors.
        """
        return self.create(
            name=post_data["name"].strip(),
            icon=post_data.get("icon", "").strip() or None,
        )


# ─────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────

class Category(models.Model):
    """
    Represents a top-level grouping for tool listings on the platform
    (e.g. Power Tools, Generators, Construction, Agriculture, Events).
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Human-readable category label displayed across the UI.",
    )
    icon = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="CSS icon class or relative asset path used in category cards.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CategoryManager()

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name