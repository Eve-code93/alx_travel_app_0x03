from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_booking_confirmation(email, booking_id):
    subject = "Booking Confirmation"
    message = f"Thank you for your booking. Your booking ID is {booking_id}."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)
    return f"Booking confirmation sent to {email}"
