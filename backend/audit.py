"""
Automatic audit trail for the ERP backend.

Hooks SQLAlchemy's before_flush so EVERY ORM create / update / delete
made through the API is recorded in the `activity_log` table, with the
record's name and who did it -- no changes to individual routes.

Setup (main.py, after create_all):

    from audit import init_audit
    init_audit(engine)

And in security.get_current_user, just before `return {...}`:

    db.info["actor_id"] = user.pkid
    db.info["actor_name"] = user.full_name

(The actor is stored on the DB session because FastAPI runs each sync
dependency in its own thread context, so a contextvar set in
get_current_user would not be visible to the route handler.)

Only changes made from now on are recorded -- there is no history to
back-fill. If the table can't be created, auditing switches itself off
rather than breaking writes.
"""
import logging
import re
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    event,
    inspect,
)
from sqlalchemy.orm import Session, declarative_base

import model


log = logging.getLogger(__name__)

AuditBase = declarative_base()

_ENABLED = False


class ActivityLog(AuditBase):

    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)

    # created | updated | deleted | restored | activated | deactivated
    action = Column(String(20), nullable=False)

    entity = Column(String(60), nullable=False)        # e.g. "user", "employee"
    entity_name = Column(String(200), nullable=True)   # e.g. "Ravi Kumar"
    detail = Column(String(300), nullable=True)

    actor_id = Column(Integer, nullable=True)
    actor_name = Column(String(100), nullable=True)


# ==================================================
# WHAT TO SKIP
# Child rows of an employee are replaced wholesale on save
# (delete + re-insert), which would flood the log; the audit
# log itself must never audit itself.
# ==================================================

_SKIP_CLASSES = {
    "ActivityLog",
    "SalEmpContact",
    "SalEmpRelation",
    "SalEmpDocument",
    "SalEmpDocuments",
}

# columns that change on every write and say nothing useful
_NOISE_FIELDS = {
    "updated_at",
    "DateTimestamp",
    "Sync",
    "ATimestamp",
}

# readable names where splitting the class name isn't enough
_ENTITY_NAMES = {
    "User": "user",
    "SalaryEmployee": "employee",
    "SalaryStructure": "salary structure",
    "KSA": "KSA",
    "KSACategory": "KSA category",
    "ContMOC": "mode of contact",
    "ContTitle": "title",
    "ContQualification": "qualification",
    "ContRelationship": "relationship",
    "ContDepartment": "department",
    "ContDesignation": "designation",
    "ContCommon": "bank",
    "AcctAccount": "account",
    "DocMasRecords": "document type",
    "UserAccountMap": "user account mapping",
    "IDSettings": "ID setting",
    "SalAttendanceRules": "attendance rule",
}


def _entity_name(obj) -> str:

    cls = obj.__class__.__name__

    if cls in _ENTITY_NAMES:
        return _ENTITY_NAMES[cls]

    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cls).lower()


def _label(session: Session, obj):

    cls = obj.__class__.__name__

    if cls == "User":
        return getattr(obj, "full_name", None)

    if cls == "SalaryEmployee":
        return getattr(obj, "Employee", None)

    if cls == "SalaryStructure":
        try:
            emp = session.get(model.SalaryEmployee, int(obj.fkEmpId))
            return f"{emp.Employee} (from {obj.SalStart:%d %b %Y})" if emp else None
        except Exception:
            return None

    # generic: first real text column that isn't a key or audit column
    for attr in inspect(obj.__class__).column_attrs:

        col = attr.columns[0]

        if col.primary_key or attr.key.startswith("fk"):
            continue

        if attr.key in {"Sync", "LastStatus", "SysDefined"}:
            continue

        if isinstance(col.type, (String, Text)):

            value = getattr(obj, attr.key, None)

            if value:
                return str(value)[:120]

    return None


def _changed_fields(obj) -> list:

    state = inspect(obj)

    return [
        a.key
        for a in state.attrs
        if a.key not in _NOISE_FIELDS and a.history.has_changes()
    ]


_FIELD_NAMES = {
    "Employee": "name",
    "Abilities": "name",
    "EmpCode": "employee code",
    "DOJ": "joining date",
    "DOL": "leaving date",
    "DOB": "date of birth",
    "PAddress": "resident address",
    "NAddress": "native address",
    "fkDepId": "department",
    "fkDegId": "designation",
    "fkQualId": "qualification",
    "fkBnkId": "bank",
    "AccountNo": "account no.",
    "PFNo": "UAN",
    "ESICNo": "ESIC no.",
    "PANNo": "PAN",
    "Photo": "photo",
    "Male": "gender",
    "Married": "marital status",
    "full_name": "name",
}


def _humanize(field: str) -> str:

    if field in _FIELD_NAMES:
        return _FIELD_NAMES[field]

    field = field.replace("_", " ")
    field = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", field)

    return field.lower()


# ==================================================
# BUILD LOG ENTRIES FOR ONE FLUSH
# ==================================================

def _collect(session: Session) -> list:

    actor_id = session.info.get("actor_id")
    actor_name = session.info.get("actor_name")

    entries = []
    rights_users = set()

    def add(action, entity, name, detail=None):
        entries.append(
            {
                "action": action,
                "entity": entity,
                "entity_name": (name or "")[:200] or None,
                "detail": (detail or "")[:300] or None,
                "actor_id": actor_id,
                "actor_name": actor_name,
            }
        )

    # ---------------- created ----------------

    for obj in list(session.new):

        cls = obj.__class__.__name__

        if cls in _SKIP_CLASSES:
            continue

        if cls == "UserRight":
            rights_users.add(obj.fkUserId)
            continue

        detail = None
        if cls == "User" and not actor_name:
            detail = "Self-registered"

        add("created", _entity_name(obj), _label(session, obj), detail)

    # ---------------- updated ----------------

    for obj in list(session.dirty):

        cls = obj.__class__.__name__

        if cls in _SKIP_CLASSES:
            continue

        if not session.is_modified(obj, include_collections=False):
            continue

        if cls == "UserRight":
            rights_users.add(obj.fkUserId)
            continue

        fields = _changed_fields(obj)

        if not fields:
            continue

        entity = _entity_name(obj)
        name = _label(session, obj)

        # ---- users get richer wording ----
        if cls == "User":

            state = inspect(obj)

            if "deleted_at" in fields:
                add(
                    "deleted" if obj.deleted_at is not None else "restored",
                    entity,
                    name,
                )
                continue

            if "is_active" in fields:
                add(
                    "activated" if obj.is_active else "deactivated",
                    entity,
                    name,
                )
                continue

            parts = []
            for f in fields:
                if f == "password_hash":
                    parts.append("password changed")
                elif f == "role":
                    parts.append(f"role \u2192 {obj.role}")
                else:
                    parts.append(_humanize(f))

            add("updated", entity, name, ", ".join(parts))
            continue

        add(
            "updated",
            entity,
            name,
            "Changed: " + ", ".join(_humanize(f) for f in fields[:6]),
        )

    # ---------------- deleted ----------------

    for obj in list(session.deleted):

        cls = obj.__class__.__name__

        if cls in _SKIP_CLASSES:
            continue

        if cls == "UserRight":
            rights_users.add(obj.fkUserId)
            continue

        add("deleted", _entity_name(obj), _label(session, obj))

    # ---------------- rights: one entry per user ----------------

    for uid in rights_users:

        target = None
        try:
            target = session.get(model.User, uid)
        except Exception:
            pass

        add(
            "updated",
            "access rights",
            target.full_name if target else f"user #{uid}",
        )

    return entries


# ==================================================
# THE HOOK
# ==================================================

def _before_flush(session, flush_context, instances):

    if not _ENABLED or session.info.get("skip_audit"):
        return

    try:
        entries = _collect(session)
    except Exception:
        # never let auditing break a real write
        log.exception("Audit collection failed; skipping this flush.")
        return

    for entry in entries:
        session.add(ActivityLog(**entry))


def init_audit(engine) -> bool:
    """Create activity_log if needed and switch auditing on."""

    global _ENABLED

    try:
        AuditBase.metadata.create_all(bind=engine, checkfirst=True)
    except Exception:
        log.exception("Could not create activity_log; auditing is OFF.")
        _ENABLED = False
        return False

    if not event.contains(Session, "before_flush", _before_flush):
        event.listen(Session, "before_flush", _before_flush)

    _ENABLED = True
    log.info("Audit trail enabled.")
    return True

#end of file
