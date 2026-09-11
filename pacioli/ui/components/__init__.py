"""UI components for Pacioli.

Reusable, styled components built on top of CustomTkinter with consistent
design tokens and theming support.
"""

from pacioli.ui.components.button import (
    Button,
    ButtonVariant,
    ButtonSize,
    primary_button,
    secondary_button,
    danger_button,
    ghost_button,
)
from pacioli.ui.components.card import Card, CardVariant, StatCard
from pacioli.ui.components.modal import Modal, ModalSize, ConfirmModal, AlertModal
from pacioli.ui.components.toast import Toast, ToastVariant, ToastManager, toasts
from pacioli.ui.components.empty_state import (
    EmptyState,
    SearchEmptyState,
    DataEmptyState,
    ErrorEmptyState,
)
from pacioli.ui.components.input import (
    Input,
    InputVariant,
    MoneyInput,
    DateInput,
    SearchInput,
)

__all__ = [
    # Button
    "Button",
    "ButtonVariant",
    "ButtonSize",
    "primary_button",
    "secondary_button",
    "danger_button",
    "ghost_button",
    # Card
    "Card",
    "CardVariant",
    "StatCard",
    # Modal
    "Modal",
    "ModalSize",
    "ConfirmModal",
    "AlertModal",
    # Toast
    "Toast",
    "ToastVariant",
    "ToastManager",
    "toasts",
    # Empty State
    "EmptyState",
    "SearchEmptyState",
    "DataEmptyState",
    "ErrorEmptyState",
    # Input
    "Input",
    "InputVariant",
    "MoneyInput",
    "DateInput",
    "SearchInput",
]
