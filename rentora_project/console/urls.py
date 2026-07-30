from django.urls import path
 
from console import views
 
app_name = "console"
 
urlpatterns = [
    path("",                                  views.overview,               name="overview"),
    path("reports/",                          views.reports_queue,          name="reports"),
    path("users/",                            views.users_list,             name="users"),
    path("users/<int:user_id>/",              views.user_detail,            name="user_detail"),
    path("users/<int:user_id>/action/",       views.user_action,            name="user_action"),
    path("bookings/",                         views.bookings_monitor,       name="bookings"),
    path("returns/",                          views.returns_queue,          name="returns"),
    path("returns/<int:booking_id>/close/",   views.booking_force_complete, name="force_complete"),
    path("categories/",                       views.categories_manage,      name="categories"),
    path("disputes/<int:dispute_id>/",        views.dispute_detail,         name="dispute_detail"),
    path("disputes/<int:dispute_id>/resolve/", views.dispute_resolve,       name="dispute_resolve"),
    path("disputes/<int:dispute_id>/owner-reply/", views.dispute_request_owner_reply, name="dispute_owner_reply"),
    path("support/",                          views.support_queue,          name="support"),
    path("support/<int:message_id>/",         views.support_detail,         name="support_detail"),
    path("support/<int:message_id>/action/",  views.support_action,         name="support_action"),
]
 
 