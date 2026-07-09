from django.contrib import admin

from listings.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display  = ('reporter', 'reported', 'reason', 'created_at')
    list_filter   = ('reason', 'created_at')
    search_fields = ('reporter__name', 'reporter__email',
                     'reported__name', 'reported__email', 'details')
    readonly_fields = ('reporter', 'reported', 'reason', 'details', 'created_at')
    date_hierarchy = 'created_at'
