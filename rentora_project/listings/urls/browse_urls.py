from django.urls import path

from listings.views.browse_views import home_view

urlpatterns = [
    path('', home_view, name='home'),
]
