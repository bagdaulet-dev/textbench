from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.utils import timezone

from text_tools.models import TextAnalysis


class Command(BaseCommand):
    help = "Delete analyses whose browser sessions no longer exist or have expired."

    def handle(self, *args, **options):
        active_sessions = Session.objects.filter(expire_date__gt=timezone.now()).values(
            "session_key"
        )
        count, _ = TextAnalysis.objects.exclude(session_key__in=active_sessions).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} expired analyses."))
