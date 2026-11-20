# Shared storage concurrency

All deployments writing to one MySQL database must use this backend version.

Use `backend.persistence_lock.PERSISTENCE_LOCK` around the complete synchronous
read/validate/change/write operation. Nested calls reuse the session and transaction.
For an explicitly selected store, use `PERSISTENCE_LOCK.for_store(store)`.

The MySQL implementation acquires a database-scoped `GET_LOCK` (15-second acquisition
timeout), holds its physical connection, and uses that connection for every document
operation in the unit of work. It verifies ownership before commit, rolls back on
failure, and releases or discards the connection safely. A caught nested failure
marks the transaction rollback-only. Do not hold an operation open across an `await`
or an external model/network call. Writes to several JSON documents in this scope
commit or roll back together. Uploaded files remain filesystem artifacts and are
not part of the SQL transaction.

New tables use InnoDB. Existing tables are checked on schema initialization and a
non-InnoDB table is rejected without automatically altering it. The lock name depends
on the database, not the checkout path or username. This supports multiple app hosts
connecting to the same writable MySQL server; it is not multi-primary cluster locking.

Folder mode retains the existing local thread/OS lock and atomic file replacements.
Stable connection-management configuration remains local and can be accessed while
the data database is unavailable. Reconfiguring credentials for the same database
does not re-import data. Separate deployments still require their own valid private
connection settings and encryption keys.

An explicit full-document replacement is not an automatic merge. Read fresh data
inside the operation boundary before replacing it. Profiles and repository mutations
follow this boundary. UI settings cached across requests use `merge_session_document`
with a private baseline: independent changes merge; same-field conflicts raise an
error telling the user to reload. New write paths must follow one of these patterns.
Direct SQL clients that ignore the protocol are not coordinated by these locks.

Keep test data and credentials out of Git. Restart both applications after upgrading
and refresh browser pages. Concurrency tests are in `test_shared_mysql_lock.py`.
