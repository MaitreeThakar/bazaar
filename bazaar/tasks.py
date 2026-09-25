from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_welcome_email(email,username):
    send_mail(
        subject = "Welcome to Bazaar",
        message = f"Hello {username}, welcome to Bazaar!",
        from_email=None,
        recipient_list=[email],
    )