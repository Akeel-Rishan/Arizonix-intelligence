from arizonix_api.db.models.audit import AuditAction

AUDIT_ACTIONS = tuple(action.value for action in AuditAction)

__all__ = ["AUDIT_ACTIONS", "AuditAction"]
