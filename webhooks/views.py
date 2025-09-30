# webhooks/views.py
import hmac, hashlib, json
from datetime import datetime, timezone
from django.conf import settings
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from hmac import compare_digest

def _within_skew(ts_iso: str, skew_seconds: int) -> bool:
    try:
        sent = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    except Exception:
        return False
    now = datetime.now(timezone.utc)
    return abs((now - sent).total_seconds()) <= skew_seconds

ALLOWED_EVENTS = {
    "scan.processing.started",
    "scan.processing.succeeded",
    "scan.processing.failed",
    "body_shape_prediction.processing.started",
    "body_shape_prediction.processing.succeeded",
    "body_shape_prediction.processing.failed",
}
SCAN_STATES = {
    "CREATED",
    "PROCESSING",
    "READY",
    "FAILED"
}

FM_STATES   = {
    "PROCESSING",
    "READY",
    "FAILED"
}

def _req_str(obj, key): 
    return isinstance(obj.get(key), str) and obj[key].strip() != ""

def validate_minimal(event: dict) -> tuple[bool, str]:
    if not isinstance(event, dict): return False, "body-must-be-object"
    et = event.get("eventType")
    payload = event.get("payload")
    if et not in ALLOWED_EVENTS: return False, "unknown-eventType"
    if not isinstance(payload, dict): return False, "payload-must-be-object"

    if et.startswith("scan."):
        if not (_req_str(payload, "scanId") and _req_str(payload, "userId") and _req_str(payload, "userToken")):
            return False, "missing-scan-fields"
        if payload.get("state") not in SCAN_STATES:
            return False, "invalid-scan-state"
        return True, ""
    else:
        if not (_req_str(payload, "bodyShapePredictionId") and _req_str(payload, "scanId")
                and _req_str(payload, "userId") and _req_str(payload, "userToken")):
            return False, "missing-fm-fields"
        if payload.get("state") not in FM_STATES:
            return False, "invalid-fm-state"
        return True, ""

@csrf_exempt
def prism_webhook(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # 1) Read headers + RAW body (exact bytes)
    timestamp = request.headers.get("prism-timestamp", "")
    given_sig = request.headers.get("prism-signature", "")
    raw_body_bytes = request.body
    raw_body_str = raw_body_bytes.decode("utf-8")

    # Optional: allow skipping verification in dev
    verify = str(getattr(settings, "PRISM_WEBHOOK_VERIFY", "true")).lower() != "false"
    if not verify:
        try:
            event = json.loads(raw_body_str)
        except Exception as e:
            return JsonResponse({"ok": False, "error": "invalid-json", "detail": str(e)}, status=400)
        print("📥 (DEV) Prism webhook:", event.get("eventType"))
        return JsonResponse({"ok": True, "dev": True}, status=200)

    # 2) Timestamp window (default 5 min)
    skew = int(getattr(settings, "PRISM_WEBHOOK_SKEW_SECONDS", 300))
    if not _within_skew(timestamp, skew):
        return JsonResponse({"ok": False, "error": "stale-or-bad-timestamp"}, status=400)

    # 3) Verify HMAC signature
    secret = getattr(settings, "PRISM_WEBHOOK_SECRET", "")
    if not secret:
        return JsonResponse({"ok": False, "error": "missing-server-secret"}, status=500)

    signature_content = f"{timestamp}.{raw_body_str}".encode("utf-8")
    expected_sig = hmac.new(
        key=secret.encode("utf-8"),
        msg=signature_content,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not given_sig or not compare_digest(given_sig, expected_sig):
        return JsonResponse({"ok": False, "error": "invalid-signature"}, status=401)

    # 4) Parse AFTER verifying
    try:
        event = json.loads(raw_body_str)
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid-json"}, status=400)

    ok, why = validate_minimal(event)
    if not ok:
        return JsonResponse({"ok": False, "error": why}, status=422)

    # 5) Publish raw + parsed downstream, ack fast:
    # publish({"raw": raw_body_str, "parsed": event, "verified": True})
    print("✅ Prism webhook verified:", event.get("eventType"))
    return JsonResponse({"ok": True}, status=200)