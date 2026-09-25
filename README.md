# Pacioli — Finanzas personales inspiradas en Luca Pacioli

> *Fray Luca Pacioli (c. 1445–1517) formalizó la partida doble.* Pacioli, la app, lleva esa idea a tus finanzas diarias: cada movimiento tiene su contrapartida y cada peso tiene su lugar.

Pacioli es una app web de finanzas personales para **presupuestar, registrar y entender** tu dinero mes a mes. 100% local (SQLite).

![Stack](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLite-blue) ![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite%206-61DAFB) ![Charts](https://img.shields.io/badge/Charts-Recharts%203-orange) ![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Funcionalidades

### Dashboard — vista general del mes seleccionado
- **Resumen:** ingresos, gastos, balance acumulado y balance del mes.
- **Cuentas** (solo lectura, gestión en Configuración): saldo real = apertura + ingresos − gastos ± transferencias ± ahorros fuera de bolsillo. El saldo inicial no pertenece a ningún mes.
- **Tarjetas de crédito:** cupo = límite − deuda total; ciclo actual `6 sep → 5 oct` con pago `15 oct` (configurable 1–31), `por facturar` del ciclo abierto y `deuda total` pendiente. Soporta **compras en cuotas** (1–60) con interés total %.
- **Presupuestos:** `Asignado / Gastado / Restante` + `Sin asignar`. Solo categorías con presupuesto cuentan para `Gastado`/`Restante`; lo gastado sin presupuesto se muestra aparte.
- **Ahorro e inversión** y **Gasto por categoría** (donut) con la misma paleta vívida del resto de la app.

### Transacciones
- Tipos: `ingreso`, `gasto`, `transferencia`, `gasto_tc` (compra con tarjeta, con cuotas 1–60 e interés), `pago_tc`, `ahorro`, `retiro`.
- **Split:** dos tablas — **Cuentas** (14) y **Tarjetas de crédito** (1) — con nota “no descuentan de tus cuentas hasta que las pagues”.
- **Filtro por tipo** con contadores (`Todos 15 · Ingreso 1 · Gasto 11…`).
- **Recurrentes:** plantillas mensuales materializadas idempotentemente; solo se materializan hasta el mes actual (no inflan saldos futuros). Marcadas con *recurrente*.
- **Ahorro:** selector de destino + botón **Crear bolsillo/CDT/acciones** (diálogo reutilizable). `CDT` y `bolsillo programado` quedan **bloqueados hasta vencimiento** (`matures_on`).

### Presupuestos
- **Presupuesto total del mes** persistido (`monthly_plans`, migración v11) — editable, por defecto el ingreso del mes. `Sin asignar = total − asignado`.
- **Categorías** en el orden pedido por el usuario: Vivienda → Alimentación → Servicios → Transporte → **Diezmo (🙏)** → **Ahorro (🐷)** → resto. `Asignado` incluye diezmo/ahorro como categorías normales.
- Se puede **guardar en 0** para limpiar un mes (ej. septiembre de prueba). Barras corregidas (`indicatorClassName`) y riel sin borde.

### Reportes — 4 paneles parejos `h-[28rem]` en grilla 2×2
| Panel | Qué muestra |
|-------|-------------|
| **Ingresos vs gastos** (barras) | Serie anual, mes actual marcado con línea punteada. Colores: azul `#3B82F6` / naranja `#F97316`. Sin animación para captura fiable. |
| **Balance mensual** (línea ámbar `#F59E0B`) | Ingresos − gastos por mes. |
| **Gasto por categoría** | Barras horizontales % del total (colores de categoría), total del mes. |
| **Presupuesto vs real** | Solo categorías con presupuesto; `Gastado` apilado (`$real` + `de presupuesto`) para alinear números. |

Eje Y compacto: `$3,0M / $750k`.

### Configuración (`/settings`) — único lugar de alta/edición
Todo lo configurable vive aquí, envuelto en `SectionCard` (card grande con header + acción):
- **Cuentas:** nombre, tipo (`efectivo/digital/ahorros/banco`), **saldo inicial** (“no cuenta en ningún mes”).
- **Tarjetas:** límite, días de corte/pago.
- **Ahorro e inversión:** bolsillo (meta + tasa), programado (día/monto + tasa + plazo), CDT (tasa + plazo), **acciones** (valor actual + **dividendos recibidos** + ganancia total). Grilla `sm:2 xl:3` y filas compactas (`p-3`, `size-9`).
- **Categorías:** `Ingresos` arriba, `Gastos` abajo (a pedido del usuario), grilla compacta.

### Navegación
- Sidebar colapsable (flecha arriba, `top-6 -right-3`), `w-20` vs `w-60`, `bg-sidebar`, persistido en `localStorage["pacioli-sidebar"]`. `flex h-screen overflow-hidden` + `min-h-0` arregla el scroll; header `h-16` centrado (`md:top-1/2 md:-translate-…`) sin `border-b`, con píldora de fecha y botón **Mes actual**.
- Tipografía **Plus Jakarta Sans** (antes Nunito), logo monograma `P` (libro con cruz: Biblia/ledger) y botones *soft-modern* (`shadow-sm`, sin relieve duro). `StatCard` unificado (icono `size-14` + valor) en Dashboard/Presupuestos/Reportes. `rounded-2xl` → `border` (1px) global.

---

## 🧱 Stack

| Capa | Tecnologías |
|------|-------------|
| **Backend** | FastAPI, Pydantic, SQLite (`money` como `INTEGER cents`), migraciones `PRAGMA user_version` (v14), `uvicorn` |
| **Frontend** | React 19, TypeScript 5, Vite 6, Tailwind v4, shadcn/ui + Base UI, Recharts 3, TanStack Query 5, React Router 7 |
| **Calidad** | `ruff`, `mypy`, `pytest`, `tsc -b`, `oxlint`, `vite build` |

---

## 📁 Estructura

```
pacioli/
├── backend/
│   ├── app/
│   │   ├── database.py      # 14 migraciones, cuentas/savings con apertura, tarjetas con ciclos/cuotas
│   │   ├── main.py          # SPA + /api
│   │   ├── routers/         # accounts, savings, transactions, budgets, credit_cards, reports
│   │   └── schemas.py       # Pydantic (Money como string "1234.56")
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/      # SectionCard, StatCard, SavingsFormDialog, Logo
│   │   ├── pages/           # Dashboard, Transactions, Budgets, Reports, Settings (+ Categories)
│   │   ├── hooks/useMonth.ts# mes en URL + espejo en localStorage
│   │   └── lib/             # api.ts, types.ts, money.ts
│   └── public/favicon.svg   # libro con cruz
└── README.md
```

---

## ✅ Requisitos

- Python 3.11+
- Node.js 22+

## 🚀 Puesta en marcha

```bash
# Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Frontend
cd ../frontend
npm install

# (opcional) fuente
# npm i @fontsource-variable/plus-jakarta-sans  # ya incluida
```

### Desarrollo

```bash
./dev.sh
# API → http://localhost:8000  (/docs)
# Vite → http://localhost:5173  (proxy /api/* → :8000)
# Ctrl+C detiene ambos
```

### Producción (un solo proceso)

```bash
cd frontend && npm run build && cd ..
backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
# Si existe frontend/dist, el backend sirve la SPA en http://localhost:8000
```

---

## 💾 Datos

- **Ubicación:** `~/.local/share/pacioli/pacioli.db` (`XDG_DATA_HOME` o `PACIOLI_DATA_DIR` la sobreescriben). Compatible con `data/budget.db` del desktop: se importa una vez.
- **Backups diarios** con rotación (10) en `~/.local/share/pacioli/backups/`.
- **Migraciones** (`SCHEMA_VERSION = 14`):
  - v11 `monthly_plans` (total del mes)
  - v12 `accounts.starting_cents` / `savings.opening_cents` (saldos iniciales fuera de mes)
  - v13 `transactions.installments` / `interest_bp`
  - v14 `savings.dividends_cents` + `matures_on` (derivado de `created_at + term_days`)
- **Reglas de saldo:**
  - **Cuenta:** `starting + ingresos − gastos − pago_tc ± transferencias − ahorro(no-bolsillo) + retiro(no-bolsillo)`. `bolsillo` es solo apartado (sigue en cuenta); `programado/cdt/acciones` salen de la cuenta.
  - **Resumen mensual:** `total_expense = gasto + pago_tc` (cuota de tarjeta no es gasto hasta pagarla). `gasto_tc` solo afecta cupo y ciclo, no caja.
  - **Tarjeta:** ciclo `6 sep → 5 oct` (exclusivo/inclusivo), `pending` = cuotas del ciclo actual, `outstanding` = Σ totales con interés − pagos, `available = limit − outstanding`.

---

## 🔌 API (`/api`)

| Prefijo | Descripción |
|---------|-------------|
| `/api/accounts` | CRUD cuentas (`starting` incluido) |
| `/api/categories` | CRUD categorías y `/subcategories` |
| `/api/savings` | CRUD ahorros (`opening`, `dividends`, `matures_on`) |
| `/api/credit-cards` | CRUD tarjetas + ciclo (`?month=&year=` para ver otro mes) |
| `/api/transactions` | CRUD mensual + `installments`/`interest_bp` + `POST /materialize` |
| `/api/budgets` | CRUD por categoría + `GET/PUT /budgets/plan` (total) + `DELETE` |
| `/api/reports` | `summary`, `monthly?year=`, `category-spending`, `budget-vs-actual`, `export` |

Montos como strings `"1234.56"` para evitar `float64`.

---

## 🧪 Calidad

```bash
# Backend
cd backend && .venv/bin/ruff check . && .venv/bin/mypy app && .venv/bin/pytest -q
# 139 passed

# Frontend
cd frontend && npx tsc -b && npm run lint && npm run build
```

Verificación visual con Chrome headless (`--screenshot`, `--virtual-time-budget`, `--remote-debugging-port` + `WebSocket` CDP) para dashboard, presupuestos, reportes, settings y formulario de transacción.

---

## 📜 Licencia

MIT — ver `LICENSE`.
