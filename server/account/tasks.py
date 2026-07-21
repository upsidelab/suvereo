from celery import shared_task
from django.utils import timezone

from account.models import AuthToken


@shared_task
def clean_expired_auth_tokens():
    AuthToken.objects.filter(expires_at__lt=timezone.now()).delete()
