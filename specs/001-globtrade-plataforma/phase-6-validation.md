# Validación final — Fase 6

Fecha: 2026-08-24 (America/Guayaquil)

## Resultado automatizado

- Suite: `tests/test_smoke.py`
- Resultado: 100 aprobadas, 0 fallidas.
- Duración: 80.63 segundos en Docker.
- Cobertura funcional: permisos por rol, dinero, períodos contables, inventario, pagos idempotentes, reportes, notificaciones, respaldos y errores.

## Recorrido visual y accesibilidad

- Portada cargada en `http://127.0.0.1:5001/` con 100 productos.
- Un único `h1`, sin identificadores duplicados y sin imágenes carentes de `alt`.
- Control de precio corregido con nombre accesible.
- Vista móvil 390 × 844: carrito visible y sin desbordamiento horizontal.
- Los recorridos autenticados se validaron mediante clientes Flask por rol para no manejar credenciales en el navegador.

## Rendimiento local observado

- Documento principal: 240 ms, HTTP 200.
- Salud: 60 ms, HTTP 200.
- Catálogo de 100 productos: 135 ms, HTTP 200.
- Cabeceras confirmadas: `X-Request-ID` y `Server-Timing`.

## Respaldo

- Bases: `globtrade_ops` y `globtrade_dw`.
- Resultado: 166 archivos y manifiesto verificado.
- Identificador: `globtrade-20260824-192304`.
- Consulta segura disponible para administrador; la API no restaura ni elimina datos.

## Exclusión

No se implementaron movimientos ni transferencias entre bodegas.
# Validación posterior — Fase 3 comercial (2026-08-24)

- Límites de pedido, límite individual y margen mínimo: aprobado.
- Excepciones: alcance exacto, monto máximo y consumo único: aprobado.
- Cupones: vigencia, pedido mínimo, segmento y límite de usos concurrente: aprobado.
- Crédito: habilitación y cupo disponible: aprobado.
- Inventario: reserva concurrente y reversión completa por lote: aprobado.
- Respuesta API de autorización comercial: `409 commercial_exception_required`: aprobado.
- Resultado de regresión: **115 pruebas aprobadas, 0 fallos**.

Defectos corregidos durante la ejecución:

1. Una excepción podía cubrir incumplimientos diferentes de los aprobados.
2. El límite de usos de un cupón no se consumía de forma atómica.
3. El checkout devolvía un error genérico ante una política comercial bloqueante.
4. Crédito deshabilitado o excedido no tenía un mensaje específico para el usuario.

## Validación posterior — Fase 4 contable (2026-08-24)

- Antigüedad de cartera y vencimientos: aprobado.
- Abonos parciales, referencia duplicada y liquidación total: aprobado.
- Estado de cuenta consolidado: aprobado.
- Margen por dimensiones comerciales: aprobado.
- Sintaxis de las interfaces de Caja y Gestión comercial: aprobada.
- Resultado de regresión: **119 pruebas aprobadas, 0 fallos**.

## Validación posterior — Fase 5 auditoría administrativa (2026-08-24)

- Se incorporó comparación anterior/nueva y clasificación por módulo con enmascaramiento preventivo de credenciales y tarjeta.
- La interfaz permite filtrar por usuario, rol, módulo, acción y fechas, consultar el detalle y exportar el resultado para Excel.
- Pruebas específicas de auditoría: `6 passed`.
- Regresión completa: `121 passed in 97.68s`.

## Validación posterior — Fase 6 experiencia y accesibilidad (2026-08-24)

- Navegación por teclado: enlace para saltar al contenido y foco visible uniforme.
- SPA: cada cambio actualiza el título del documento y se anuncia mediante una región viva.
- Modales: semántica de diálogo, etiqueta por título, foco inicial, ciclo con Tab y retorno al control de origen.
- Formularios: asociación de etiquetas visuales con sus controles, incluyendo componentes creados dinámicamente.
- Preferencias del sistema: movimiento reducido y alto contraste respetados.
- Sintaxis JavaScript: aprobada.
- Pruebas específicas: `7 passed`.
- Regresión completa: `122 passed in 90.81s`.

## Validación posterior — Fase 7 documentación y preparación final (2026-08-24)

- Manual de operación y entrega consolidado con instalación, roles, reglas, respaldo, recuperación y límites de integración.
- README y plan de pruebas actualizados al flujo vigente.
- Verificador no destructivo: `ready: true`; archivos, aplicación, salud y MongoDB aprobados.
- Bases verificadas: operativo con 41 colecciones y analítico con 44 colecciones.
- Pruebas específicas de entrega: `2 passed`.
- Regresión completa final: `123 passed in 86.32s`.

## Validación posterior — reemplazo del histórico analítico (2026-08-24)

- Respaldo previo verificado: `globtrade-20260824-205050`, 172 archivos.
- Histórico anterior eliminado: 1.500.156 filas de landing y hechos, más sus indicadores mensuales.
- Histórico vigente: 2.000.000 filas en `sales_records` y 2.000.000 hechos sincronizados.
- Rango: 2010-01-01 a 2026-08-24; 200 meses continuos, sin fechas futuras ni meses en cero.
- Volumen mensual: mínimo 8.118 y máximo 12.854; crecimiento y estacionalidad moderados.
- API `/api/trend?months=999`: 200 puntos, primero 2010-01, último 2026-08.
- Regresión completa: `125 passed in 126.35s`.
