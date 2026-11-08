# ADR 0001 — Semántica de saldos, balance acumulado y tarjetas

- **Estado:** aceptado (describe el comportamiento actual) · 2 puntos abiertos
- **Fecha:** 2026-11-07
- **Tests que lo fijan:** `backend/tests/test_invariants.py`

## Contexto

Varias pantallas muestran "cuánto dinero tengo" con cifras distintas (saldo de cuentas,
balance acumulado del mes, patrimonio en el dashboard). Las reglas estaban repartidas en
`database.py` (`get_accounts`, `get_monthly_summary`, `_row_to_card`, reportes) y en docstrings
que ya no coincidían del todo tras `79d1a8d feat(savings): pockets leave the account balance`.
Antes de refactorizar la capa de datos hay que fijar qué significa cada número.

## Decisión (comportamiento vigente)

| Concepto | Fórmula | Dónde |
|---|---|---|
| **Saldo de cuenta** | `apertura + ingreso − gasto − pago_tc ± transferencia − ahorro + retiro` | `GET /api/accounts` |
| **Total gastado del mes (caja)** | `gasto + pago_tc` del mes. `gasto_tc` **no** es salida de caja | `summary.total_expense` |
| **Balance acumulado** | `Σ aperturas de cuentas + Σ (ingreso − gasto − pago_tc)` hasta fin de mes | `summary.accumulated_balance` |
| **Invariante** | `balance acumulado = Σ saldos de cuentas + Σ (saldo − apertura) de ahorros` | test `test_equals_accounts_plus_net_savings` |
| **Encadenamiento** | `carryover(m+1) = accumulated_balance(m)` | test `test_months_chain` |
| **Patrimonio (dashboard)** | `Σ cuentas + Σ ahorros (valor actual o saldo)` | `DashboardPage.tsx` (cliente) |
| **Deuda de tarjeta** | `outstanding = Σ compras con interés − Σ pagos`; `available = límite − outstanding` | `GET /api/credit-cards` |
| **Cuota del ciclo** | `pending = Σ (bruto / cuotas)` de las compras cuyo plan cae en el ciclo abierto | idem |

Mover dinero a un bolsillo/CDT/acciones **sale de la cuenta** pero **no** reduce el balance
acumulado: es apartar, no gastar. Las aperturas de ahorros no forman parte de ninguna de las dos cifras.

## Puntos abiertos (requieren decisión de producto)

1. **Compras en cuotas en presupuestos/reportes.** Hoy una compra de 300.000 en 3 cuotas cuenta
   **completa y sin interés** en el mes del primer pago, mientras que la tarjeta factura 100.000 por
   ciclo (con interés). Opciones: (a) mantener — el gasto se reconoce al comprar; (b) repartir por
   cuota con interés, coherente con lo que realmente se paga cada mes.
2. **`debt` en `/api/credit-cards` es incorrecto** cuando hay pagos de ciclos anteriores:
   se calcula como `cuotas del ciclo cerrado − TODOS los pagos históricos`. Ejemplo: compra en 3 cuotas,
   se paga el extracto de septiembre, el de octubre queda pendiente → `debt = 0` en vez de 100.000.
   La UI no usa el campo (solo aparece en `types.ts`), así que el bug está latente. Opciones:
   corregir con asignación de pagos por ciclo (FIFO) o eliminar el campo.

## Consecuencias

- Cualquier refactor de `database.py` debe mantener verde `test_invariants.py` en SQLite **y** Postgres.
- Cambiar alguno de los puntos abiertos implica actualizar este ADR y el test correspondiente
  (`test_card_purchase_attributed_to_first_payment_month`).
