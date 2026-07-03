from django.urls import include, path

app_name = 'listings'

urlpatterns = [
    path('', include('listings.urls.browse_urls')),
    path('', include('listings.urls.tool_urls')),
    path('', include('listings.urls.booking_urls')),
    path('', include('listings.urls.review_urls')),
    path('', include('listings.urls.wishlist_urls')),
    path('', include('listings.urls.notification_urls')),
]
