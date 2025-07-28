from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker
import random
from taskbird.models import Category, Priority, Status, Ticket, TicketComment, TicketAttachment, TicketEscalation

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates random tickets with associated data for testing purposes'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Number of tickets to create')

    def handle(self, *args, **kwargs):
        fake = Faker()
        count = kwargs['count']

        # Ensure some categories, priorities, and statuses exist
        categories = [
            Category.objects.get_or_create(name=name, defaults={'description': fake.sentence()})[0]
            for name in ['Technical', 'Billing', 'General', 'Account']
        ]
        
        priorities = [
            Priority.objects.get_or_create(
                name=name, 
                defaults={'level': level, 'description': fake.sentence()}
            )[0]
            for name, level in [('Low', 1), ('Medium', 2), ('High', 3), ('Urgent', 4)]
        ]
        
        statuses = [
            Status.objects.get_or_create(name=name, defaults={'description': fake.sentence()})[0]
            for name in ['Open', 'In Progress', 'Waiting', 'Resolved', 'Closed']
        ]

        # Get or create some users
        users = []
        for _ in range(max(5, count // 2)):  # Ensure enough users
            user = User.objects.filter(email=fake.email()).first()
            if not user:
                user = User.objects.create_user(
                    username=fake.user_name(),
                    email=fake.email(),
                    password='password123',
                    name = fake.name()
                )
            users.append(user)

        self.stdout.write(f"Creating {count} random tickets...")

        for _ in range(count):
            # Create ticket
            ticket = Ticket.objects.create(
                title=fake.sentence(nb_words=6),
                description=fake.paragraph(),
                customer=random.choice(users),
                agent=random.choice(users) if random.random() > 0.3 else None,
                category=random.choice(categories),
                priority=random.choice(priorities),
                status=random.choice(statuses),
                channel=random.choice(['FORM', 'CHAT']),
                created_at=fake.date_time_this_year(tzinfo=timezone.get_current_timezone()),
                is_active=random.choice([True, False]) if random.random() > 0.8 else True
            )

            # Add random comments (0-3 per ticket)
            for _ in range(random.randint(0, 3)):
                TicketComment.objects.create(
                    ticket=ticket,
                    user=random.choice(users),
                    content=fake.paragraph(),
                    created_at=fake.date_time_between(start_date=ticket.created_at, end_date='now', tzinfo=timezone.get_current_timezone()),
                    is_from_chatbot=random.choice([True, False])
                )

            # Add random attachments (0-2 per ticket)
            # for _ in range(random.randint(0, 2)):
            #     TicketAttachment.objects.create(
            #         ticket=ticket,
            #         file=f"ticket_attachments/{fake.file_name(category='document')}",
            #         uploaded_at=fake.date_time_between(start_date=ticket.created_at, end_date='now', tzinfo=timezone.get_current_timezone()),
            #         uploaded_by=random.choice(users)
            #     )

            # Add random escalations (0-1 per ticket)
            if random.random() > 0.7:
                TicketEscalation.objects.create(
                    ticket=ticket,
                    escalated_by=random.choice(users),
                    previous_agent=random.choice(users) if ticket.agent else None,
                    new_agent=random.choice(users) if random.random() > 0.5 else None,
                    previous_priority=ticket.priority,
                    new_priority=random.choice(priorities),
                    previous_status=ticket.status,
                    new_status=random.choice(statuses),
                    reason=fake.paragraph(),
                    escalated_at=fake.date_time_between(start_date=ticket.created_at, end_date='now', tzinfo=timezone.get_current_timezone())
                )

        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} random tickets'))