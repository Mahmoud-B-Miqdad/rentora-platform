from django.urls import path
from listings.views import legal_views

urlpatterns = [
    path("terms/",           legal_views.terms_of_service, name="terms"),
    path("privacy/",         legal_views.privacy_policy,   name="privacy"),
    path("faq/",             legal_views.faq,               name="faq"),
    path("contact/",         legal_views.contact,           name="contact"),
    path("my-messages/",     legal_views.my_messages,       name="my_messages"),
]
