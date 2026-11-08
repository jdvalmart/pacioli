# Pacioli — Finanzas personales inspiradas en Luca Pacioli

> *Fray Luca Pacioli (c. 1445–1517) formalizó la partida doble.* Pacioli, la app, lleva esa idea a tus finanzas diarias: cada movimiento tiene su contrapartida y cada peso tiene su lugar.

Pacioli es una app web de finanzas personales para **presupuestar, registrar y entender** tu dinero mes a mes. 100% local: **SQLite por defecto** y **PostgreSQL en contenedor** cuando se activa con `DATABASE_URL`.

![Stack](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLite%2FPostgres-blue) ![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite%206-61DAFB) ![Charts](https://img.shields.io/badge/Charts-Recharts%203-orange) ![License](https://img.shields.io/badge/License-MIT-green)

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
- **Ahorro e inversión:** bolsillo (meta + tasa), programado (día/monto + tasa + plazo), CDT (tasa + plazo), **acciones** (valor actual + **dividendos recibidos** + ganancia total). Un bolsillo puede **enlazarse a una categoría** y se muestra como **Reservado** en el presupuesto (es apartar, no gastar). Grilla `sm:2 xl:3` y filas compactas (`p-3`, `size-9`).
- **Categorías:** `Ingresos` arriba, `Gastos` abajo (a pedido del usuario), grilla compacta.

### Navegación
- Sidebar colapsable (flecha arriba, `top-6 -right-3`), `w-20` vs `w-60`, `bg-sidebar`, persistido en `localStorage["pacioli-sidebar"]`. `flex h-screen overflow-hidden` + `min-h-0` arregla el scroll; header `h-16` centrado (`md:top-1/2 md:-translate-…`) sin `border-b`, con píldora de fecha y botón **Mes actual**.
- Tipografía **Plus Jakarta Sans** (antes Nunito), logo monograma `P` (libro con cruz: Biblia/ledger) y botones *soft-modern* (`shadow-sm`, sin relieve duro). `StatCard` unificado (icono `size-14` + valor) en Dashboard/Presupuestos/Reportes. `rounded-2xl` → `border` (1px) global.

---

## 🧱 Stack

| Capa | Tecnologías |
|------|-------------|
| **Backend** | FastAPI, Pydantic, SQLite/PostgreSQL dual (`money` como `INTEGER`/`BIGINT cents`), migraciones `PRAGMA user_version` / `pacioli_schema_version` (v16), `uvicorn`, `psycopg` |
| **Frontend** | React 19, TypeScript 5, Vite 6, Tailwind v4, shadcn/ui + Base UI, Recharts 3, TanStack Query 5, React Router 7 |
| **Calidad** | `ruff`, `mypy`, `pytest`, `tsc -b`, `oxlint`, `vite build` |

---

## 📁 Estructura

```
pacioli/
├── backend/
│   ├── app/
│   │   ├── main.py          # SPA + /api, manejo central de errores de dominio
│   │   ├── routers/         # solo HTTP: accounts, savings, transactions, budgets, credit_cards, reports
│   │   ├── services/        # casos de uso (validación de movimientos)
│   │   ├── domain/          # reglas puras: billing (ciclos, cuotas, FIFO), kinds (TxKind)
│   │   ├── db/              # persistencia por agregado + connection, migrations (v16), backup
│   │   ├── database.py      # fachada de compatibilidad sobre app/db
│   │   ├── cli.py           # python -m app.cli backup
│   │   └── schemas.py       # Pydantic (Money como string "1234.56")
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/      # SectionCard, StatCard, secciones de Ajustes (cuentas, tarjetas, ahorro, categorías)
│   │   ├── pages/           # Dashboard, Transactions, Budgets, Reports, Settings
│   │   ├── hooks/useMonth.ts# mes en URL + espejo en localStorage
│   │   └── lib/             # api.ts, types.ts, money.ts
│   └── public/favicon.svg   # libro con cruz
├── Dockerfile
├── docker-compose.yml      # app (8000) + db (host 5433)
├── scripts/migrate_to_postgres.py
└── README.md
```

---

## ✅ Requisitos

- Python 3.11+
- Node.js 22+
- `uv` (entorno de Python) y systemd de usuario para el servicio local
- Opcional: Docker o Podman con compose (stack con Postgres)

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

### Uso diario: servicio local siempre activo (recomendado)

Pacioli corre como servicio de usuario de systemd: arranca al iniciar sesión, se reinicia solo
si falla y sirve la app compilada en **http://localhost:8000** (solo `127.0.0.1`). Los datos
viven en SQLite (`~/.local/share/pacioli`) y un timer hace un backup diario a las 03:00.

```bash
scripts/install-service.sh              # instala o actualiza (compila el frontend y reinicia)
scripts/install-service.sh --uninstall  # quita el servicio (los datos se conservan)

systemctl --user status pacioli         # estado
journalctl --user -u pacioli -f         # logs
systemctl --user list-timers pacioli-backup.timer
```

Después de hacer `git pull` o cambiar el código, vuelve a correr `scripts/install-service.sh`.
Las unidades están en [`deploy/systemd/`](deploy/systemd/).

### Desarrollo

```bash
./dev.sh
# API  → http://localhost:8001  (/docs)   ← 8001 para no chocar con el servicio en 8000
# Vite → http://localhost:5173  (proxy /api/* → :8001)
# Datos de desarrollo en ./.dev-data (nunca toca tus datos reales)
# Ctrl+C detiene ambos
```

### Contenedores (opcional, Postgres)

```bash
docker compose up -d --wait   # http://localhost:8000 (y Postgres en :5433)
```
Detén antes el servicio local (`systemctl --user stop pacioli`), porque ambos usan el puerto 8000.

---

## 💾 Datos

- **Ubicación:** SQLite en `~/.local/share/pacioli/pacioli.db` (`XDG_DATA_HOME` o `PACIOLI_DATA_DIR` lo sobreescriben). Compatible con `data/budget.db` del desktop: se importa una vez. Con `DATABASE_URL` los datos viven en PostgreSQL (volúmen `pgdata` del compose).
- **Backups diarios** con rotación (10) en `~/.local/share/pacioli/backups/`: al arrancar y con el timer `pacioli-backup` (`python -m app.cli backup`). Solo SQLite; Postgres no se respalda automáticamente.
- **Migraciones** (`SCHEMA_VERSION = 16`). Antes de migrar una base SQLite existente se guarda una copia `backups/pre-migration_vN-to-vM_<fecha>.db` (fuera de la rotación):
  - v11 `monthly_plans` (total del mes)
  - v12 `accounts.starting_cents` / `savings.opening_cents` (saldos iniciales fuera de mes)
  - v13 `transactions.installments` / `interest_bp`
  - v14 `savings.dividends_cents` + `matures_on` (derivado de `created_at + term_days`)
  - v15 `savings.category_id` (bolsillos como reserva de una categoría del presupuesto)
  - v16 `categories.role`: la categoría de sistema `savings` (🐷 Ahorro) agrupa los movimientos de ahorro; se busca por rol, se puede renombrar y no se puede borrar
- **Reglas de saldo:**
  - **Cuenta:** `starting + ingresos − gastos − pago_tc ± transferencias − ahorro + retiro`. Cualquier movimiento a un ahorro (bolsillo, programado, CDT o acciones) sale del saldo disponible de la cuenta; el retiro lo devuelve.
  - **Resumen mensual:** `total_expense = gasto + pago_tc` (cuota de tarjeta no es gasto hasta pagarla). `gasto_tc` no mueve caja; para presupuestos, gasto por categoría y listado cada cuota se atribuye al **mes en que se paga** su extracto (no al mes de compra): una compra después del corte cae en el mes siguiente.
  - **Tarjeta:** ciclo `6 sep → 5 oct` (exclusivo/inclusivo). Cada cuota (con interés) cuenta en el mes en que vence su extracto. `debt` (*por pagar ya*) = extractos cerrados sin pagar (pagos FIFO), `pending` = cuota del ciclo abierto, `outstanding` = Σ totales con interés − pagos, `available = limit − outstanding`. Detalle en [ADR 0001](docs/adr/0001-balance-semantics.md).

### 🐘 PostgreSQL (opcional)

SQLite sigue siendo el valor por defecto en desarrollo local. El stack de producción corre **app + Postgres juntos** en Podman (compose), con Postgres publicado en el host en el puerto **5433** (5432 lo ocupa otro servicio):

```bash
# 1) Levanta el stack completo (app 8000 + db host 5433)
podman-compose up -d --wait   # usa docker-compose.yml

# 2) (una vez) Migra tu SQLite actual a Postgres
DATABASE_URL=postgresql://pacioli:pacioli@localhost:5433/pacioli \
  backend/.venv/bin/python scripts/migrate_to_postgres.py

# 3) La app ya corre contra Postgres (DATABASE_URL lo inyecta compose)
curl -s http://localhost:8000/health
```

Datos de conexión: `postgresql://pacioli:pacioli@localhost:5433/pacioli` (host `localhost`, puerto `5433`, usuario `pacioli`, password `pacioli`, DB `pacioli`). Sin `DATABASE_URL` la app sigue usando SQLite.

En **VS Code**: instala **PostgreSQL** (`cweijan.vscode-postgresql-client2`), `Ctrl+Shift+P` → **PostgreSQL: Add Connection** → host `localhost`, puerto `5433`, usuario `pacioli`, password `pacioli`, DB `pacioli`. Después: Schemas → public → Tables.

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
cd backend && .venv/bin/ruff check . && .venv/bin/mypy app tests && .venv/bin/pytest -q

# Misma suite contra Postgres (¡borra el esquema public de esa BD!)
docker run -d --rm --name pacioli-test-pg -e POSTGRES_USER=pacioli -e POSTGRES_PASSWORD=pacioli \
  -e POSTGRES_DB=pacioli_test -p 127.0.0.1:55432:5432 postgres:16-alpine
PACIOLI_TEST_DATABASE_URL=postgresql://pacioli:pacioli@127.0.0.1:55432/pacioli_test .venv/bin/pytest -q

# Frontend
cd frontend && npx tsc -b && npm run lint && npm run build
```

Verificación visual con Chrome headless (`--screenshot`, `--virtual-time-budget`, `--remote-debugging-port` + `WebSocket` CDP) para dashboard, presupuestos, reportes, settings y formulario de transacción.

---

## 📜 Licencia

MIT — ver `LICENSE`.
