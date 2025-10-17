import random
import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from taskbird.models import TicketSession, Category, Priority
from django.contrib.auth import get_user_model

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = "Create fake TicketSession records for testing (only for customer users)."

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Number of fake TicketSessions to create.')

    def handle(self, *args, **options):
        count = options['count']

        # Get only customer users
        customers = list(User.objects.filter(user_type=User.UserType.CUSTOMER))
        categories = list(Category.objects.all())
        priorities = list(Priority.objects.all())

        if not customers:
            self.stdout.write(self.style.ERROR('❌ No customers found. Please create at least one customer first.'))
            return

        created_sessions = []

        for _ in range(count):
            customer = random.choice(customers)
            priority = random.choice(priorities) if priorities else None

            session = TicketSession.objects.create(
                session_id=uuid.uuid4(),
                title=fake.sentence(nb_words=6),
                description=fake.paragraph(nb_sentences=3),
                customer=customer,
                category=None,  # ✅ keep category null
                priority=priority,
                channel=random.choice(['FORM', 'CHAT', 'OTHER']),
                session_status='PENDING',  # ✅ all sessions are pending
                reviewed_by=None,  # ✅ null
                rejection_reason=None,  # ✅ empty
                created_at=fake.date_time_between(start_date='-10d', end_date='now', tzinfo=timezone.get_current_timezone()),
                reviewed_at=None,  # ✅ null
            )

            created_sessions.append(session)

        self.stdout.write(self.style.SUCCESS(f'✅ Successfully created {len(created_sessions)} fake TicketSessions (PENDING).'))


# command ----> python manage.py crteate_sessions 30