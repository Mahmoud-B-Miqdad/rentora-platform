from django.shortcuts import render, redirect
from listings.models.wishlist import Wishlist

def wishlist_view(request):
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('users:login') 
        
    wishlist_items = Wishlist.objects.filter(user_id=user_id).select_related('tool')

    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'listings/wishlist/wishlist.html', context)