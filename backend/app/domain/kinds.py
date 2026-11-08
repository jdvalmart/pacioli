"""Closed value sets (movement kinds, category/account/savings types)
shared by the API, the services and the data layer."""

from enum import StrEnum
from typing import Literal

# Closed sets stored as text in the database (enforced by CHECK constraints
# or by the API); shared by app.db models and the API schemas.
CategoryType = Literal["income", "expense"]
CategoryRole = Literal["savings"]
AccountType = Literal["efectivo", "digital", "ahorros", "banco"]
SavingsKind = Literal["bolsillo", "bolsillo_programado", "cdt", "acciones"]


class TxKind(StrEnum):
    """What a transaction does with the money.

    Values are the strings stored in ``transactions.kind`` (and allowed
    by its CHECK constraint), so a ``TxKind`` compares equal to the raw
    database value.
    """

    INGRESO = "ingreso"  # money into an account
    GASTO = "gasto"  # money out of an account
    TRANSFERENCIA = "transferencia"  # between two of the user's accounts
    GASTO_TC = "gasto_tc"  # credit card purchase: no cash moves until paid
    PAGO_TC = "pago_tc"  # credit card payment from an account
    AHORRO = "ahorro"  # account -> savings item
    RETIRO = "retiro"  # savings item -> account

    @property
    def label(self) -> str:
        """Human label (Spanish UI)."""
        return _LABELS[self]


_LABELS = {
    TxKind.INGRESO: "Ingreso",
    TxKind.GASTO: "Gasto",
    TxKind.TRANSFERENCIA: "Transferencia",
    TxKind.GASTO_TC: "Gasto TC",
    TxKind.PAGO_TC: "Pago TC",
    TxKind.AHORRO: "Ahorro",
    TxKind.RETIRO: "Retiro",
}
