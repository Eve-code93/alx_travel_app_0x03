from rest_framework import viewsets
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer
import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Payment
from rest_framework import viewsets
from .models import Booking
from .serializers import BookingSerializer
from .tasks import send_booking_confirmation

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save()
        # Trigger Celery task asynchronously
        send_booking_confirmation.delay(booking.user.email, booking.id)

CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")
CHAPA_BASE_URL = "https://api.chapa.co/v1"

@csrf_exempt
def initiate_payment(request):
    """
    Initiates a payment request with Chapa.
    """
    if request.method == "POST":
        data = request.POST
        amount = data.get("amount")
        booking_reference = data.get("booking_reference")
        email = data.get("email")

        headers = {
            "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
        }

        payload = {
            "amount": amount,
            "currency": "ETB",
            "email": email,
            "tx_ref": booking_reference,
            "callback_url": "http://localhost:8000/api/verify-payment/"
        }

        response = requests.post(f"{CHAPA_BASE_URL}/transaction/initialize",
                                 headers=headers, json=payload)

        res_data = response.json()

        if res_data.get("status") == "success":
            Payment.objects.create(
                booking_reference=booking_reference,
                amount=amount,
                transaction_id=res_data["data"]["tx_ref"],
                status="Pending"
            )
            return JsonResponse({"checkout_url": res_data["data"]["checkout_url"]})

        return JsonResponse({"error": res_data}, status=400)

@csrf_exempt
def verify_payment(request):
    """
    Verifies payment status from Chapa.
    """
    if request.method == "GET":
        tx_ref = request.GET.get("tx_ref")

        headers = {
            "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
        }

        response = requests.get(f"{CHAPA_BASE_URL}/transaction/verify/{tx_ref}",
                                headers=headers)

        res_data = response.json()

        try:
            payment = Payment.objects.get(transaction_id=tx_ref)
        except Payment.DoesNotExist:
            return JsonResponse({"error": "Payment not found"}, status=404)

        if res_data.get("status") == "success":
            payment.status = "Completed"
            payment.save()
            # TODO: trigger Celery task to send confirmation email
        else:
            payment.status = "Failed"
            payment.save()

        return JsonResponse(res_data)


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
