from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
 
from console.decorators import staff_required
from console.models import AdminAction
from listings.models import Category
 
 
@staff_required
def categories_manage(request):
    errors = {}
 
    if request.method == "POST":
        errors = Category.objects.register_validator(request.POST)
        if not errors:
            cat_id = request.POST.get("category_id")
            name = request.POST.get("name", "").strip()
            icon = request.POST.get("icon", "").strip()
 
            if cat_id:
                Category.objects.filter(id=cat_id).update(name=name, icon=icon)
                action_note = f'Updated category "{name}"'
            else:
                Category.objects.create(name=name, icon=icon)
                action_note = f'Created category "{name}"'
 
            AdminAction.objects.create(
                staff=request.staff_user, action="category_change",
                reason=action_note,
            )
            messages.success(request, action_note + ".")
            return redirect("console:categories")
 
    categories = Category.objects.annotate(tools_count=Count("tools")).order_by("name")
 
    return render(request, "console/categories.html", {
        "active_tab": "categories",
        "categories": categories,
        "errors": errors,
    })