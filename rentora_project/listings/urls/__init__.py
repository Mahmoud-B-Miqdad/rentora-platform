from django.urls import path
from listings.views.browse_views import home_view

app_name = 'listings'

urlpatterns = [
    path('', home_view, name='home'),
]