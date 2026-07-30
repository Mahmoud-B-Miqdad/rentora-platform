from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from listings.models import ContactMessage
from listings.services.email_service import send_support_confirmation_email


@require_http_methods(["GET"])
def terms_of_service(request):
    """Terms of Service page (static)"""
    return render(request, 'listings/legal/terms_of_service.html')


@require_http_methods(["GET"])
def privacy_policy(request):
    """Privacy Policy page (static)"""
    return render(request, 'listings/legal/privacy_policy.html')


@require_http_methods(["GET"])
def faq(request):
    """FAQ page with expandable sections"""
    return render(request, 'listings/legal/faq.html')


@require_http_methods(["GET", "POST"])
def contact(request):
    """Support/Contact form"""

    if request.method == "GET":
        return render(request, 'listings/legal/contact.html')

    # POST: Process contact form
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    subject = request.POST.get('subject', '').strip()
    category = request.POST.get('category', 'other')
    message_text = request.POST.get('message', '').strip()

    # Validation
    errors = {}
    if not name or len(name) < 2:
        errors['name'] = _('Please enter a valid name.')
    if not email or '@' not in email:
        errors['email'] = _('Please enter a valid email address.')
    if not subject or len(subject) < 5:
        errors['subject'] = _('Subject must be at least 5 characters.')
    if not message_text or len(message_text) < 10:
        errors['message'] = _('Message must be at least 10 characters.')

    if errors:
        return render(request, 'listings/legal/contact.html', {
            'errors': errors,
            'form_data': request.POST,
        })

    # Link the ticket to the sender's account when logged in. This project
    # uses custom session auth (request.session["user_id"]), NOT request.user,
    # so resolve the User from the session id.
    sender = None
    session_user_id = request.session.get("user_id")
    if session_user_id:
        from users.models import User
        sender = User.objects.filter(pk=session_user_id).first()

    # Optional evidence attachment (image, screenshot, or document).
    attachment = request.FILES.get('attachment')
    if attachment and attachment.size > 10 * 1024 * 1024:
        return render(request, 'listings/legal/contact.html', {
            'errors': {'attachment': _('The attachment must be under 10 MB.')},
            'form_data': request.POST,
        })

    # Save contact message
    contact_msg = ContactMessage.objects.create(
        name=name,
        email=email,
        subject=subject,
        category=category,
        message=message_text,
        attachment=attachment,
        user=sender,
    )

    # Send confirmation email
    send_support_confirmation_email(contact_msg)

    # Show success and redirect
    messages.success(request, _('Thank you! We received your message. We\'ll respond within 24 hours.'))
    return redirect('listings:contact')


@require_http_methods(["GET"])
def my_messages(request):
    """Logged-in user's own support tickets and the staff replies."""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("users:login")

    from users.models import User
    user = get_object_or_404(User, pk=user_id)
    tickets = ContactMessage.objects.filter(user=user).order_by("-created_at")
    return render(request, "listings/legal/my_messages.html", {"tickets": tickets})
