from django.urls import path

from listings.views.browse_views import home_view, browse_view, about_view, smart_search_view

urlpatterns = [
    path('',              home_view,         name='home'),
    path('browse/',       browse_view,       name='browse'),
    path('about/',        about_view,        name='about'),
    path('smart-search/', smart_search_view, name='smart_search'),
]
