from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
import random

from .models import Notification

def send_sms_verification(user):

    code = str(random.randint(100000, 999999))
    user.phone_verification_code = code
    user.code_created_at = timezone.now()
    user.save()

    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    message = client.messages.create(
        body=f"your verification code is: {code}. This code will expire in 10 minutes. \n\n -BITGE (Ben Is The Greatest Ever)",
        from_=settings.TWILIO_PHONE_NUMBER,
        to=user.phone_number
    )

    return message.sid



def create_notification(recipient, sender, notification_type, post=None, comment=None):

    if recipient == sender:
        return None
    
    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        post=post,
        comment=comment
    )