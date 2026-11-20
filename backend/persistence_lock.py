"""Shared application operation boundary for folder and MySQL persistence."""
from functools import wraps
from contextlib import contextmanager
import errno
import hashlib
import os
from pathlib import Path
import tempfile
import time
from threading import RLock, local


class PersistenceLock:
    def __init__(self):
        self._thread_lock = RLock()
        self._local = local()

    @staticmethod
    def _lock_path():
        identity = os.path.normcase(str(Path(__file__).resolve().parents[1])).encode("utf-8")
        return Path(tempfile.gettempdir()) / ("gen-ai-hybrid-eval-" + hashlib.sha256(identity).hexdigest() + ".lock")

    @staticmethod
    def _acquire_file_lock(lock_file):
        if os.name == "nt":
            import msvcrt
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            while True:
                lock_file.seek(0)
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EDEADLK, errno.EAGAIN):
                        raise
                    time.sleep(.05)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

    @staticmethod
    def _release_file_lock(lock_file):
        if os.name == "nt":
            import msvcrt
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def for_store(self, store):
        previous = getattr(self._local, "override_store", self)
        self._local.override_store = store
        try:
            with self:
                if store is None:
                    yield self
                else:
                    from backend.database.mysql_unit_of_work import mysql_unit_of_work
                    with mysql_unit_of_work(store):
                        yield self
        finally:
            if previous is self:
                del self._local.override_store
            else:
                self._local.override_store = previous

    def local_only(self):
        return self.for_store(None)

    def __enter__(self):
        self._thread_lock.acquire()
        depth = getattr(self._local, "depth", 0)
        try:
            if depth == 0:
                handle = self._lock_path().open("a+b")
                locked = False
                try:
                    self._acquire_file_lock(handle)
                    locked = True
                    from backend.database.mysql_json_store import active_mysql_store
                    from backend.database.mysql_unit_of_work import mysql_unit_of_work
                    store = self._local.override_store if hasattr(self._local, "override_store") else active_mysql_store()
                    context = mysql_unit_of_work(store) if store is not None else None
                    if context is not None:
                        context.__enter__()
                    self._local.context = context
                    self._local.handle = handle
                except BaseException:
                    if locked:
                        self._release_file_lock(handle)
                    handle.close()
                    raise
            self._local.depth = depth + 1
            return self
        except BaseException:
            self._thread_lock.release()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        depth = self._local.depth - 1
        try:
            if exc_type is not None:
                from backend.database.mysql_unit_of_work import mark_failed
                mark_failed()
            if depth == 0:
                try:
                    context = self._local.context
                    if context is not None:
                        context.__exit__(exc_type, exc_value, traceback)
                finally:
                    handle = self._local.handle
                    try:
                        self._release_file_lock(handle)
                    finally:
                        handle.close()
                        del self._local.context
                        del self._local.handle
        finally:
            self._local.depth = depth
            self._thread_lock.release()


PERSISTENCE_LOCK = PersistenceLock()


def persistence_operation(function):
    """Protect an entire service operation, rather than only its final write."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with PERSISTENCE_LOCK:
            return function(*args, **kwargs)
    return wrapped
