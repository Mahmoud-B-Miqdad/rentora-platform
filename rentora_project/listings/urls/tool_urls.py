from django.urls import path
from listings.views.tool_views import (
    tool_detail_view,
    toggle_wishlist_view,
    add_tool_view,
    my_tools_view,
    edit_tool_view,
    delete_tool_view,
)

app_name = "tools"

urlpatterns = [
    path("add/", add_tool_view, name="add_tool"),
    path("my-tools/", my_tools_view, name="my_tools"),

    path('<int:pk>/', tool_detail_view, name='detail'),
    path('<int:pk>/wishlist/', toggle_wishlist_view, name='toggle_wishlist'),
    path("<int:tool_id>/edit/", edit_tool_view, name="edit_tool"),
    path("<int:tool_id>/delete/", delete_tool_view, name="delete_tool"),
]