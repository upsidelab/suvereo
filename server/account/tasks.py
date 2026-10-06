from celery import shared_task
from django.core.management import call_command


@shared_task
def flush_expired_tokens():
    """Remove expired refresh tokens from the outstanding and blacklist tables."""
    call_command("flushexpiredtokens")
