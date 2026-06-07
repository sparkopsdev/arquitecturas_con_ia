from __future__ import annotations

from .auth import Principal
from .db import Database


class AuditService:
    def __init__(self, db: Database):
        self.db = db

    def record(self, principal: Principal | None, action: str, detail: dict | str) -> None:
        if principal is None:
            self.db.add_audit("anonymous", "anonymous", action, detail)
        else:
            self.db.add_audit(principal.username, principal.role, action, detail)
