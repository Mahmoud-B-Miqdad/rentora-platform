from django.urls import path
from users import views

app_name = "users"

urlpatterns = [
    path("register/",                      views.register_view,          name="register"),
    path("login/",                         views.login_view,             name="login"),
    path("logout/",                        views.logout_view,            name="logout"),
    path("profile/",                       views.profile_view,           name="profile"),
    path("profile/<int:pk>/",              views.public_profile_view,    name="public_profile"),
    path("verify-email/<str:token>/",      views.verify_email_view,      name="verify_email"),
    path("resend-verification/",           views.resend_verification_view, name="resend_verification"),
]