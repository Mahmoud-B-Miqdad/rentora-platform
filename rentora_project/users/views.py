from django.shortcuts import render, redirect, get_object_or_404
from django.contrib    import messages
from django.db.models  import Avg, Count, Prefetch, Q

from users.models    import User, EmailVerification
from users.services  import send_verification_email
from listings.models import Tool, ToolImage, Booking, BookingStatus, Review, ReviewType
from listings.models.report import Report

from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings


def test_email(request):
    send_mail(
        subject="Rentora Test Email",
        message="Hello! This is a test email from Rentora.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=["monaalakhars00@gmail.com"],
        fail_silently=False,
    )

    return HttpResponse("Email sent successfully!")


# ─────────────────────────────────────────────
#  Register View
# ─────────────────────────────────────────────

def register_view(request):
    if request.method == "POST":
        errors = User.objects.register_validator(request.POST)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, "users/auth.html", {"active_form": "register"})

        user = User.objects.create_user(request.POST)

        try:
            send_verification_email(request, user)
            messages.success(
                request,
                "Account created! We've sent a verification link to "
                f"{user.email} — please check your inbox.",
            )
        except Exception:
            messages.success(
                request,
                "Account created successfully! Please sign in.",
            )

        return render(request, "users/auth.html", {"active_form": "login"})

    return render(request, "users/auth.html", {"active_form": "login"})


# ─────────────────────────────────────────────
#  Login View
# ─────────────────────────────────────────────

def login_view(request):
    if request.method == "POST":
        errors = User.objects.login_validator(request.POST)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, "users/auth.html", {"active_form": "login"})

        user = User.objects.get_by_email(request.POST["email"])
        request.session["user_id"]   = user.id
        request.session["user_name"] = user.name
        return redirect("listings:home")

    return render(request, "users/auth.html", {"active_form": "login"})


# ─────────────────────────────────────────────
#  Logout View
# ─────────────────────────────────────────────

def logout_view(request):
    request.session.flush()
    return redirect("users:login")


# ─────────────────────────────────────────────
#  Email Verification
# ─────────────────────────────────────────────

def verify_email_view(request, token):
    """
    Called when the user clicks the link in their verification email.
    Marks the account as verified and auto-logs them in.
    """
    verification = get_object_or_404(EmailVerification, token=token)

    if verification.is_expired():
        verification.delete()
        messages.error(
            request,
            "This verification link has expired. Please request a new one.",
        )
        return redirect("users:login")

    user = verification.user
    user.is_verified = True
    user.save(update_fields=["is_verified"])
    verification.delete()

    request.session["user_id"]   = user.id
    request.session["user_name"] = user.name

    messages.success(request, "Your email has been verified. Welcome to Rentora!")
    return redirect("listings:home")


def resend_verification_view(request):
    """
    POST — resend the verification email to the currently logged-in user.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("users:login")

    if request.method != "POST":
        return redirect("users:profile")

    user = get_object_or_404(User, pk=user_id)

    if user.is_verified:
        messages.info(request, "Your account is already verified.")
        return redirect("users:profile")

    try:
        send_verification_email(request, user)
        messages.success(
            request,
            f"Verification email sent to {user.email}. Please check your inbox.",
        )
    except Exception:
        messages.error(
            request,
            "Could not send the email right now. Please try again later.",
        )

    return redirect("users:profile")


# ─────────────────────────────────────────────
#  Profile View
# ─────────────────────────────────────────────

def profile_view(request, user_id=None):
    logged_in_id = request.session.get("user_id")
    if not logged_in_id:
        return redirect("users:login")

    # لو ما في user_id بالـ URL، عرض بروفايل الـ logged in user
    if user_id is None:
        user_id = int(logged_in_id)

    profile_user = get_object_or_404(User, pk=user_id)
    is_owner     = int(logged_in_id) == int(user_id)
    edit_mode    = request.GET.get("edit") == "1" and is_owner
    errors       = {}

    # Handle profile update (POST) — فقط لو owner
    if request.method == "POST" and is_owner:
        user, errors = User.objects.update_profile(
            profile_user, request.POST, request.FILES
        )
        if not errors:
            request.session["user_name"] = user.name
            return redirect("users:profile")
        edit_mode = True

    # Stats
    tools_listed  = Tool.objects.filter(owner=profile_user).count()
    rentals_done  = Booking.objects.filter(
        renter=profile_user, status='completed'
    ).count()
    reviews_received = Review.objects.filter(
        booking__tool__owner=profile_user
    ).select_related('reviewer').order_by('-created_at')
    reviews_given = Review.objects.filter(
        reviewer=profile_user
    ).select_related('booking__tool').order_by('-created_at')
    avg_rating    = profile_user.rating if profile_user.rating else None
    reviews_count = reviews_received.count()
    listed_tools  = Tool.objects.filter(
        owner=profile_user, is_available=True
    ).select_related('category')
    report_count  = Report.objects.filter(reported=profile_user).count()
    given_count   = reviews_given.count()

    context = {
        'profile_user'    : profile_user,
        'is_owner'        : is_owner,
        'session_user_id' : int(logged_in_id),
        'edit_mode'       : edit_mode,
        'errors'          : errors,
        'listed_tools'    : listed_tools,
        'reviews_received': reviews_received,
        'reviews_given'   : reviews_given,
        'given_count'     : given_count,
        'report_count'    : report_count,
        'stats': {
            'tools_listed' : tools_listed,
            'rentals_done' : rentals_done,
            'avg_rating'   : avg_rating,
            'reviews_count': reviews_count,
        },
    }
    return render(request, 'users/profile.html', context)


    
# ─────────────────────────────────────────────
#  Forgot Password
# ─────────────────────────────────────────────

def forgot_password_view(request):
    sent = False

    if request.method == "POST":
        sent = True  

    return render(request, "users/forgot_password.html", {"sent": sent})
# ─────────────────────────────────────────────
#  Public Profile View
# ─────────────────────────────────────────────

def public_profile_view(request, pk):
    viewer_id = request.session.get("user_id")
    if not viewer_id:
        return redirect("users:login")

    profile_user = get_object_or_404(User, pk=pk)

    primary_img_prefetch = Prefetch(
        "images",
        queryset=ToolImage.objects.filter(is_primary=True),
        to_attr="primary_images",
    )
    listed_tools = (
        Tool.objects
        .filter(owner=profile_user, is_available=True)
        .select_related("category")
        .prefetch_related(primary_img_prefetch)
        .order_by("-created_at")
    )

    reviews_received = (
        Review.objects
        .filter(
            Q(review_type=ReviewType.FOR_OWNER,  booking__tool__owner=profile_user) |
            Q(review_type=ReviewType.FOR_RENTER, booking__renter=profile_user)
        )
        .select_related("reviewer")
        .order_by("-created_at")
    )

    avg_data   = reviews_received.aggregate(avg=Avg("rating"))
    avg_rating = round(float(avg_data["avg"]), 1) if avg_data["avg"] else None

    tools_listed = Tool.objects.filter(owner=profile_user).count()
    rentals_done = Booking.objects.filter(
        renter=profile_user, status=BookingStatus.COMPLETED
    ).count()

    context = {
        "profile_user":     profile_user,
        "edit_mode":        False,
        "is_owner":         False,
        "errors":           {},
        "listed_tools":     listed_tools,
        "reviews_received": reviews_received,
        "reviews_given":    None,
        "given_count":      0,
        "stats": {
            "tools_listed":  tools_listed,
            "rentals_done":  rentals_done,
            "avg_rating":    avg_rating,
            "reviews_count": reviews_received.count(),
        },
    }
    return render(request, "users/profile.html", context)
