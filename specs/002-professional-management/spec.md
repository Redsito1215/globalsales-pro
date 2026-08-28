# Feature Specification: Gestión Profesional en 11 Fases

**Feature Branch**: `002-professional-management`

**Created**: 2026-08-26

**Status**: Approved

**Input**: User description: "Profesionalizar Altavia Trade en 11 fases; no agregar seguridad empresarial."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inicio personalizado por rol (Priority: P1)

Como usuario interno quiero abrir el sistema y ver primero las cifras, pendientes y accesos que corresponden a mi función para comenzar a trabajar sin recorrer módulos irrelevantes.

**Why this priority**: Reduce el tiempo diario de orientación y convierte la plataforma en una herramienta de gestión.

**Independent Test**: Iniciar sesión con dos roles distintos y comprobar que cada uno recibe tarjetas y accesos rápidos diferentes.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado, **When** abre Inicio profesional, **Then** ve un resumen adaptado a su rol.
2. **Given** un usuario sin datos disponibles, **When** abre Inicio, **Then** ve estados vacíos claros y accesos útiles.

---

### User Story 2 - Centro de alertas accionables (Priority: P1)

Como gerente quiero ver alertas priorizadas con causa y acción sugerida para atender riesgos comerciales y operativos.

**Independent Test**: Consultar el centro con inventario bajo o pedidos pendientes y comprobar prioridad, explicación y enlace de acción.

**Acceptance Scenarios**:

1. **Given** una condición que requiere atención, **When** se carga el centro, **Then** aparece una alerta con gravedad, métrica y acción.
2. **Given** ausencia de incidencias, **When** se carga el centro, **Then** se comunica que no hay alertas críticas.

---

### User Story 3 - Ficha integral de producto (Priority: P1)

Como gerente comercial quiero consultar en una sola ficha ventas, margen, inventario, proveedor e historial de un producto.

**Independent Test**: Buscar un producto existente y validar que la ficha reúne identidad, métricas y movimientos relacionados.

**Acceptance Scenarios**:

1. **Given** un producto existente, **When** se abre su ficha, **Then** se presenta una vista consolidada y trazable.
2. **Given** un identificador inexistente, **When** se solicita la ficha, **Then** se informa sin romper la vista.

---

### User Story 4 - Ficha integral de cliente (Priority: P2)

Como responsable comercial quiero conocer compras, pedidos, valor y comportamiento de un cliente para atenderlo mejor.

**Independent Test**: Buscar un cliente y validar el resumen de actividad, segmentación e historial reciente.

**Acceptance Scenarios**:

1. **Given** un cliente registrado, **When** se abre su ficha, **Then** se muestran sus indicadores e interacciones.

---

### User Story 5 - Evaluación de proveedores (Priority: P2)

Como responsable de compras quiero comparar proveedores por actividad, órdenes, monto y cumplimiento para decidir a quién comprar.

**Independent Test**: Abrir la evaluación y comprobar que cada proveedor tiene indicadores comparables y estado.

**Acceptance Scenarios**:

1. **Given** proveedores con órdenes, **When** se consulta la evaluación, **Then** se ordenan mediante métricas consistentes.

---

### User Story 6 - Metas y presupuesto (Priority: P2)

Como gerente quiero registrar metas por periodo y comparar avance real contra objetivo.

**Independent Test**: Crear una meta, recargar la vista y validar porcentaje de avance y brecha.

**Acceptance Scenarios**:

1. **Given** un periodo y objetivo válidos, **When** se guarda la meta, **Then** queda disponible con avance calculado.
2. **Given** datos incompletos, **When** se intenta guardar, **Then** se muestra una validación comprensible.

---

### User Story 7 - Flujos de aprobación (Priority: P2)

Como gerente quiero revisar solicitudes de aprobación de operaciones sensibles del negocio antes de su ejecución.

**Independent Test**: Crear una solicitud, aprobarla o rechazarla y comprobar su cambio de estado e historial.

**Acceptance Scenarios**:

1. **Given** una solicitud pendiente, **When** un responsable toma una decisión, **Then** se registra decisión, responsable y fecha.

---

### User Story 8 - Historial visible por registro (Priority: P3)

Como supervisor quiero consultar cambios de productos, clientes, proveedores y operaciones desde una vista comprensible.

**Independent Test**: Filtrar el historial por entidad y verificar actor, fecha, acción y cambios.

**Acceptance Scenarios**:

1. **Given** eventos registrados, **When** se filtra por entidad, **Then** solo aparecen eventos relacionados y legibles.

---

### User Story 9 - Calidad y actualización de datos (Priority: P2)

Como analista quiero conocer vigencia, volumen y problemas básicos de las fuentes para confiar en los informes.

**Independent Test**: Abrir el monitor y validar que cada fuente muestra registros, última actualización y estado.

**Acceptance Scenarios**:

1. **Given** fuentes disponibles o caídas, **When** se abre el monitor, **Then** cada fuente comunica su estado sin bloquear las demás.

---

### User Story 10 - Búsqueda global (Priority: P2)

Como usuario interno quiero buscar productos, clientes, proveedores y pedidos desde un único campo y navegar al resultado.

**Independent Test**: Buscar por nombre o identificador y validar resultados agrupados por tipo.

**Acceptance Scenarios**:

1. **Given** una consulta de dos o más caracteres, **When** se ejecuta la búsqueda, **Then** aparecen coincidencias agrupadas y limitadas.

---

### User Story 11 - Experiencia visual consistente (Priority: P3)

Como usuario quiero que estas herramientas mantengan una presentación clara, adaptable y consistente con Altavia Trade.

**Independent Test**: Recorrer las once pestañas en escritorio y pantalla estrecha verificando jerarquía, estados y legibilidad.

**Acceptance Scenarios**:

1. **Given** cualquiera de las once fases, **When** se visualiza, **Then** usa los mismos patrones de filtros, tarjetas, tablas y estados.

### Edge Cases

- Una fuente de datos puede estar vacía o temporalmente inaccesible; el resto del centro debe seguir funcionando.
- Los identificadores pueden llegar como números o texto y deben normalizarse antes de buscar.
- Una meta puede no disponer aún de datos reales; su avance se presenta como cero, no como error.
- La búsqueda global no se ejecuta con consultas vacías o de un solo carácter.
- Una aprobación ya resuelta no puede decidirse por segunda vez.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST ofrecer un espacio de gestión profesional dividido exactamente en 11 fases visibles.
- **FR-002**: El inicio MUST adaptar indicadores y accesos al rol autenticado.
- **FR-003**: El sistema MUST producir alertas con gravedad, causa, valor observado y acción sugerida.
- **FR-004**: El sistema MUST consolidar la ficha de producto con datos comerciales, inventario, proveedor e historial disponible.
- **FR-005**: El sistema MUST consolidar la ficha de cliente con segmentación, pedidos, compras e historial disponible.
- **FR-006**: El sistema MUST comparar proveedores con métricas homogéneas y una calificación explicable.
- **FR-007**: Los usuarios autorizados MUST poder crear, consultar y actualizar metas de ventas o margen por periodo.
- **FR-008**: Los usuarios autorizados MUST poder crear solicitudes y resolver aprobaciones pendientes con comentario.
- **FR-009**: El sistema MUST exponer un historial legible y filtrable de cambios ya registrados.
- **FR-010**: El monitor MUST informar vigencia, cantidad de registros y estado de fuentes operativas y analíticas.
- **FR-011**: La búsqueda MUST consultar productos, clientes, proveedores y pedidos y agrupar resultados por tipo.
- **FR-012**: Las once fases MUST compartir patrones visuales, estados de carga, vacío y error.
- **FR-013**: La solución MUST reutilizar autenticación, permisos y fuentes existentes sin incorporar un módulo nuevo de seguridad empresarial.
- **FR-014**: Las funciones de lectura MUST degradarse de forma parcial cuando una fuente no esté disponible.
- **FR-015**: Toda interfaz y mensaje nuevo MUST estar en español y usar la marca Altavia Trade.

### Key Entities

- **Meta de gestión**: objetivo medible por tipo y periodo, con valor objetivo, valor real y avance.
- **Solicitud de aprobación**: petición de decisión con tipo, referencia, monto, motivo, estado, solicitante y revisor.
- **Resultado global**: coincidencia agrupada que enlaza una entidad existente con su módulo de origen.
- **Estado de fuente**: resumen de disponibilidad, volumen, última actualización y observaciones.
- **Ficha consolidada**: proyección de información existente alrededor de un producto, cliente o proveedor.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario interno puede llegar a cualquiera de las 11 fases en un máximo de dos interacciones desde el menú.
- **SC-002**: El 95% de las consultas del centro con datos disponibles presenta contenido útil en menos de dos segundos en el entorno local objetivo.
- **SC-003**: Una ficha de producto o cliente reúne al menos cuatro grupos de información sin exigir cambiar de módulo.
- **SC-004**: Toda alerta incluye prioridad y una acción siguiente identificable.
- **SC-005**: Una meta nueva puede registrarse y comprobarse en menos de un minuto.
- **SC-006**: El 100% de las decisiones de aprobación conserva estado, responsable y fecha.
- **SC-007**: Una búsqueda válida devuelve resultados agrupados de hasta cuatro dominios sin duplicados evidentes.
- **SC-008**: Las once fases muestran estados de carga, vacío y error sin dejar áreas en blanco.

## Assumptions

- Se reutilizan los usuarios, roles, permisos, auditoría, notificaciones y colecciones ya existentes.
- La primera versión es una consola integrada para usuarios internos; no reemplaza los módulos operativos especializados.
- Las metas se comparan inicialmente contra ventas e ingresos disponibles en el sistema.
- Las aprobaciones cubren solicitudes administrativas genéricas y no alteran automáticamente operaciones existentes.
- La seguridad empresarial queda fuera del alcance por decisión expresa del usuario; no se eliminan las protecciones ya existentes.
- MongoDB continúa siendo la fuente operativa y ClickHouse la fuente analítica cuando está disponible.
