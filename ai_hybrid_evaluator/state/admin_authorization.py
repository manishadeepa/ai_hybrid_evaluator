"""Server-side authorization helpers for protected Admin state handlers."""


def is_verified_admin_session(auth_state) -> bool:
    """Check role and identity fields from a server-resolved AuthState."""
    email = getattr(auth_state, "admin_email", "")
    return bool(
        getattr(auth_state, "is_authenticated", False)
        and getattr(auth_state, "admin_role", "") in {"Master Admin", "Group Admin"}
        and isinstance(email, str)
        and email.strip()
    )


async def get_auth_state(state):
    from ai_hybrid_evaluator.state.auth_state import AuthState

    return await state.get_state(AuthState)


async def has_admin_session(state) -> bool:
    auth_state = await get_auth_state(state)
    return is_verified_admin_session(auth_state)


async def has_candidate_session(state) -> bool:
    auth_state = await get_auth_state(state)
    return bool(
        auth_state.is_candidate_authenticated
        and auth_state.candidate_emp_id
    )


async def has_facilitator_session(state) -> bool:
    auth_state = await get_auth_state(state)
    return bool(
        auth_state.is_facilitator_authenticated
        and auth_state.facilitator_emp_id
    )
