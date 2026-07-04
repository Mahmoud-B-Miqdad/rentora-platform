from django.urls import path
from listings.views.chat_views import chat_view, send_message_view, poll_messages_view

urlpatterns = [
    path("chat/<int:booking_id>/",        chat_view,          name="chat"),
    path("chat/<int:booking_id>/send/",   send_message_view,  name="chat_send"),
    path("chat/<int:booking_id>/poll/",   poll_messages_view, name="chat_poll"),
]
