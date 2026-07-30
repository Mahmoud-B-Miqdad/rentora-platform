from django.contrib import admin

from listings.models import Report, PaymentBreakdown, DepositDispute, ContactMessage


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display  = ('reporter', 'reported', 'reason', 'created_at')
    list_filter   = ('reason', 'created_at')
    search_fields = ('reporter__name', 'reporter__email',
                     'reported__name', 'reported__email', 'details')
    readonly_fields = ('reporter', 'reported', 'reason', 'details', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(PaymentBreakdown)
class PaymentBreakdownAdmin(admin.ModelAdmin):
    list_display  = ('id', 'booking', 'rental_total', 'platform_fee', 'total_charged_to_renter', 'owner_payout', 'created_at')
    list_filter   = ('created_at', 'insurance_opted')
    search_fields = ('booking__id', 'booking__renter__name', 'booking__tool__title')
    readonly_fields = ('booking', 'rental_total', 'platform_fee', 'insurance_fee', 'total_charged_to_renter', 'owner_payout', 'stripe_fee', 'net_platform_revenue', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(DepositDispute)
class DepositDisputeAdmin(admin.ModelAdmin):
    list_display  = ('id', 'booking', 'initiated_by', 'status', 'resolved_at')
    list_filter   = ('status', 'created_at', 'initiated_by')
    search_fields = ('booking__id', 'booking__renter__name', 'booking__tool__owner__name', 'reason')
    readonly_fields = ('booking', 'deposit_amount', 'created_at', 'updated_at')
    fieldsets = (
        ('Dispute Info', {'fields': ('booking', 'initiated_by', 'reason', 'status', 'deposit_amount')}),
        ('Evidence', {'fields': ('dispute_evidence', 'owner_response', 'renter_response')}),
        ('Resolution', {'fields': ('staff_decision', 'staff_notes', 'refund_amount', 'claim_amount', 'resolved_by', 'resolved_at')}),
        ('Metadata', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    date_hierarchy = 'created_at'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'category', 'status', 'created_at')
    list_filter   = ('status', 'category', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Sender Info', {'fields': ('name', 'email', 'user')}),
        ('Message', {'fields': ('subject', 'category', 'message')}),
        ('Status & Response', {'fields': ('status', 'assigned_to', 'staff_response', 'resolved_at')}),
        ('Metadata', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    date_hierarchy = 'created_at'
