from django.shortcuts import render, redirect
from django.contrib    import messages
from users.models      import User


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

        User.objects.create_user(request.POST)
        messages.success(request, "Account created successfully! Please sign in.")
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