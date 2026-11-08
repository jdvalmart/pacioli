"""Persistence layer, one module per aggregate.

- ``connection``: connections, SQLite/Postgres dialect, paths, money helpers.
- ``models``: dataclasses returned by the repositories.
- ``migrations``: schema versions, Postgres schema, seeds, ``init_db``.
- ``categories``, ``transactions``, ``budgets``, ``accounts``, ``cards``,
  ``savings``: repositories.
- ``reports``: monthly aggregations and CSV export.
- ``backup``: SQLite snapshots with rotation.
"""
