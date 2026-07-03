from django.urls import path
from listings.views.notification_views import (
    notifications_json,
    mark_notification_read,
    mark_all_read,
    unread_count,
)

urlpatterns = [
    path('notifications/',                          notifications_json,       name='notifications_json'),
    path('notifications/unread/',                   unread_count,             name='notifications_unread'),
    path('notifications/mark-all-read/',            mark_all_read,            name='notifications_mark_all_read'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='notifications_mark_read'),
]
