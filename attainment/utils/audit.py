"""
Lightweight audit-log helper.
"""
from attainment.models import AuditLog


def log_action(user, action: str, entity: str, entity_id, details: str = ""):
    """
    Create an AuditLog entry.
    `user` can be a User instance or a string (username / id).
    """
    uid = str(user.pk) if hasattr(user, "pk") else str(user)
    AuditLog.objects.create(
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        user_id=uid,
        details=details,
    )
