from django.urls import include, path

app_name = 'listings'

urlpatterns = [
    path('', include('listings.urls.browse_urls')),
    path('', include('listings.urls.tool_urls')),
    path('', include('listings.urls.booking_urls')),
]
