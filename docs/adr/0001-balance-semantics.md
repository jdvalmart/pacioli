# ADR 0001 — Semántica de saldos, balance acumulado y tarjetas

- **Estado:** aceptado · puntos abiertos resueltos el 2026-11-08 (ver *Decisiones de tarjeta*)
- **Fecha:** 2026-11-07 (revisado 2026-11-08)
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
| **Deuda total** | `outstanding = Σ compras con interés − Σ pagos`; `available = límite − outstanding` | `GET /api/credit-cards` |
| **Por pagar ya** | `debt = Σ cuotas de extractos cerrados − Σ pagos` (mínimo 0) | idem |
| **Cuota del ciclo** | `pending = cuotas del ciclo abierto − pagos anticipados` (pagos que exceden lo ya facturado) | idem |
| **Gasto por categoría** | cada cuota (con interés) cuenta en el mes en que vence su extracto | resumen, reportes, presupuesto, listado |

Mover dinero a un bolsillo/CDT/acciones **sale de la cuenta** pero **no** reduce el balance
acumulado: es apartar, no gastar. Las aperturas de ahorros no forman parte de ninguna de las dos cifras.

## Decisiones de tarjeta (2026-11-08)

Criterio: comportarse como un producto comercial y como factura un banco. Las reglas viven en
el módulo puro `backend/app/domain/billing.py` y se prueban sin base de datos en `tests/test_billing.py`.

1. **Las compras en cuotas se reparten por cuota, con interés.** Cada cuota cuenta en la categoría de la
   compra el mes en que vence su extracto. Una compra de 300.000 en 3 cuotas suma 100.000 en cada uno de
   los tres meses y aparece en el listado de cada mes como "cuota k/3". `amount` sigue siendo el valor de
   la compra (para editarla) y `billed_amount` es la cuota del mes. El interés es un costo real del gasto,
   así que se presupuesta. *Rechazado:* reconocer la compra completa al comprar o en el primer pago, porque
   descuadra el presupuesto respecto de lo que el usuario realmente paga cada mes e ignora el interés.
2. **`debt` se corrige y se muestra como "Por pagar ya".** Los pagos se aplican primero a los extractos
   más antiguos (FIFO), así que `debt` es lo facturado en extractos cerrados que sigue sin pagarse (incluye
   extractos vencidos). Lo pagado de más reduce la cuota del ciclo abierto (`pending`). Es la cifra más
   importante de una tarjeta, así que la UI la destaca y la propone por defecto en el diálogo de pago.
   *Rechazado:* eliminar el campo.
3. **Redondeo:** el total financiado se redondea una vez al centavo (half-up) y se reparte en cuotas
   enteras que suman exactamente ese total; los centavos sobrantes van en las primeras cuotas.
   Con 1 cuota no se cobra interés.

Una compra cuya tarjeta se eliminó ya no tiene ciclo: cuenta una vez, completa, en el mes de compra.

4. **Dos cuotas pueden vencer en el mismo mes** (2026-11-08). Con corte 31 y pago 30, el extracto
   de enero vence el 28 de febrero (no hay 30) y el de febrero, que cierra el 28, vence ese mismo día.
   Ambas cuotas cuentan en febrero; antes se contaba solo la primera.

## Rendimiento (2026-11-08)

Medido con 10 años de uso intenso (36.537 movimientos, 9.122 compras con tarjeta): el 90 % del
tiempo era construir el cronograma completo de cada compra histórica, no el SQL.

- `billing.billed_in_month` y `card_status` calculan en O(1) por compra (solo 1–2 ciclos candidatos
  por mes; sumas de cuotas por aritmética). `schedule()` queda como referencia legible y un test con
  miles de casos aleatorios exige que las rutas rápidas den exactamente lo mismo.
- Prefiltro SQL portable (`CARD_CANDIDATES_SQL`): una compra en N cuotas solo puede cobrarse entre su
  mes y N+1 meses después (cota verificada contra el cronograma); la lista del mes filtra por fecha en SQL.
- Resultado: lista del mes 536 → 43 ms, resumen 317 → 23 ms, tarjetas 325 → 67 ms, reporte anual
  3,85 s → 0,25 s; salidas idénticas a la versión anterior en 120 respuestas comparadas.
- *Rechazado:* persistir el mes de cobro en una columna (Fase 4 original). Duplicaba un dato derivado
  que habría que recalcular al editar el corte de una tarjeta, y el problema real era algorítmico.

## Consecuencias

- Cualquier refactor de `database.py` debe mantener verde `test_invariants.py` en SQLite **y** Postgres.
- Cambiar una regla de tarjeta implica actualizar este ADR, `test_billing.py` y
  `test_installments_spread_over_their_payment_months` / `test_debt_is_unpaid_closed_statements`.
