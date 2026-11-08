"""Backwards-compatible facade over the ``app.db`` package.

The data layer used to live in this single module. It is now split by
aggregate under ``app/db/``; this module re-exports every name so existing
imports keep working. New code should import from ``app.db.<module>``.

Design rules (unchanged):

- Money is stored as INTEGER cents; Decimal is used at the domain edge.
- Schema is versioned (``PRAGMA user_version`` / ``pacioli_schema_version``).
- Recurring templates are materialized once per month and recorded in
  ``recurring_materialized`` so instances are never duplicated.
- The database lives outside the repository (XDG data dir).
"""

from app.db.accounts import (  # noqa: F401
    _ensure_income_category,
    _row_to_account,
    add_account,
    delete_account,
    get_accounts,
    update_account,
)
from app.db.backup import (  # noqa: F401
    BACKUP_KEEP,
    auto_backup,
    backup_database,
)
from app.db.budgets import (  # noqa: F401
    delete_budget,
    get_budgets,
    get_monthly_plan,
    set_budget,
    set_budgets_bulk,
    set_monthly_plan,
)
from app.db.cards import (  # noqa: F401
    _billed_in,
    _card_of,
    _purchase_of,
    _row_to_card,
    add_credit_card,
    delete_credit_card,
    get_credit_cards,
    update_credit_card,
)
from app.db.categories import (  # noqa: F401
    add_category,
    add_subcategory,
    delete_category,
    delete_subcategory,
    get_all_subcategories,
    get_categories,
    get_subcategories,
    update_category,
)
from app.db.connection import (  # noqa: F401
    _DRIVER_INTEGRITY_ERRORS,
    DEFAULT_DB_PATH,
    _adapt_sql,
    _ddl,
    _default_data_dir,
    _get_version,
    _has_column,
    _insert_get_id,
    _is_postgres,
    _PGConnWrapper,
    _PGCursorWrapper,
    _q,
    _set_version,
    _to_cents,
    _to_dec,
    get_backup_dir,
    get_connection,
    get_db_path,
    set_db_path,
)
from app.db.migrations import (  # noqa: F401
    LEGACY_DB_PATH,
    SCHEMA_VERSION,
    _create_postgres_schema,
    _ensure_savings_category,
    _import_legacy_db,
    _migrate_v1_baseline,
    _migrate_v2_cents,
    _migrate_v3_subcategory_dedup,
    _migrate_v4_budget_constraint,
    _migrate_v5_accounts,
    _migrate_v6_account_starting_transactions,
    _migrate_v7_transaction_kinds,
    _migrate_v8_credit_cards,
    _migrate_v9_payment_kind,
    _migrate_v10_savings,
    _migrate_v11_monthly_plan,
    _migrate_v12_opening_balances,
    _migrate_v13_installments,
    _migrate_v14_savings_dividends,
    _migrate_v15_savings_category,
    _migrate_v16_category_roles,
    _seed_defaults,
    _user_version,
    init_db,
)
from app.db.models import (  # noqa: F401
    ACCOUNT_TYPE_DEFAULTS,
    CATEGORY_ROLE_SAVINGS,
    SAVINGS_KIND_ICONS,
    Account,
    Budget,
    Category,
    CreditCard,
    MonthlySummary,
    SavingsItem,
    Subcategory,
    Transaction,
)
from app.db.reports import (  # noqa: F401
    export_transactions_csv,
    get_budget_vs_actual,
    get_category_spending,
    get_monthly_summaries,
    get_monthly_summary,
    transactions_to_csv,
)
from app.db.savings import (  # noqa: F401
    _row_to_savings,
    _savings_category,
    _savings_net_for_month,
    add_savings,
    delete_savings,
    get_savings,
    update_savings,
)
from app.db.transactions import (  # noqa: F401
    _TX_KEYS,
    _month_window,
    _row_to_tx,
    add_transaction,
    delete_transaction,
    ensure_recurring,
    get_transactions,
    update_transaction,
)
