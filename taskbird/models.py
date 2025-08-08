from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Priority(models.Model):
    name = models.CharField(max_length=20, unique=True)
    level = models.IntegerField(unique=True)  # Higher number = higher priority
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Status(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Ticket(models.Model):
    CHANNEL_CHOICES = (
        ('FORM', 'Form'),
        ('CHAT', 'Live Chat'),
        ('OTHER', 'Other')
    )

    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, default=1)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, default=1)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='FORM')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            last_ticket = Ticket.objects.order_by('-id').first()
            new_id = f"TKT{1000 + (last_ticket.id + 1) if last_ticket else 1000}"
            self.ticket_id = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_id} - {self.title}"

class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_from_chatbot = models.BooleanField(default=False)  # For comments from live chat

    def __str__(self):
        return f"Comment by {self.user} on {self.ticket.ticket_id}"

class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='ticket_attachments/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Attachment for {self.ticket.ticket_id}"

class TicketEscalation(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='escalations')
    escalated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escalations_initiated')
    previous_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_tickets')
    new_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='new_tickets')
    previous_priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_priorities')
    new_priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, blank=True, related_name='new_priorities')
    previous_status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_statuses')
    new_status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True, related_name='new_statuses')
    reason = models.TextField()  # Reason for escalation or change
    escalated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Escalation for {self.ticket.ticket_id} by {self.escalated_by}"