# API Contracts: Plataforma Web GLOBTRADE

Base prefix for application endpoints: `/api`

## Shared Authentication

### POST `/api/auth/register`

Creates an account. The first user may become administrator; subsequent users are
analysts unless changed by project logic.

**Body**: `email`, `password`, `password_confirm`, `name`

**Success**: `201` with `status`, `message`, `user`

### POST `/api/auth/login`

Starts a session.

**Body**: `email` or `username`, `password`

**Success**: `200` with `status`, `message`, `user`

### POST `/api/auth/logout`

Clears the session.

**Success**: `200` with `status`, `message`

### GET `/api/auth/me`

Returns current authentication state.

**Success**: `200` with `authenticated` and `user`

## Q1 Tablero

### GET `/api/summary`

Returns dashboard KPIs. Public read.

**Query**: `region`, `item_type`, `channel`, `priority`, `months`

### GET `/api/regions`, `/api/products`, `/api/trend`, `/api/channels`, `/api/priorities`, `/api/countries`

Returns chart datasets. Public read.

**Query**: common filters; `/trend` accepts `months`; `/countries` accepts `top`.

### GET `/api/orders`

Returns paginated sales records. Public read.

**Query**: `country`, `item_type`, `channel`, `priority`, `region`, `limit`, `offset`

### GET `/api/orders/count`

Returns count for the current sales filters. Public read.

### POST `/api/sales_records/generate`

Generates sales records. Administrator required.

**Body**: `count`

## Q3 Ventas

### GET `/api/sales/orders`

Returns paginated order list for the Ventas page. Public read.

**Query**: `country`, `item_type`, `channel`, `priority`, `region`, `limit`, `offset`

### GET `/api/sales/orders/{order_id}`

Returns order detail. Public read.

### POST `/api/sales/orders`

Creates an order. Administrator required.

### PUT `/api/sales/orders/{order_id}`

Updates an order. Administrator required.

### DELETE `/api/sales/orders/{order_id}`

Deletes an order. Administrator required.

## Q2 Analisis

### GET `/api/analysis/trend`

Returns trend analysis dataset. Public read.

### GET `/api/analysis/regions`

Returns region and country analysis dataset. Public read.

### GET `/api/analysis/products`

Returns product analysis dataset. Public read.

### GET `/api/analysis/export`

Exports analysis data. Authenticated analyst or administrator required.

## Q4 Datos

### GET `/api/master/tables`

Lists available master/dimensional collections. Public read.

### GET `/api/master/{name}`

Returns paginated rows for a master table. Public read.

**Query**: `limit`, `offset`, búsqueda opcional y `active=true|false` para filtrar estado.

La creación mediante `POST /api/master/{name}` devuelve `403 fixed_catalog` para
`dim_region`, `dim_pais`, `dim_canal` y `dim_prioridad`. Estos catálogos solo
admiten edición y cambio de estado.

### PATCH `/api/master/{name}/{row_id}/status`

Habilita o inhabilita un registro maestro sin eliminar su historial. Requiere permiso `masters.write`.

**Body**: `{ "active": true|false }`

**Success**: `200` con `status`, `message` y `row` actualizado.

### GET `/api/schema`

Returns schema/model summary cards. Public read.

### POST `/api/build_model`

Runs model build or dimensional transformation. Administrator required.

### POST `/api/load_dataset`

Runs dataset load. Administrator required.

### GET `/api/elt_status`

Returns current data/ELT status. Public read.

## Seguridad operativa

- El acceso limita intentos de inicio de sesión por dirección IP y por cuenta mediante una operación segura ante solicitudes concurrentes.
- CORS solo responde a los orígenes configurados en `CORS_ORIGINS`; las respuestas incluyen CSP y cabeceras defensivas.
- En `APP_ENV=production`, el arranque exige `FLASK_SECRET_KEY` fuerte y cookies seguras.
- `PATCH /api/compras/vendors/{vendor_id}/status`: habilita o inhabilita un proveedor; al inhabilitar exige motivo.
- `DELETE /api/compras/vendors/{vendor_id}`: no elimina y devuelve conflicto indicando que debe inhabilitarse.
- `PATCH /api/compras/inventory/{variant_id}`: todo ajuste manual exige `reason` de al menos ocho caracteres y se audita.
- La sesión autenticada expira por inactividad según `SESSION_IDLE_MINUTES` (120 minutos por defecto).

## Control contable

Todos los endpoints requieren sesión y permiso `compras.manage`.

- `GET /api/compras/accounting/summary`: ingresos, devoluciones, costos, utilidad, impuestos y cartera.
- `GET /api/compras/accounting/receivables`: solicitudes aprobadas con saldo pendiente.
- `GET /api/compras/accounting/customers/{email}/statement`: estado de cuenta consolidado del cliente.
- `POST /api/compras/accounting/receivables/{request_id}/payments`: registra un abono parcial con monto y referencia única.
- `GET /api/compras/accounting/margins?group_by=product|customer|channel|country`: análisis de ingresos, costos, utilidad y margen.
- `GET /api/compras/accounting/reconciliation/{request_id}`: concilia pedido, pago, factura y caja; emite la factura si corresponde y aún no existe.
- `GET /api/compras/accounting/periods`: lista cierres contables.
- `POST /api/compras/accounting/periods/close`: cierra un día (`daily`, `AAAA-MM-DD`) o mes (`monthly`, `AAAA-MM`) con motivo.
- `GET /api/compras/accounting/credit-notes`: lista notas de crédito.
- `POST /api/compras/accounting/credit-notes`: emite una contrapartida con `request_id`, `amount` y `reason`.

Los intentos de registrar movimientos en períodos cerrados devuelven conflicto; los documentos conservan consecutivos únicos y trazabilidad de usuario/fecha.

## Control de inventario

- `GET /api/compras/inventory`: incluye disponible, comprometido, dañado, en tránsito, mínimo, objetivo y reposición sugerida por variante.
- `GET /api/compras/inventory/{variant_id}/kardex`: devuelve los asientos inmutables más recientes del SKU.
- `PATCH /api/compras/inventory/{variant_id}/policy`: configura `minimum` y `target`; el objetivo no puede ser menor al mínimo.
- `POST /api/compras/inventory/{variant_id}/physical-count`: aplica `counted` con `reason`, registra la diferencia y genera su asiento de kardex.

No existe endpoint de modificación o eliminación de movimientos del kardex. Esta fase excluye expresamente los movimientos entre bodegas.

## Pedidos, pagos y devoluciones

- `POST /api/solicitudes/{request_id}/pagar`: autoriza el pago del cliente con `idempotency_key` y metadatos seguros `card` (`brand`, `last4`, `exp_month`, `exp_year`).
- `POST /api/solicitudes/{request_id}/registrar-pago`: equivalente autorizado para personal con `ventas.manage` cuando aplica.
- `POST /api/solicitudes/{request_id}/intentos-pago`: registra rechazos sin cambiar el pedido a pagado.
- `GET /api/solicitudes/{request_id}/timeline`: línea de tiempo visible para el dueño o personal autorizado.
- `GET /api/solicitudes/{request_id}/comprobante`: comprobante del pago aprobado con tarjeta enmascarada y número de factura.
- `POST /api/solicitudes/{request_id}/devolver`: integra inspección, inventario, reversión financiera, nota de crédito y estado de reembolso.

El API rechaza expresamente cualquier payload que contenga PAN completo, número de tarjeta, CVV o CVC. Los intentos repetidos con la misma clave no generan un segundo cobro.

## Notificaciones y exportaciones

- `GET /api/auth/notifications`: acepta `limit`, `offset`, `unread`, `category` y `q`; devuelve avisos, total filtrado, total no leído y conteos por categoría.
- `POST /api/auth/notifications/read-category`: marca leída una categoría concreta del usuario autenticado.
- `GET /api/reportes/{report_id}/csv`: exporta hasta 2000 filas del informe simple respetando búsqueda y umbral.
- `GET /api/compuestos/{report_id}/csv`: exporta hasta 2000 filas del informe compuesto.
- `GET /api/reportes/exportaciones`: historial de exportaciones para usuarios con `audit.read`.

Las exportaciones PDF y CSV requieren `reportes.view` y `analysis.export`, conservan trazabilidad y los resultados consultados incluyen `generated_at`.

## Salud, errores y respaldos

- `GET /api/health`: comprobación pública mínima de disponibilidad de MongoDB.
- `GET /api/health/details`: diagnóstico para administrador con topología, errores abiertos y último respaldo verificado.
- `GET /api/backups`: consulta administrativa de manifiestos; no permite descargar, restaurar ni eliminar respaldos.

Cada respuesta web incluye `X-Request-ID` y `Server-Timing`. Los errores inesperados se registran en `system_errors` y el cliente recibe un mensaje neutro con el identificador para soporte.
## Auditoría administrativa

- `GET /api/audit_log`: requiere `audit.read`; admite `role`, `email`, `module`, `action`, `entity`, `entity_id`, `date_from`, `date_to`, `limit` y `offset`.
- `GET /api/audit_log/export`: requiere `audit.read`; aplica los mismos filtros y entrega hasta 5.000 eventos en CSV UTF-8 compatible con Excel.
- Los eventos nuevos incluyen `module`, `details` y `changes`, donde cada cambio contiene `before` y `after`. Contraseñas, secretos, tokens, CVV y números de tarjeta se almacenan como `[PROTEGIDO]`.
