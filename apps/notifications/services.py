import json
import os

from django.contrib.auth import get_user_model
from django.conf import settings

from .models import PushSubscription

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - optional dependency
    WebPushException = Exception
    webpush = None

User = get_user_model()

VAPID_PRIVATE_KEY = getattr(settings, "VAPID_PRIVATE_KEY", os.getenv("VAPID_PRIVATE_KEY", ""))
VAPID_CLAIMS = {
    "sub": getattr(settings, "VAPID_SUBJECT", os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")),
    "audience": getattr(settings, "VAPID_AUDIENCE", os.getenv("VAPID_AUDIENCE", "")),
}


def _subscription_info(subscription):
    return {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }


def send_push_to_user(user, payload):
    """Send a browser push notification to all active subscriptions for a user."""
    if not webpush or not VAPID_PRIVATE_KEY or not VAPID_CLAIMS["audience"]:
        return
    subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
    for subscription in subscriptions:
        try:
            webpush(
                _subscription_info(subscription),
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
        except WebPushException:
            subscription.is_active = False
            subscription.save(update_fields=["is_active"])


def send_push_to_users(users, payload):
    """Send a browser push notification to multiple users."""
    for user in users:
        send_push_to_user(user, payload)
