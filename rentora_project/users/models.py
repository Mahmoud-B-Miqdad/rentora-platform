import re
import bcrypt

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ─────────────────────────────────────────────
#  Manager
# ─────────────────────────────────────────────

class UserManager(BaseUserManager):

    # ── private helpers ───────────────────────────────────────────────────────

    _EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    )
    _PHONE_REGEX = re.compile(
        r"^\+?[0-9\s\-]{7,20}$"
    )
    _NAME_REGEX = re.compile(
        r"^[a-zA-Z\u0600-\u06FF\s'\-]{2,80}$"
    )

    @staticmethod
    def _hash_password(plain_text):
        """Returns a bcrypt hash of *plain_text* as a UTF-8 string."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_text.encode("utf-8"), salt).decode("utf-8")

    # ── public API ────────────────────────────────────────────────────────────

    def register_validator(self, post_data):
        """
        Validates all incoming data for User registration.

        Rules enforced
        ──────────────
        name          : 2-80 chars, letters (Latin + Arabic), spaces, hyphens, apostrophes
        email         : RFC-5322-like regex + platform uniqueness check
        password      : min 8 chars, at least one digit and one letter
        confirm_pw    : must match password
        phone         : optional, but if provided must match E.164-ish pattern
        location      : required, 2-100 chars

        Returns
        -------
        dict  — field-keyed error messages; empty means validation passed.
        """
        errors = {}

        name       = post_data.get("name",       "").strip()
        email      = post_data.get("email",      "").strip().lower()
        password   = post_data.get("password",   "")
        confirm_pw = post_data.get("confirm_pw", "")
        phone      = post_data.get("phone",      "").strip()
        location   = post_data.get("location",   "").strip()

        # ── name ──────────────────────────────────────────────────────────────
        if not name:
            errors["name"] = "Full name is required."
        elif not self._NAME_REGEX.match(name):
            errors["name"] = (
                "Name must be 2–80 characters and may only contain "
                "letters (Arabic or Latin), spaces, hyphens, and apostrophes."
            )

        # ── email ─────────────────────────────────────────────────────────────
        if not email:
            errors["email"] = "Email address is required."
        elif not self._EMAIL_REGEX.match(email):
            errors["email"] = "Please enter a valid email address."
        elif self.filter(email=email).exists():
            errors["email"] = "An account with this email already exists."

        # ── password ──────────────────────────────────────────────────────────
        if not password:
            errors["password"] = "Password is required."
        elif len(password) < 8:
            errors["password"] = "Password must be at least 8 characters."
        elif not re.search(r"[A-Za-z]", password):
            errors["password"] = "Password must contain at least one letter."
        elif not re.search(r"[0-9]", password):
            errors["password"] = "Password must contain at least one digit."

        # ── confirm password ──────────────────────────────────────────────────
        if "password" not in errors:
            if not confirm_pw:
                errors["confirm_pw"] = "Please confirm your password."
            elif password != confirm_pw:
                errors["confirm_pw"] = "Passwords do not match."

        # ── phone (optional) ──────────────────────────────────────────────────
        if phone and not self._PHONE_REGEX.match(phone):
            errors["phone"] = (
                "Phone number must be 7–20 digits and may include "
                "spaces, hyphens, or a leading '+'."
            )

        # ── location ──────────────────────────────────────────────────────────
        if not location:
            errors["location"] = "Location (city or district) is required."
        elif len(location) < 2:
            errors["location"] = "Location must be at least 2 characters."
        elif len(location) > 100:
            errors["location"] = "Location must not exceed 100 characters."

        return errors

    def login_validator(self, post_data):
        """
        Validates login credentials.

        Returns
        -------
        dict  — field-keyed error messages; empty means validation passed.
        """
        errors = {}

        email    = post_data.get("email",    "").strip().lower()
        password = post_data.get("password", "")

        if not email:
            errors["email"] = "Email address is required."
        elif not self._EMAIL_REGEX.match(email):
            errors["email"] = "Please enter a valid email address."

        if not password:
            errors["password"] = "Password is required."

        if not errors:
            user = self.filter(email=email).first()
            
            if user is None:
                errors["credentials"] = "Invalid email or password."
            else:
                is_valid = False
                try:
                    is_valid = bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8"))
                except (ValueError, AttributeError):
                    is_valid = user.check_password(password)

                if not is_valid:
                    errors["credentials"] = "Invalid email or password."

        return errors
        
    def create_user(self, post_data):
        """
        Hashes the password with bcrypt and persists a new User record.
        Callers must run register_validator() first and guard on errors.

        NOTE: We bypass Django's set_password() intentionally — bcrypt is
        handled manually so our login_validator() can use bcrypt.checkpw()
        directly without Django's authentication pipeline.
        """
        user = self.model(
            name=post_data["name"].strip(),
            email=self.normalize_email(post_data["email"].strip().lower()),
            phone=post_data.get("phone", "").strip() or None,
            location=post_data.get("location", "").strip(),
        )
        # Store bcrypt hash directly in the password column.
        user.password = self._hash_password(post_data["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Required by Django's management commands (e.g. createsuperuser).
        Bypasses register_validator — intended for CLI use only.
        """
        extra_fields.setdefault("is_staff",     True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified",  True)
        extra_fields.setdefault("name",     extra_fields.get("name", "Admin"))
        extra_fields.setdefault("location", extra_fields.get("location", "N/A"))

        user = self.model(
            email=self.normalize_email(email.strip().lower()),
            **extra_fields,
        )
        user.password = self._hash_password(password)
        user.save(using=self._db)
        return user

    def get_by_email(self, email):
        """
        Returns the User matching *email* (case-insensitive), or None.
        """
        return self.filter(email=email.strip().lower()).first()

    def update_profile(self, user, post_data, files=None):
        """
        Validates and applies profile edits for name, phone, location,
        and optional profile_image upload.

        Returns (user, errors). Callers should check errors before trusting
        the returned user instance.
        """
        errors = {}

        name     = post_data.get("name",     "").strip()
        phone    = post_data.get("phone",    "").strip()
        location = post_data.get("location", "").strip()

        if not name:
            errors["name"] = "Full name is required."
        elif not self._NAME_REGEX.match(name):
            errors["name"] = (
                "Name must be 2–80 characters and may only contain "
                "letters (Arabic or Latin), spaces, hyphens, and apostrophes."
            )

        if phone and not self._PHONE_REGEX.match(phone):
            errors["phone"] = (
                "Phone number must be 7–20 digits and may include "
                "spaces, hyphens, or a leading '+'."
            )

        if not location:
            errors["location"] = "Location is required."
        elif len(location) < 2 or len(location) > 100:
            errors["location"] = "Location must be 2–100 characters."

        if errors:
            return user, errors

        user.name     = name
        user.phone    = phone or None
        user.location = location

        if files:
            img = files.get("profile_image")
            if img and img.size > 0:
                user.profile_image = img

        user.save()
        return user, {}


# ─────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────

class User(AbstractBaseUser, PermissionsMixin):
    """
    Core platform member — replaces Django's built-in User entirely.

    Inherits from AbstractBaseUser (provides the password column and
    last_login) and PermissionsMixin (provides is_superuser + groups).

    A single User instance can act as both a Tool owner (listing tools
    for rent) and a Renter (booking tools from others) — controlled
    entirely at the relationship level, not by a role field.
    """

    name = models.CharField(
        max_length=80,
        help_text="Full display name shown across the platform.",
    )
    email = models.EmailField(
        max_length=100,
        unique=True,
        help_text="Primary identifier used for login and notifications.",
    )
    # AbstractBaseUser already defines `password` and `last_login`.
    # We store our bcrypt hash directly in that inherited column.
    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Optional contact number for booking coordination.",
    )
    location = models.CharField(
        max_length=100,
        help_text="City or district used for proximity-based tool discovery.",
    )
    profile_image = models.ImageField(
        upload_to="profiles/",
        null=True,
        blank=True,
        help_text="Optional avatar displayed on profile and review cards.",
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Running average of all reviews received as owner or renter.",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Trust badge granted after identity confirmation.",
    )
    # Required by Django's admin and permission system.
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user account is active.",
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Grants access to the Django admin site.",
    )
    last_seen  = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Automatically updated on every page request via LastSeenMiddleware.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    # Tell Django which field is used as the username for authentication.
    USERNAME_FIELD  = "email"
    # Fields prompted by `createsuperuser` beyond USERNAME_FIELD + password.
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        verified = " ✓" if self.is_verified else ""
        return f"{self.name} <{self.email}>{verified}"


# ─────────────────────────────────────────────
#  Email Verification Token
# ─────────────────────────────────────────────

class EmailVerification(models.Model):
    """
    One-time token sent to a user's email address.
    Deleted automatically after successful verification.
    """
    user       = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification",
    )
    token      = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    class Meta:
        verbose_name = "Email Verification"

    def __str__(self):
        return f"Verification for {self.user.email}"