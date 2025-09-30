from django.urls import path
from webhooks.views import prism_webhook

urlpatterns = [
    path("api/prism/", prism_webhook, name="prism-webhook"),
]
