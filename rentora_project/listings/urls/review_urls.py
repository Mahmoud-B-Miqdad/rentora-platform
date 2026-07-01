from django.urls import path

from listings.views.review_views import submit_review_view

urlpatterns = [
    path('reviews/submit/<int:booking_id>/', submit_review_view, name='submit_review'),
]
