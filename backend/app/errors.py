"""Domain-level exceptions, independent of the database driver."""


class IntegrityViolation(Exception):
    """A write broke a database constraint (unique, foreign key or check).

    Raised by ``database.get_connection`` for both SQLite and Postgres,
    so callers never need to know which driver is active.
    """
