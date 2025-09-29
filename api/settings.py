import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Django's own secret (framework crypto). Set in env for prod.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = ["*", ".vercel.app"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "webhooks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "api.urls"

# Prism webhook config (env-driven)
PRISM_WEBHOOK_SECRET = os.getenv("PRISM_WEBHOOK_SECRET", "")
PRISM_WEBHOOK_VERIFY = os.getenv("PRISM_WEBHOOK_VERIFY", "true")
PRISM_WEBHOOK_SKEW_SECONDS = int(os.getenv("PRISM_WEBHOOK_SKEW_SECONDS", "300"))

# Vercel's Python runtime expects 'app' in wsgi.py
WSGI_APPLICATION = "api.wsgi.app"
