from django.urls import path
from users import views
from django.contrib.auth import views as auth_views


app_name = "users"

urlpatterns = [
    path("register/",                      views.register_view,          name="register"),
    path("login/",                         views.login_view,             name="login"),
    path("logout/",                        views.logout_view,            name="logout"),
    path("profile/",                       views.profile_view,           name="profile"),
    path("profile/<int:user_id>/",         views.profile_view,           name="profile_user"),
    # Alias: legacy name used by links across the site — same page as profile_user.
    path("profile/<int:user_id>/",         views.profile_view,           name="public_profile"),
    path("verify-email/<str:token>/",      views.verify_email_view,      name="verify_email"),
    path("resend-verification/",           views.resend_verification_view, name="resend_verification"),
    
    path("forgot-password/", auth_views.PasswordResetView.as_view(
        template_name="users/password/forgot_password.html",
        email_template_name="users/emails/password_reset_email.html", 
        success_url="/users/password-reset/done/"
    ), name="forgot_password"),

    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="users/password/password_reset_done.html"
    ), name="password_reset_done"),

    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="users/password/password_reset_confirm.html",
        success_url="/users/reset/done/"
    ), name="password_reset_confirm"),

    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="users/password/password_reset_complete.html"
    ), name="password_reset_complete"),
    
]