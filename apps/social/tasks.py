from celery import shared_task
from django.contrib.auth import get_user_model

from .services import broadcast_presence_change, maybe_mark_stale_presence_offline

User = get_user_model()


@shared_task(name="apps.social.cleanup_stale_presence")
def cleanup_stale_presence():
    changed_user_ids = []
    for user in User.objects.filter(presence_state__is_online=True).select_related("presence_state"):
        if maybe_mark_stale_presence_offline(user):
            changed_user_ids.append(user.id)
            broadcast_presence_change(user, False)
    return {"changed_user_ids": changed_user_ids}
