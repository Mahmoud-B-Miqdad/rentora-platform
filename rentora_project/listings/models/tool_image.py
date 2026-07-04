import re

from django.db import models


# ─────────────────────────────────────────────
#  Manager
# ─────────────────────────────────────────────

class ToolImageManager(models.Manager):

    # ── private helpers ───────────────────────────────────────────────────────

    _ALLOWED_EXTENSIONS = re.compile(
        r"\.(jpg|jpeg|png|webp|gif)$", re.IGNORECASE
    )
    _MAX_IMAGES_PER_TOOL = 8

    # ── public API ────────────────────────────────────────────────────────────

    def register_validator(self, post_data, tool):
        """
        Validates an incoming image upload for a given tool listing.

        Parameters
        ----------
        post_data : dict
            Must contain an 'image' key whose value is a Django UploadedFile
            (or any object exposing a .name attribute for extension checking).
        tool : listings.Tool
            The parent listing this image will be attached to.

        Returns
        -------
        dict
            Field-keyed error messages. Empty dict means validation passed.
        """
        errors = {}

        image      = post_data.get("image")
        is_primary = post_data.get("is_primary", False)

        # ── tool reference ────────────────────────────────────────────────────
        if tool is None or not getattr(tool, "pk", None):
            errors["tool"] = "A valid parent tool listing is required."
            return errors  # cannot continue without a tool

        # ── image presence ────────────────────────────────────────────────────
        if not image:
            errors["image"] = "An image file is required."
        else:
            file_name = getattr(image, "name", "") or ""
            if not self._ALLOWED_EXTENSIONS.search(file_name):
                errors["image"] = (
                    "Unsupported file type. "
                    "Accepted formats: JPG, JPEG, PNG, WEBP, GIF."
                )

        # ── per-tool image cap ────────────────────────────────────────────────
        current_count = self.filter(tool=tool).count()
        if current_count >= self._MAX_IMAGES_PER_TOOL:
            errors["image"] = (
                f"A listing may not have more than "
                f"{self._MAX_IMAGES_PER_TOOL} images."
            )

        # ── primary-image uniqueness ──────────────────────────────────────────
        # If the caller wants this image to be primary, demote any existing one.
        # We only flag it as an *error* if the field itself is invalid;
        # the demotion logic lives in create_image() below.
        if not isinstance(is_primary, bool):
            try:
                is_primary = bool(int(is_primary))
            except (TypeError, ValueError):
                errors["is_primary"] = "is_primary must be a boolean value."

        return errors

    def create_image(self, post_data, tool):
        """
        Persists a new ToolImage record.

        If is_primary=True, demotes any existing primary image for this tool
        before inserting the new record so the invariant is maintained.

        Callers must run register_validator() first and guard on errors.
        """
        is_primary = bool(post_data.get("is_primary", False))

        if is_primary:
            # Atomically demote the previous primary (if any).
            self.filter(tool=tool, is_primary=True).update(is_primary=False)

        return self.create(
            tool=tool,
            image=post_data["image"],
            is_primary=is_primary,
        )

    def primary_for(self, tool):
        """
        Returns the primary ToolImage for *tool*, or None if not set.
        """
        return self.filter(tool=tool, is_primary=True).first()

    def gallery_for(self, tool):
        """
        Returns all images for *tool*, primary image first.
        """
        return self.filter(tool=tool).order_by("-is_primary", "id")


# ─────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────

class ToolImage(models.Model):
    """
    Stores individual uploaded photos for a Tool listing.
    One image per tool is designated as the primary display image.
    """

    tool = models.ForeignKey(
        "listings.Tool",
        on_delete=models.CASCADE,
        related_name="images",
        help_text="The parent tool listing this photo belongs to.",
    )
    image = models.ImageField(
        upload_to="tools/images/%Y/%m/",
        help_text="Uploaded photo file (stored under MEDIA_ROOT).",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=(
            "Marks this photo as the cover image shown on listing cards. "
            "Only one image per tool should carry this flag."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ToolImageManager()

    class Meta:
        verbose_name = "Tool Image"
        verbose_name_plural = "Tool Images"
        ordering = ["-is_primary", "id"]

    def __str__(self):
        flag = " [primary]" if self.is_primary else ""
        return f"Image #{self.pk} for '{self.tool.title}'{flag}"