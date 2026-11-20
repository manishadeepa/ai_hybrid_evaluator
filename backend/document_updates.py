"""Merge changes from a session snapshot without replacing newer unrelated data."""
from copy import deepcopy

from backend.persistence_lock import PERSISTENCE_LOCK
from backend.repositories.json_repository import read_json_document, write_json_document


_MISSING = object()


def _merge(before, proposed, latest):
    if proposed == before:
        return deepcopy(latest) if latest is not _MISSING else _MISSING
    if latest == before or latest == proposed:
        return deepcopy(proposed) if proposed is not _MISSING else _MISSING
    if isinstance(proposed, dict) and isinstance(latest, dict) and (isinstance(before, dict) or before is _MISSING):
        base = {} if before is _MISSING else before
        result = {}
        for key in base.keys() | proposed.keys() | latest.keys():
            value = _merge(base.get(key, _MISSING), proposed.get(key, _MISSING), latest.get(key, _MISSING))
            if value is not _MISSING:
                result[key] = value
        return result
    raise ValueError("Data changed in another session. Reload before saving; no changes were overwritten.")


def merge_session_document(path, before, proposed):
    """Atomically save only session changes; reject conflicting concurrent edits."""
    if not isinstance(before, dict) or not isinstance(proposed, dict):
        raise ValueError("Session document updates must be JSON objects.")
    with PERSISTENCE_LOCK:
        latest = read_json_document(path, {})
        if latest == []:
            latest = {}
        if not isinstance(latest, dict):
            raise ValueError("Stored session document must be a JSON object.")
        merged = _merge(before, proposed, latest)
        write_json_document(path, merged)
        return merged
