"""Shared rules for facilitator approval before test creation."""


def assigned_facilitator_ids(assessment: dict) -> list[str]:
    """Return assigned facilitator IDs, including legacy single-ID records."""
    ids = assessment.get("facilitator_ids")
    if not isinstance(ids, list) or not ids:
        legacy_id = assessment.get("facilitator_id", "")
        ids = [legacy_id] if isinstance(legacy_id, str) and legacy_id.strip() else []
    return [identity.strip() for identity in ids if isinstance(identity, str) and identity.strip()]


def all_facilitators_approved(assessment: dict) -> bool:
    """Require an explicit approval from each assigned facilitator."""
    ids = assigned_facilitator_ids(assessment)
    if not ids:
        # Preserve legacy service behavior for assessments without assignments.
        return True

    approvals = assessment.get("facilitator_approvals")
    if not isinstance(approvals, dict):
        approvals = {}

    legacy_single_approval = (
        len(ids) == 1
        and ids[0] not in approvals
        and str(assessment.get("approval_status", "")).strip().casefold() == "approved"
    )
    return legacy_single_approval or all(
        str(approvals.get(identity, "")).strip().casefold() == "approved"
        for identity in ids
    )


def aggregate_facilitator_approval_status(assessment: dict) -> str:
    """Derive the overall status from every assigned facilitator's decision."""
    ids = assigned_facilitator_ids(assessment)
    if not ids:
        existing = str(assessment.get("approval_status", "pending")).strip().casefold()
        return existing if existing in {"approved", "pending", "declined"} else "pending"

    approvals = assessment.get("facilitator_approvals")
    if not isinstance(approvals, dict):
        approvals = {}

    values = [
        str(approvals.get(identity, "")).strip().casefold()
        for identity in ids
    ]
    if (
        len(ids) == 1
        and not values[0]
        and str(assessment.get("approval_status", "")).strip().casefold() in {"approved", "declined"}
    ):
        values[0] = str(assessment["approval_status"]).strip().casefold()

    if all(value == "approved" for value in values):
        return "approved"
    if all(value == "declined" for value in values):
        return "declined"
    return "pending"
