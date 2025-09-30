A minimal Django service that **receives and verifies Prism webhooks**.  
It validates the timestamp + HMAC signature, parses the JSON, and returns `200` quickly so Prism doesn’t retry.

> Live endpoint path (after deploy):  
> **`/api/prism/`** (note the trailing slash)

---

## Features

- ✅ **HMAC verification** with Prism’s `prism-signature` header  
- ⏱️ **Replay protection** using `prism-timestamp` (default skew = 5 minutes)  
- 🛡️ **Constant-time compare** for signatures
- 📦 **Minimal payload validation** (forward-compatible)  
- ⚡ **Fast ack** — do heavy work async
- 🫀 Small **health check** endpoint  
- ☁️ Deployable on **Vercel** with zero ops

---

## Repository Layout
```bash
prism-webhook-listener-django/
│
├─ api/
│ ├─ settings.py # env-driven config
│ ├─ urls.py # routes /api/prism/
│ └─ wsgi.py # exposes 'app' for Vercel
│
├─ webhooks/
│ └─ views.py # webhook endpoint
│
├─ manage.py
├─ requirements.txt
└─ vercel.json # routes all requests to Django WSGI
```

---

## Environment Variables

Set these both **locally** and in Vercel:

| Variable                  | Purpose                                    |
|----------------------------|--------------------------------------------|
| `DJANGO_SECRET_KEY`        | Django’s own crypto key (any long string)  |
| `PRISM_WEBHOOK_SECRET`     | Shared secret from Prism (for HMAC)        |
| `PRISM_WEBHOOK_VERIFY`     | `true` (default) or `false` in dev         |
| `PRISM_WEBHOOK_SKEW_SECONDS` | Allowed timestamp skew (default `300`)   |

---

## Local Development

### 1. Create virtualenv and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set environment variables
```bash
export DJANGO_SECRET_KEY="dev-123"
export PRISM_WEBHOOK_SECRET="whsec_test_1234567890"
export PRISM_WEBHOOK_VERIFY=true
export PRISM_WEBHOOK_SKEW_SECONDS=300
```

### 3. Run server locally
```bash
python manage.py runserver 0.0.0.0:8000
```

## Local Test

```bash
URL="http://127.0.0.1:8000/api/prism/"
SECRET="whsec_test_1234567890"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BODY='{"eventType":"scan.processing.succeeded","payload":{"scanId":"scan_11111111-2222-3333-4444-555555555555","userId":"user_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee","userToken":"partner_user_token_123","state":"READY"}}'
SIG=$(printf "%s.%s" "$TIMESTAMP" "$BODY" | \\
  openssl dgst -sha256 -hmac "$SECRET" -r | awk '{print $1}')

curl -i -X POST "$URL" \\
  -H "Content-Type: application/json" \\
  -H "prism-timestamp: $TIMESTAMP" \\
  -H "prism-signature: $SIG" \\
  -d "$BODY"
```

Expected: HTTP/1.1 200 OK with {"ok": true}.

## Deploy to Vercel or equivalent

If you want to quickly deploy this code to Vercel or equivalent follow the instructions below. This repo already includes the edits and files described below.

### 1. Push repo to GitHub/GitLab/Bitbucket

Make sure the repo has:
- requirements.txt with Django
- vercel.json (see below)
- api/wsgi.py exposing app

### 2. Import project in Vercel

- Go to Vercel dashboard → New Project → Import repo.
- Framework preset: Python.

### 3. Add environment variables in Vercel

- DJANGO_SECRET_KEY
- PRISM_WEBHOOK_SECRET
- PRISM_WEBHOOK_VERIFY
- PRISM_WEBHOOK_SKEW_SECONDS

### 4. Make sure to add vercel.json

```bash
{
  "builds": [
    { "src": "api/wsgi.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "api/wsgi.py" }
  ]
}
```

### 5. Add this code to wsgi.py

```bash
# api/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")
app = get_wsgi_application()  # Vercel expects 'app'
```

### 6. Deploy 🚀

Once deployed, your webhook URL will be: ```https://<your-project>.vercel.app/api/prism/```

### 7. Deployed Test Example

Run the following on the terminal:

```bash
URL="https://<your-project>.vercel.app/api/prism/"
SECRET="<same as PRISM_WEBHOOK_SECRET in Vercel>"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BODY='{"eventType":"scan.processing.succeeded","payload":{"scanId":"scan_11111111-2222-3333-4444-555555555555","userId":"user_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee","userToken":"partner_user_token_123","state":"READY"}}'
SIG=$(printf "%s.%s" "$TIMESTAMP" "$BODY" | \\
  openssl dgst -sha256 -hmac "$SECRET" -r | awk '{print $1}')

curl -i -X POST "$URL" \\
  -H "Content-Type: application/json" \\
  -H "prism-timestamp: $TIMESTAMP" \\
  -H "prism-signature: $SIG" \\
  -d "$BODY"
```

### Troubleshooting

- 404 on Vercel → check vercel.json routes + wsgi.py exposes app.
- 301 locally → add trailing slash (/api/prism/) or curl -L.
- invalid-signature → Secret mismatch, body altered, or wrong timestamp in signature.
- stale-or-bad-timestamp → Event older than allowed skew. Fix system clock or raise PRISM_WEBHOOK_SKEW_SECONDS.
- minimal payload validation is done for:
    - Top-level shape: { eventType: string, payload: object }
    - eventType ∈ { scan.processing.started|succeeded|failed, body_shape_prediction.processing.started|succeeded|failed }
    - Scan payload: scanId, userId, userToken are non-empty strings; state ∈ { CREATED, PROCESSING, READY, FAILED }
    - Future Me payload: bodyShapePredictionId, scanId, userId, userToken are non-empty strings; state ∈ { PROCESSING, READY, FAILED }
    - Accept unknown/extra fields (don’t fail on them)
- Check health of endpoint with ```curl -i http://127.0.0.1:8000/health```

Logs:
- Local: terminal where you runserver
- Vercel: Project → Deployments → Functions → Logs