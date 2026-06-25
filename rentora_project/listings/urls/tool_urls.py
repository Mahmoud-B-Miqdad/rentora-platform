from django.urls import path

from listings.views.tool_views import tool_detail_view

urlpatterns = [
    path('tools/<int:pk>/', tool_detail_view, name='detail'),
]
