# urls.py
from django.urls import path
from django.http import JsonResponse
from webhooks.views import prism_webhook

def health(_):
    return JsonResponse({"ok": True, "service": "prism-webhook-listener"}, status=200)

urlpatterns = [
    path("api/prism/", prism_webhook, name="prism-webhook"),
    path("health", health),  # GET-friendly
]