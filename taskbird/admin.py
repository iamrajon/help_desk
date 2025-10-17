from django.contrib import admin
from taskbird.models import (
    Ticket,
    Category,
    Priority,
    Status,
    TicketComment,
    TicketAttachment,
    TicketEscalation,
    TicketSession,
    TicketSessionAttachment
)


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




@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'created_at', 'is_from_chatbot')
    search_fields = ('ticket__ticket_id', 'user__username', 'content')
    list_filter = ('is_from_chatbot', 'created_at')
    ordering = ('-created_at',)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'file', 'uploaded_by', 'uploaded_at')
    search_fields = ('ticket__ticket_id', 'uploaded_by__username')
    list_filter = ('uploaded_at',)
    ordering = ('-uploaded_at',)


@admin.register(TicketEscalation)
class TicketEscalationAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'escalated_by', 'previous_agent', 'new_agent', 'escalated_at')
    search_fields = ('ticket__ticket_id', 'escalated_by__username')
    list_filter = ('escalated_at',)
    ordering = ('-escalated_at',)


@admin.register(TicketSession)
class TicketSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'title', 'customer', 'session_status', 'created_at', 'reviewed_by')
    search_fields = ('session_id', 'title', 'customer__username')
    list_filter = ('session_status', 'created_at')
    ordering = ('-created_at',)


@admin.register(TicketSessionAttachment)
class TicketSessionAttachmentAdmin(admin.ModelAdmin):
    list_display = ('session', 'file', 'uploaded_by', 'uploaded_at')
    search_fields = ('session__session_id', 'uploaded_by__username')
    list_filter = ('uploaded_at',)
    ordering = ('-uploaded_at',)

