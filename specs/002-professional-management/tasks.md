# Tasks: Gestión Profesional en 11 Fases

**Input**: Design documents from `/specs/002-professional-management/`

**Tests**: Se incluyen pruebas porque cada fase debe poder verificarse independientemente.

## Phase 1: Setup

- [X] T001 Registrar el nuevo paquete y recursos frontend en `frontend/app.py` y `frontend/static/index.html`

## Phase 2: Foundational

- [X] T002 Crear helpers, validación y proyecciones compartidas en `paquetes/profesional/services.py`
- [X] T003 Crear contratos HTTP y manejo de errores en `paquetes/profesional/routes.py`

## Phase 3: Fase 1 — Inicio por rol (US1)

**Independent Test**: El resumen cambia accesos y pendientes al cambiar el rol.

- [X] T004 [US1] Implementar resumen personalizado en `paquetes/profesional/services.py`
- [X] T005 [US1] Renderizar inicio por rol en `frontend/static/js/profesional.js`

## Phase 4: Fase 2 — Alertas (US2)

**Independent Test**: Cada alerta contiene gravedad, explicación y acción.

- [X] T006 [US2] Implementar agregación de alertas en `paquetes/profesional/services.py`
- [X] T007 [US2] Renderizar centro de alertas en `frontend/static/js/profesional.js`

## Phase 5: Fase 3 — Productos 360 (US3)

**Independent Test**: Una ficha existente reúne identidad, margen, stock, proveedor e historial.

- [X] T008 [US3] Implementar ficha integral de producto en `paquetes/profesional/services.py`
- [X] T009 [US3] Implementar buscador y ficha de producto en `frontend/static/js/profesional.js`

## Phase 6: Fase 4 — Clientes 360 (US4)

**Independent Test**: Una ficha de cliente muestra segmento, actividad y valor.

- [X] T010 [US4] Implementar ficha integral de cliente en `paquetes/profesional/services.py`
- [X] T011 [US4] Implementar buscador y ficha de cliente en `frontend/static/js/profesional.js`

## Phase 7: Fase 5 — Proveedores (US5)

**Independent Test**: Proveedores aparecen con indicadores comparables y calificación explicada.

- [X] T012 [US5] Implementar evaluación de proveedores en `paquetes/profesional/services.py`
- [X] T013 [US5] Renderizar tabla de evaluación en `frontend/static/js/profesional.js`

## Phase 8: Fase 6 — Metas (US6)

**Independent Test**: Una meta válida se persiste y muestra avance y brecha.

- [X] T014 [US6] Implementar persistencia y cálculo de metas en `paquetes/profesional/services.py`
- [X] T015 [US6] Implementar formulario y tablero de metas en `frontend/static/js/profesional.js`

## Phase 9: Fase 7 — Aprobaciones (US7)

**Independent Test**: Una solicitud pasa una sola vez de pendiente a aprobada o rechazada.

- [X] T016 [US7] Implementar ciclo de aprobaciones en `paquetes/profesional/services.py`
- [X] T017 [US7] Implementar bandeja y acciones de aprobación en `frontend/static/js/profesional.js`

## Phase 10: Fase 8 — Historial (US8)

**Independent Test**: Los eventos se filtran por entidad y muestran actor, fecha y cambio.

- [X] T018 [US8] Implementar historial legible en `paquetes/profesional/services.py`
- [X] T019 [US8] Renderizar filtros y línea temporal en `frontend/static/js/profesional.js`

## Phase 11: Fase 9 — Calidad de datos (US9)

**Independent Test**: Cada fuente muestra estado, cantidad y actualización sin bloquear otras fuentes.

- [X] T020 [US9] Implementar monitor de fuentes en `paquetes/profesional/services.py`
- [X] T021 [US9] Renderizar monitor de calidad en `frontend/static/js/profesional.js`

## Phase 12: Fase 10 — Búsqueda global (US10)

**Independent Test**: Una consulta válida devuelve resultados agrupados de cuatro dominios.

- [X] T022 [US10] Implementar búsqueda agrupada en `paquetes/profesional/services.py`
- [X] T023 [US10] Implementar buscador global navegable en `frontend/static/js/profesional.js`

## Phase 13: Fase 11 — Experiencia consistente (US11)

**Independent Test**: Las once pestañas son legibles y adaptables y comparten estados visuales.

- [X] T024 [US11] Crear estructura de consola y once pestañas en `frontend/static/index.html`
- [X] T025 [US11] Crear sistema visual adaptable en `frontend/static/css/profesional.css`

## Phase 14: Validation

- [X] T026 [P] Crear pruebas de servicios y contratos en `tests/test_professional_center.py`
- [X] T027 Ejecutar pruebas y recorrido definido en `specs/002-professional-management/quickstart.md`

## Phase 15: Extensión operativa solicitada (puntos 3–11)

- [X] T028 Implementar seguimiento y resumen logístico en `paquetes/profesional/services.py`
- [X] T029 Implementar pronóstico explicable de demanda y reposición sugerida en `paquetes/profesional/services.py`
- [X] T030 Ampliar evaluación de proveedores con puntualidad y plazo medio en `paquetes/profesional/services.py`
- [X] T031 Implementar rentabilidad ajustada por descuentos, devoluciones, logística y merma en `paquetes/profesional/services.py`
- [X] T032 Implementar segmentación de fidelización y acciones recomendadas en `paquetes/profesional/services.py`
- [X] T033 Programar publicación estratégica diaria a ClickHouse en `airflow/dags/globtrade_strategic_etl.py`
- [X] T034 Añadir reglas de validación de calidad de datos en `paquetes/profesional/services.py`
- [X] T035 Reforzar experiencia móvil en `frontend/static/css/profesional.css`
- [X] T036 Exponer la operación avanzada y sus pruebas en `paquetes/profesional/routes.py`, `frontend/static/js/profesional.js` y `tests/test_professional_center.py`

## Phase 16: Acciones gerenciales solicitadas (puntos 2–10)

- [X] T037 Graficar pronóstico mensual y confianza en `frontend/static/js/profesional.js`
- [X] T038 Convertir reposición sugerida en requisición de compra en `paquetes/profesional/services.py`
- [X] T039 Detectar y mostrar alertas automáticas de atrasos logísticos en `paquetes/profesional/services.py`
- [X] T040 Crear campañas segmentadas de fidelización en `paquetes/profesional/services.py`
- [X] T041 Comparar rentabilidad por producto, categoría, cliente y región en `paquetes/profesional/services.py`
- [X] T042 Medir objetivo logístico y cumplimiento de entregas en `paquetes/profesional/services.py`
- [X] T043 Mostrar vigencia de MongoDB y ClickHouse en `paquetes/profesional/services.py`
- [X] T044 Exportar la vista ejecutiva en PDF desde `paquetes/profesional/routes.py`
- [X] T045 Añadir pruebas del recorrido acciones → resultados en `tests/test_professional_center.py`

## Phase 17: Inventario y venta profesional pendientes

- [X] T046 Gestionar lotes, caducidad, FEFO y trazabilidad en `backend/shared/inventory_lots.py`
- [X] T047 Integrar lotes con recepciones, ventas y devoluciones en `paquetes/compras/services.py`, `paquetes/shop/services.py` y `paquetes/ventas/services.py`
- [X] T048 Implementar listas de precios por cliente o canal en `backend/shared/price_lists.py`
- [X] T049 Aplicar la lista de precios correspondiente durante checkout en `paquetes/shop/services.py`
- [X] T050 Permitir devoluciones parciales repetibles por producto en `paquetes/ventas/services.py` y `frontend/static/js/q3-ventas.js`
- [X] T051 Añadir monitor visible de ClickHouse y gestión UI en `paquetes/profesional/routes.py` y `frontend/static/js/profesional.js`
- [X] T052 Validar contratos y casos parciales en `tests/test_professional_center.py` y `tests/test_smoke.py`

## Phase 18: Precios, vendedores y usabilidad

- [X] T053 Ampliar listas de precios a múltiples productos y ajustes porcentuales en `backend/shared/price_lists.py`
- [X] T054 Implementar metas, ventas netas y comisiones por vendedor en `backend/shared/sales_performance.py`
- [X] T055 Crear recorrido guiado y registro de pruebas de uso en `frontend/static/js/profesional.js`
- [X] T056 Exponer contratos y validar los tres recorridos en `paquetes/profesional/routes.py` y `tests/test_professional_center.py`

## Phase 19: Rendimiento del Centro de decisiones

- [X] T057 Mover rankings de margen y canal desde MongoDB masivo a ClickHouse en `paquetes/decisiones/services.py`
- [X] T058 Ejecutar cálculos operativos y contables en paralelo sin compartir la sesión ClickHouse en `paquetes/decisiones/services.py`
- [X] T059 Añadir caché por filtros de 90 segundos y validar el panel con datos reales

## Phase 20: Corrección integral de Decisiones

- [X] T060 Corregir el origen de existencias infladas en la sincronización del catálogo
- [X] T061 Normalizar de forma no destructiva inventarios históricos corruptos en los cálculos estratégicos
- [X] T062 Corregir capital en riesgo, rotación, cobertura y señalización de datos estimados
- [X] T063 Rediseñar escalas, cuadrantes, etiquetas y tarjetas de la matriz de portafolio
- [X] T064 Validar cálculos y contratos con ClickHouse real y pruebas automatizadas

## Phase 21: Conciliación, cierre y recuperación

- [X] T065 Implementar conciliación por conteo físico sin reemplazo automático de existencias
- [X] T066 Crear cierre gerencial mensual con resumen financiero, inventario y comisiones
- [X] T067 Mostrar catálogo de respaldos verificados en Gestión profesional
- [X] T068 Crear restauración protegida con confirmación exacta y respaldo preventivo
- [X] T069 Validar sintaxis y contratos; pruebas Docker pendientes si el motor está apagado

## Phase 22: Calidad integral de gestión y experiencia

- [X] T070 Automatizar la línea de catálogo y ocultar entidades inhabilitadas de operaciones nuevas
- [X] T071 Validar precios, costos, cantidades y datos de perfil en cliente y servidor
- [X] T072 Unificar semántica de Cerrar/Cancelar y rediseñar detalle de pedido y kardex
- [X] T073 Hacer funcionales los filtros de Mis pedidos e incorporar devoluciones visibles
- [X] T074 Revisar preferencias de idioma y agregar visibilidad controlada a todas las contraseñas
- [X] T075 Ejecutar pruebas de regresión y recorrido visual de los nueve casos solicitados

## Phase 23: Selectores avanzados globales

- [X] T076 Sustituir selectores nativos por un cuadro global con búsqueda y selección accesible
- [X] T077 Detectar selectores dinámicos y conservar sus eventos y validaciones existentes
- [X] T078 Añadir filtros contextuales por proveedor, país, disponibilidad y grupo alfabético
- [X] T079 Validar regresión, búsqueda, selección y diseño responsivo
- [X] T080 Enriquecer selectores por categoría, proveedor, disponibilidad, región, país y área funcional
- [X] T081 Propagar la inhabilitación de categorías y productos a la tienda y a operaciones nuevas
- [X] T082 Resaltar claramente la categoría seleccionada en el catálogo

## Dependencies & Execution Order

- Setup → Foundational → fases 1–11 → Validation.
- Las fases de lectura pueden comprobarse independientemente después de Foundational.
- Metas y aprobaciones requieren sus endpoints de escritura antes de probar su UI.

## Parallel Opportunities

- T026 puede escribirse mientras se completa la UI.
- Las proyecciones de productos, clientes y proveedores son independientes.

## Implementation Strategy

Entregar una sola consola navegable, activar cada fase en orden y comprobar que cada una conserva un estado vacío útil. No se añade ninguna fase de seguridad empresarial.
