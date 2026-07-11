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
]
 
 