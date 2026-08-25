# Data Model: Plataforma Web GLOBTRADE

## Capas de datos (operativo vs estratégico)

Misma base MongoDB `globtrade_dw`, tres capas de acceso (`backend/shared/data_layers.py`):

| Capa | Colecciones típicas | Quién lee |
|------|---------------------|-----------|
| **Operativo** | `purchase_requests`, shop, inventario, OC, soporte, notifs | Vitrina, Ventas, Compras, Soporte |
| **Landing** | `sales_records` (+ espejos `orders` / `order_lines`) | Explorar ventas, export CSV, post-`convertir`, generate/CSV |
| **Estratégico** | `fact_ventas` + `dim_*` (+ `monthly_kpis`) | Tablero KPIs/gráficos, margen en Decisiones |

**Puente**: solicitud operativa → `convertir` escribe en **landing** (`sales_records`) con `analytics_stale=true` → admin ejecuta **Carga ELT / Construir modelo** → refresca **fact_ventas**. El Tablero no lee operativo ni landing para KPIs.

Meta API: `GET /api/meta/data-layers`.

## SalesRecord (landing)

Represents one sales order in `sales_records` (staging / histórico denormalizado).

**Fields**:
- `order_id`: unique business identifier.
- `region`, `country`: geographic classification.
- `item_type`: product category/type.
- `sales_channel`: sales channel.
- `order_priority`: priority value.
- `order_date`, `ship_date`: date strings used by filters and listados.
- `units_sold`: quantity sold.
- `unit_price`, `unit_cost`: pricing inputs.
- `total_revenue`, `total_cost`, `total_profit`: computed commercial metrics.

**Relationships**:
- Fuente del ELT hacia `fact_ventas` + dimensiones.
- Listados “Explorar ventas” y export CSV.
- No es la fuente de KPIs del Tablero (eso es `fact_ventas`).

**Validation Rules**:
- `order_id` must be present for detail/update/delete.
- Numeric values must be non-negative.
- Date fields must support chronological filtering.

## FactVenta (estratégico)

Hecho del modelo estrella en `fact_ventas`.

**Fields** (principales):
- `venta_id`, `order_id`
- `fecha_id`, `tiempo_id`
- `region_id`, `country_id`, `category_id`, `channel_id`, `priority_id`, `client_id`
- `units_sold`, `unit_price`, `unit_cost`
- `total_revenue`, `total_cost`, `total_profit`

**Relationships**:
- Joins lógicos a `dim_*` en agregaciones del Tablero / margen Decisiones.


## User

Represents an authenticated account in the users collection managed by
`backend/auth/users.py`.

**Fields**:
- `id` or Mongo `_id`: stable identifier.
- `email`: unique login identifier.
- `name`: display name.
- `password_hash`: stored credential hash.
- `role`: `analista` or `administrador`.
- `active`: whether the account can log in.

**Relationships**:
- Session stores public user id, email, name, and role.
- Role controls write/export/load permissions.

**Validation Rules**:
- Email must be normalized.
- Password must pass validators before account creation.
- First registered user may become administrator; later users default to analyst unless changed.

## Role

Represents allowed capability groups.

**Values**:
- `visitante`: unauthenticated read-only behavior.
- `analista`: authenticated read plus export/analysis capabilities when enabled.
- `administrador`: all analyst capabilities plus generate/build/load/CRUD actions.

## MasterTable

Represents a readable dimensional collection in MongoDB.

**Fields**:
- `name`: collection name, usually `dim_*`.
- `display_name`: Spanish label for UI.
- `fields`: visible columns.
- `records`: paginated result set.
- `active`: controla disponibilidad para operaciones nuevas sin eliminar el historial.

**Relationships**:
- Used by Q4 Datos master table browser and schema cards.

**Lifecycle Rules**:
- Los maestros editables se inhabilitan/reactivan; no se eliminan como operación normal.
- Regiones, Países, Canales y Prioridades son catálogos fijos: admiten edición e inhabilitación, pero no altas manuales.
- Los registros inactivos siguen disponibles para consultas e informes históricos.
- La eliminación física se bloquea cuando existen dimensiones hijas, pedidos o hechos relacionados.
- El ELT conserva el estado `active` al reconstruir dimensiones.
- Los proveedores también se habilitan/inhabilitan; nunca se borran como operación normal.
- Los ajustes manuales de inventario requieren motivo y registran valores anterior/nuevo en auditoría.
- `audit_log` conserva acción, módulo, entidad, referencia, actor, rol, fecha, detalle y diferencias `before/after`. Los campos sensibles se enmascaran antes de persistir el evento.
- Nombres, códigos y correos definidos como únicos se validan antes de crear o editar.

## FilterSelection

Represents UI-selected criteria for dashboard, analysis, and sales lists.

**Fields**:
- `region`
- `item_type`
- `channel`
- `priority`
- `country`
- `months`
- `limit`
- `offset`

**Validation Rules**:
- Empty filters are treated as no filter.
- `months=999` means all historical data.
- Pagination limits must stay within UI-defined options.

## AccountingDocument

Conserva documentos y controles contables sin eliminar movimientos históricos.

**Colecciones**:
- `invoices`: factura única por solicitud, con consecutivo `FAC-AAAA-NNNNNN`.
- `credit_notes`: contrapartida de devolución o ajuste, con consecutivo `NC-AAAA-NNNNNN` y motivo obligatorio.
- `cash_movements`: entradas por pago y salidas por devolución enlazadas con solicitud y pedido.
- `accounting_periods`: cierres diarios o mensuales con responsable, motivo y resumen financiero.

**Reglas**:
- La conciliación compara esperado, pagado, reembolsado y facturado; calcula el saldo pendiente.
- Un período cerrado bloquea nuevos movimientos de caja y notas de crédito dentro de sus fechas.
- Una nota de crédito no puede superar el valor pagado aún no devuelto.
- Las anulaciones financieras se realizan mediante movimientos de contrapartida, no borrando registros.
- El resumen expone ingresos, devoluciones, caja neta, costos, utilidad bruta, impuesto incluido y cuentas por cobrar.
- Los créditos conservan días y fecha de vencimiento; la cartera se clasifica en por vencer, 1–30, 31–60, 61–90 y más de 90 días.
- Los abonos parciales generan entradas de caja, actualizan el saldo y cambian el pago a `parcial` o `pagado` sin borrar movimientos previos.
- El estado de cuenta consolida cargos, pagos, devoluciones y saldo por cliente.
- El margen comercial puede agruparse por producto, cliente, canal o país.

## InventoryControl

Controla existencias en una única bodega, sin movimientos entre bodegas.

**Colecciones y campos**:
- `product_variants`: `inventory_quantity`, `minimum_stock` y `reorder_target` por SKU.
- `inventory_levels`: saldos `available` y `committed` de la bodega general.
- `inventory_scrapped`: unidades dañadas que no vuelven al disponible.
- `inventory_movements`: kardex append-only con tipo, cantidad, saldo anterior/nuevo, motivo, referencia, usuario y fecha.
- `inventory_counts`: conteos físicos aplicados, diferencia y responsable.

**Reglas**:
- En tránsito se calcula desde cantidades pendientes de OC enviadas o parcialmente recibidas.
- La reposición considera disponible menos comprometido, mínimo y objetivo configurados por variante.
- Los conteos y ajustes exigen motivo; nunca reescriben ni eliminan asientos anteriores del kardex.
- Las alertas de stock utilizan el mínimo específico del SKU cuando está configurado.
- El checkout reserva existencias mediante una actualización condicional atómica; dos compras simultáneas no pueden dejar saldo negativo.
- Una reserva de varias líneas es todo-o-nada: si una línea falla, se liberan las anteriores y se elimina el checkout incompleto.

## PaymentAttempt y RequestEvent

**PaymentAttempt** registra cada autorización de tarjeta con `attempt_id`, referencia de transacción, clave de idempotencia, solicitud, monto, resultado, marca, últimos cuatro dígitos y vencimiento. Nunca almacena PAN completo, CVV/CVC ni datos equivalentes.

**RequestEvent** forma la línea de tiempo append-only del pedido: creación, cambios de estado, autorización o rechazo de pago, conversión, devolución y reembolso.

**Reglas**:
- La clave de idempotencia es única y evita procesar dos veces el mismo intento.
- Solo una solicitud aprobada puede pagarse; envío, conversión y entrega requieren pago completo.
- Un pago en período contable cerrado se rechaza antes de modificar el pedido.
- Una devolución actualiza inventario apto/dañado, revierte ingresos, emite nota de crédito y registra `refund_status`.
- El comprobante expone referencia, monto, factura y tarjeta enmascarada.

## NotificationInbox y ReportExport

**NotificationInbox** conserva avisos por usuario con categoría, estado leído/no leído, fecha y referencias accionables a solicitudes, pagos, soporte u órdenes de compra. Admite búsqueda, paginación y conteos por categoría.

**ReportExport** registra cada descarga PDF o CSV con informe, tipo, formato, cantidad de filas, usuario, rol y fecha. Los CSV se generan en UTF-8 desde el servidor y neutralizan celdas que podrían ejecutarse como fórmulas al abrirse en una hoja de cálculo.
