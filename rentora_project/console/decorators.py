from functools import wraps
 
from django.http import Http404
from django.shortcuts import redirect
 
from users.models import User
 
 
def staff_required(view_func):
    """Session-auth guard for the staff console.
 
    Non-staff users get a 404 (not 403) so the console's existence
    is never revealed to regular accounts.
    """
 
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get("user_id")
        if not user_id:
            return redirect("users:login")
 
        user = User.objects.filter(id=user_id, is_staff=True, is_active=True).first()
        if user is None:
            raise Http404()
 
        request.staff_user = user
        return view_func(request, *args, **kwargs)
 
    return wrapper