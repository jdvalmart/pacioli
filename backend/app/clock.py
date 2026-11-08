"""Single source of "today" for the whole backend.

Billing cycles, savings maturity and recurring materialization all
depend on the current date. Reading it through this module (always as
``clock.today()``, never ``from app.clock import today``) lets tests
freeze time in one place instead of patching ``date`` per module.
"""

from datetime import date


def today() -> date:
    """Return the current local date."""
    return date.today()
