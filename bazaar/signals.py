from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from .models import RegistrationLog


@receiver(post_save, sender=User)
def create_account(sender, instance, created, **kwargs):
    if created:
        RegistrationLog.objects.create(user=instance)