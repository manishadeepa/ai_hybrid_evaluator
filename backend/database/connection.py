"""SQLAlchemy access to the MySQL profile managed by the Developer Console."""

from sqlalchemy.orm import sessionmaker

from backend.database.mysql_json_store import active_mysql_store


def get_active_engine():
    """Return the configured Developer Console MySQL engine."""
    store = active_mysql_store()
    if store is None:
        raise RuntimeError(
            "MySQL is not active. Configure and save it in the Developer Console."
        )
    return store.engine


def get_session_factory():
    """Create a session factory for the active Developer Console MySQL profile."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_active_engine(),
    )
