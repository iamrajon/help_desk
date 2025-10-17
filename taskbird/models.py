
"""

New Code for models.py
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
from taskbird.algorithms import PriorityScoring, RoundRobinAssignment, ResponseTimePredictor


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
    
    class Meta:
        verbose_name_plural = "Priorities"  # ADDED: Proper plural name


class Status(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Statuses"  # ADDED: Proper plural name


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
    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, blank=True)  # CHANGED: removed default=1
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True)  # CHANGED: removed default=1
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='FORM')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # NEW FIELD: Store calculated priority score (optional but recommended)
    priority_score = models.IntegerField(default=0, help_text="Auto-calculated priority score (0-100)")
    
    # NEW FIELD: Store estimated resolution time (optional but recommended)
    estimated_resolution_hours = models.FloatField(null=True, blank=True, 
                                                     help_text="Predicted resolution time in hours")

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            last_ticket = Ticket.objects.order_by('-id').first()
            new_id = f"TKT{1000 + (last_ticket.id + 1) if last_ticket else 1000}"
            self.ticket_id = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_id} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']  # ADDED: Default ordering by newest first


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_from_chatbot = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment by {self.user} on {self.ticket.ticket_id}"
    
    class Meta:
        ordering = ['created_at']  # ADDED: Order comments chronologically


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
    reason = models.TextField()
    escalated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Escalation for {self.ticket.ticket_id} by {self.escalated_by}"
    
    class Meta:
        ordering = ['-escalated_at']  # ADDED: Order by most recent


# class TicketSession(models.Model):
#     session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
#     title = models.CharField(max_length=255)
#     description = models.TextField()
#     customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_sessions')
#     category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
#     priority = models.ForeignKey('Priority', on_delete=models.SET_NULL, null=True, blank=True)
#     channel = models.CharField(max_length=50, choices=[('CHAT', 'Chat'), ('FORM', 'Form'), ('OTHER', 'Other')])
#     session_status = models.CharField(max_length=50, choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('REJECTED', 'Rejected')], default='PENDING')
#     reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_sessions')
#     rejection_reason = models.TextField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     reviewed_at = models.DateTimeField(null=True, blank=True)
#     created_ticket = models.ForeignKey('Ticket', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_session')

#     def accept_and_create_ticket(self, agent):
#         """
#         Accept the session and create a Ticket, applying algorithms for assignment and priority.
#         """
#         if self.session_status != 'PENDING':
#             raise ValueError("Session is not pending.")
        
#         # Create a new Ticket instance
#         from .models import Ticket, Priority, Status
#         ticket = Ticket.objects.create(
#             ticket_id=f"TICKET-{self.session_id}",  # Example ticket_id format
#             title=self.title,
#             description=self.description,
#             customer=self.customer,
#             category=self.category,
#             priority=self.priority or Priority.objects.filter(name='Medium').first(),  # Default priority if none
#             status=Status.objects.filter(name='Open').first(),  # Default status
#             is_active=True
#         )

#         # Apply RoundRobinAssignment algorithm to assign the ticket
#         assigned_agent = RoundRobinAssignment.assign_ticket(ticket)
#         if not assigned_agent:
#             # Handle case where no agents are available
#             ticket.agent = None  # Or assign to a default admin user
#             ticket.save()

#         # Update session
#         self.session_status = 'ACCEPTED'
#         self.reviewed_by = agent
#         self.reviewed_at = timezone.now()
#         self.created_ticket = ticket
#         self.save()

#         return ticket

#     def reject_session(self, agent, reason):
#         """
#         Reject the session with a reason.
#         """
#         if self.session_status != 'PENDING':
#             raise ValueError("Session is not pending.")
        
#         self.session_status = 'REJECTED'
#         self.reviewed_by = agent
#         self.reviewed_at = timezone.now()
#         self.rejection_reason = reason
#         self.save()


class TicketSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_sessions')
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.ForeignKey('Priority', on_delete=models.SET_NULL, null=True, blank=True)
    channel = models.CharField(max_length=50, choices=[('CHAT', 'Chat'), ('FORM', 'Form'), ('OTHER', 'Other')])
    session_status = models.CharField(max_length=50, choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('REJECTED', 'Rejected')], default='PENDING')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_sessions')
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_ticket = models.ForeignKey('Ticket', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_session')

    def accept_and_create_ticket(self, agent):
        """
        Accept the session and create a Ticket, applying algorithms for assignment and priority.
        """
        if self.session_status != 'PENDING':
            raise ValueError("Session is not pending.")
        
        # Create a new Ticket instance
        from .models import Ticket, Priority, Status
        ticket = Ticket.objects.create(
            ticket_id=f"TICKET-{self.session_id}",  # Example ticket_id format
            title=self.title,
            description=self.description,
            customer=self.customer,
            category=self.category,
            priority=self.priority or Priority.objects.filter(name='Medium').first(),  # Default priority if none
            status=Status.objects.filter(name='Open').first(),  # Default status
            is_active=True
        )

        # Apply RoundRobinAssignment algorithm to assign the ticket
        assigned_agent = RoundRobinAssignment.assign_ticket(ticket)
        if not assigned_agent:
            # Handle case where no agents are available
            ticket.agent = None  # Or assign to a default admin user
            ticket.save()

        # Update session
        self.session_status = 'ACCEPTED'
        self.reviewed_by = agent
        self.reviewed_at = timezone.now()
        self.created_ticket = ticket
        self.save()

        return ticket

    def reject_session(self, agent, reason):
        """
        Reject the session with a reason.
        """
        if self.session_status != 'PENDING':
            raise ValueError("Session is not pending.")
        
        self.session_status = 'REJECTED'
        self.reviewed_by = agent
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class TicketSessionAttachment(models.Model):
    """Attachments uploaded with ticket session requests"""
    session = models.ForeignKey(TicketSession, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='session_attachments/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Attachment for {self.session.session_id}"