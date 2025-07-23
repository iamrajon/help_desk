from django.contrib import admin
from taskbird.models import Ticket, Category, Priority, Status





@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'description')

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'description',
        'customer',
        'agent',
        'category',
        'priority',
        'status',
        'channel',
        'is_active',
        'created_at'
    )

admin.site.register(Ticket, TicketAdmin)
