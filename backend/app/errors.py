"""Domain-level exceptions, independent of the database driver and of HTTP.

Services raise these; ``app.main`` maps them to HTTP responses in one
place, so business rules never import FastAPI.
"""


class IntegrityViolation(Exception):
    """A write broke a database constraint (unique, foreign key or check).

    Raised by ``database.get_connection`` for both SQLite and Postgres,
    so callers never need to know which driver is active.
    """


class DomainError(Exception):
    """A business rule rejected the request. The message is shown to the user."""


class ValidationFailed(DomainError):
    """The request breaks a business rule (HTTP 400)."""


class NotFound(DomainError):
    """A referenced entity does not exist (HTTP 404)."""
