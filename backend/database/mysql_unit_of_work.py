"""Session-owned MySQL advisory lock and transaction for JSON document operations."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from threading import local

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


_LOCAL = local()
LOCK_TIMEOUT_SECONDS = 15


def lock_name(database):
    # MySQL user locks are server-wide; credentials and checkout paths must not
    # distinguish two applications accessing the same database.
    identity = "application_json_documents:" + str(database).casefold()
    return "genai:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:58]


@dataclass
class _Binding:
    engine: object
    connection: object
    failed: bool = False


def mark_failed():
    binding = getattr(_LOCAL, "binding", None)
    if binding is not None:
        binding.failed = True


@contextmanager
def mysql_unit_of_work(store, *, timeout=LOCK_TIMEOUT_SECONDS):
    """Use one pinned connection until commit/rollback and explicit lock release.

    SQLite contract tests retain their existing transaction implementation. This
    coordination is for one writable MySQL server, not multi-primary clusters.
    """
    if store.engine.dialect.name != "mysql":
        yield None
        return
    previous = getattr(_LOCAL, "binding", None)
    if previous is not None and previous.engine is store.engine:
        if previous.failed:
            raise ValueError("The database operation was rolled back after an earlier failure.")
        try:
            yield previous.connection
        except BaseException:
            previous.failed = True
            raise
        return

    if previous is not None:
        # A second connection cannot acquire a named lock held by our own session.
        def target(engine):
            url = engine.url
            return (str(url.host).casefold(), url.port or 3306, str(url.database).casefold())
        if target(previous.engine) == target(store.engine):
            raise ValueError("A different connection to this database is already active in this operation.")

    name = lock_name(store.configuration.get("database", store.engine.url.database))
    connection = None
    acquired = False
    transaction = None
    body_failed = False
    commit_attempted = False
    try:
        connection = store.engine.connect()
        acquired = connection.execute(
            text("SELECT GET_LOCK(:name, :timeout)"),
            {"name": name, "timeout": timeout},
        ).scalar_one() == 1
        if not acquired:
            raise ValueError("Database is busy; the shared storage lock could not be acquired. No changes were saved.")
        # GET_LOCK starts SQLAlchemy's implicit transaction. End it before the
        # application snapshot begins. Named locks survive commit/rollback.
        connection.commit()
        store.ensure_schema()
        transaction = connection.begin()
        binding = _Binding(store.engine, connection)
        _LOCAL.binding = binding
        yield connection
        if binding.failed:
            raise ValueError("The database operation was rolled back after an earlier failure.")
        owned = connection.execute(
            text("SELECT IS_USED_LOCK(:name) = CONNECTION_ID()"), {"name": name}
        ).scalar_one()
        if owned != 1:
            raise ValueError("Shared database lock ownership was lost; changes were not committed.")
        commit_attempted = True
        transaction.commit()
    except BaseException as exc:
        body_failed = True
        if transaction is not None and transaction.is_active:
            try:
                transaction.rollback()
            except SQLAlchemyError:
                connection.invalidate()
        if isinstance(exc, SQLAlchemyError):
            if commit_attempted:
                raise ValueError("Database confirmation failed during commit; verify the saved result before retrying.") from None
            raise ValueError("Shared MySQL operation failed; changes were not committed. Verify database connectivity before retrying.") from None
        raise
    finally:
        _LOCAL.binding = previous
        if connection is not None:
            try:
                if acquired and not connection.invalidated and not connection.closed:
                    released = connection.execute(
                        text("SELECT RELEASE_LOCK(:name)"), {"name": name}
                    ).scalar_one()
                    if released != 1:
                        connection.invalidate()
                        if not body_failed:
                            raise ValueError("Shared database lock release failed; verify the saved result before retrying.")
            except SQLAlchemyError:
                connection.invalidate()
                if not body_failed:
                    raise ValueError("Database connection ended during lock cleanup; verify the saved result before retrying.") from None
            finally:
                connection.close()


@contextmanager
def document_connection(store, *, write=False):
    """Bind every read/write to the session that owns the MySQL lock."""
    with mysql_unit_of_work(store) as connection:
        if connection is not None:
            if connection.invalidated or connection.closed:
                mark_failed()
                raise ValueError("The locked database connection is no longer available.")
            yield connection
        else:
            with (store.engine.begin() if write else store.engine.connect()) as fallback:
                yield fallback
