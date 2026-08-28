# Data Model: Gestión Profesional en 11 Fases

## ManagementGoal (`management_goals`)

- `goal_id`: entero incremental, único.
- `name`: nombre visible, 3–100 caracteres.
- `metric`: `revenue`, `orders`, `profit` o `margin`.
- `period_start`, `period_end`: fechas ISO; inicio no posterior al fin.
- `target`: número positivo.
- `actual`: valor calculado desde datos existentes.
- `status`: `active` o `closed`.
- `owner_email`, `created_at`, `updated_at`: trazabilidad.

Transición: `active -> closed`. El avance es `actual / target`.

## ApprovalRequest (`management_approvals`)

- `approval_id`: entero incremental, único.
- `type`: tipo de decisión administrativa.
- `title`, `reason`: explicación humana.
- `reference`, `amount`: referencia opcional y monto no negativo.
- `status`: `pending`, `approved` o `rejected`.
- `requester_email`, `reviewer_email`: participantes.
- `created_at`, `decided_at`, `comment`: trazabilidad.

Transiciones: `pending -> approved` o `pending -> rejected`; los estados finales no se reabren.

## Read Models

- `ProfessionalHome`: rol, KPIs, pendientes y accesos rápidos.
- `ActionAlert`: gravedad, causa, valor y destino.
- `ProductProfile`: identidad, margen, inventario, proveedor, ventas y movimientos.
- `CustomerProfile`: identidad, segmento, pedidos, gasto y actividad.
- `VendorScore`: identidad, órdenes, monto, recepción y calificación.
- `SourceHealth`: fuente, estado, registros, actualización y detalle.
- `GlobalSearchResult`: tipo, id, título, subtítulo y destino.
- `ShipmentOverview`: estado, transportista, guía, fecha estimada y tiempo medio.
- `DemandForecast`: promedio mensual, existencias, cobertura y reposición sugerida.
- `AdjustedProfitability`: utilidad analítica menos devoluciones, logística y merma.
- `LoyaltyProfile`: frecuencia, valor, actividad, segmento y acción sugerida.
- `DataQualityIssue`: regla empresarial, colección afectada y cantidad de incidencias.
- `InventoryLot`: variante, código de lote, cantidades recibida/disponible, recepción y caducidad.
- `LotMovement`: lote, variante, tipo de movimiento, cantidad y referencia a pedido u orden de compra.
- `PriceList`: alcance cliente/canal, vigencia, estado y precios por producto.
- `ReturnEvent`: devolución parcial, líneas aptas/dañadas, monto reembolsado y responsable.
- `SalesGoal`: vendedor, período, meta, porcentaje y comisión calculada sobre ventas netas.
- `UsabilityFeedback`: tareas completadas, calificación, observación, participante y fecha.

## Relationships

- Producto → variantes → inventario/movimientos y líneas de venta.
- Producto → proveedor.
- Cliente → pedidos/solicitudes → pagos y ventas.
- Proveedor → órdenes de compra → líneas.
- Auditoría → entidad e identificador.
- Variante → lotes → movimientos FEFO → pedido/devolución.
- Cliente o canal → lista de precios → producto → precio aplicado en checkout.
