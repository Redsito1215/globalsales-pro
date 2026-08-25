# Feature Specification: Plataforma Web GLOBTRADE

**Feature Branch**: `001-globtrade-plataforma`

**Created**: 2026-06-21

**Status**: Implemented (2026-08)

**Input**: User description: "Formalizar en Spec Kit el proyecto GLOBTRADE existente en C:\proyect6softwa, tomando como base la especificacion Kiro de la plataforma web."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explorar tablero Q1 (Priority: P1)

Como visitante, quiero abrir el tablero inicial de GLOBTRADE y revisar KPIs,
graficos y ventas filtradas sin iniciar sesion, para entender el comportamiento
historico de ventas.

**Why this priority**: Q1 Tablero ya representa el primer 25 % funcional y es la
base demostrable del proyecto.

**Independent Test**: Abrir la aplicacion en el navegador, elegir "Todo el
historico" y verificar KPIs, graficos y tabla con datos reales.

**Acceptance Scenarios**:

1. **Given** que MongoDB contiene datos historicos de ventas, **When** el visitante abre el tablero, **Then** ve pedidos, ingresos, utilidad, costos, margen, paises y productos.
2. **Given** que el visitante cambia region, producto, canal, prioridad o periodo, **When** aplica el filtro, **Then** los KPIs, graficos y tabla reflejan el nuevo criterio.
3. **Given** que los datos son de 2010 a 2017, **When** se selecciona "Todo el historico", **Then** el tablero no muestra ceros por usar una ventana relativa a la fecha actual.

---

### User Story 2 - Explorar y administrar ventas Q3 (Priority: P2)

Como usuario del area comercial, quiero listar, filtrar y consultar detalles de
pedidos, y como administrador quiero crear, editar o eliminar pedidos, para
gestionar ventas desde la misma plataforma.

**Why this priority**: Q3 completa el uso operativo de ventas y reutiliza la
base de datos y patrones del tablero.

**Independent Test**: Abrir el menu Ventas, filtrar pedidos, consultar un detalle
y verificar que las acciones de modificacion pidan sesion o rol administrador.

**Acceptance Scenarios**:

1. **Given** que existen pedidos en la base, **When** el usuario abre Ventas, **Then** ve un listado paginado con filtros por pais, producto, canal y prioridad.
2. **Given** que un visitante intenta crear, editar o eliminar un pedido, **When** ejecuta la accion, **Then** el sistema solicita iniciar sesion.
3. **Given** que un administrador autenticado modifica un pedido, **When** guarda los cambios, **Then** el listado refleja la operacion y conserva la integridad de los datos.

---

### User Story 3 - Analizar tendencias Q2 (Priority: P3)

Como analista, quiero revisar tendencias, regiones, paises y productos en vistas
dedicadas, para interpretar mejor el rendimiento comercial.

**Why this priority**: Q2 amplifica el valor analitico de consultas ya existentes
sin bloquear el flujo de ventas.

**Independent Test**: Abrir Informes, navegar por Tendencias, Regiones y
Productos, y verificar que cada pantalla se alimente del periodo historico.

**Acceptance Scenarios**:

1. **Given** que el usuario abre Informes, **When** selecciona Tendencias, **Then** ve la evolucion de ventas del periodo seleccionado.
2. **Given** que el usuario selecciona Regiones o Productos, **When** cambia filtros, **Then** los graficos y metricas se actualizan coherentemente.
3. **Given** que un visitante intenta exportar informacion, **When** pulsa Exportar, **Then** el sistema le indica que debe iniciar sesion.

---

### User Story 4 - Consultar y operar datos Q4 (Priority: P4)

Como administrador de datos, quiero consultar tablas maestras, revisar el modelo
de datos y ejecutar cargas controladas, para mantener disponible el dataset de
GLOBTRADE.

**Why this priority**: Q4 completa la administracion de datos y expone el estado
operativo sin mezclarlo con el tablero.

**Independent Test**: Abrir Datos, consultar una tabla maestra, revisar estado
Mongo y confirmar que build_model o cargas requieren permisos.

**Acceptance Scenarios**:

1. **Given** que existen colecciones maestras, **When** el usuario abre Datos, **Then** puede listar tablas y explorar registros paginados.
2. **Given** que un administrador ejecuta build_model, **When** termina el proceso, **Then** el sistema muestra estado o resultado de la operacion.
3. **Given** que un visitante intenta ejecutar ELT o cargar datos, **When** pulsa la accion, **Then** se bloquea y se solicita sesion.

---

### User Story 5 - Acceso y roles (Priority: P5)

Como administrador, quiero controlar sesiones y roles de visitante, analista y
administrador, para permitir lectura publica y proteger acciones sensibles.

**Why this priority**: El control de acceso es transversal y debe cerrar las
acciones sensibles de Q2, Q3 y Q4.

**Independent Test**: Iniciar sesion, consultar el estado del usuario, cerrar
sesion y verificar permisos en generar ventas, exportar, CRUD y ELT.

**Acceptance Scenarios**:

1. **Given** que un usuario valido inicia sesion, **When** envia sus credenciales, **Then** el sistema crea sesion y devuelve su rol.
2. **Given** que un visitante accede a vistas de lectura, **When** navega por Q1-Q4, **Then** puede ver informacion sin autenticarse.
3. **Given** que una accion requiere rol administrador o analista, **When** un usuario sin permiso la intenta ejecutar, **Then** el sistema la rechaza con un mensaje claro.

### Edge Cases

- MongoDB esta apagado o sin datos: la UI debe mostrar un error comprensible y no romper la pagina.
- El periodo por defecto no encuentra datos historicos: el usuario debe poder seleccionar "Todo el historico".
- Filtros combinados devuelven cero filas: KPIs y graficos deben mostrar estado vacio coherente.
- Un pedido inexistente se consulta, edita o elimina: la respuesta debe indicar que no fue encontrado.
- Una sesion expirada intenta una accion sensible: el sistema debe pedir iniciar sesion otra vez.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST present four main quadrants: Inicio/Tablero, Informes, Ventas, and Datos.
- **FR-002**: Visitors MUST be able to navigate and read Q1-Q4 views without an account.
- **FR-003**: System MUST show Q1 KPIs for pedidos, ingresos, utilidad, costos, margen, paises, and product types.
- **FR-004**: System MUST support Q1 filters by region, product, channel, priority, and period, including "Todo el historico".
- **FR-005**: System MUST render Q1 charts for region, channel, priority, country, trend, and products.
- **FR-006**: System MUST show a paginated sales table in the dashboard.
- **FR-007**: System MUST provide Q3 order listing, count, detail, creation, update, and deletion capabilities.
- **FR-008**: System MUST protect order creation, update, and deletion so only an administrator can execute them.
- **FR-009**: System MUST provide Q2 trend, region/country, and product analysis views.
- **FR-010**: System MUST protect exports so only authenticated users with allowed roles can execute them.
- **FR-011**: System MUST provide Q4 master table browsing, schema/model visibility, Mongo status, and controlled ELT/model actions.
- **FR-012**: System MUST protect data generation, model build, data loading, and ELT actions behind authenticated roles.
- **FR-013**: System MUST support login, logout, current-user state, and roles for visitante, analista, and administrador.
- **FR-014**: System MUST use Spanish UI labels and messages.
- **FR-015**: System MUST preserve Odoo-inspired navigation and styling, including the purple `#714B67` top bar.
- **FR-016**: System MUST keep all application code in `C:\proyect6softwa` and use the documented MongoDB database.

### Key Entities *(include if feature involves data)*

- **SalesRecord**: A sales order record with order metadata, geography, product, channel, priority, dates, units, revenue, cost, and profit metrics.
- **User**: A platform account with credentials, display data, active status, and role.
- **Role**: Permission grouping for visitor, analyst, and administrator behavior.
- **MasterTable**: Read-only representation of dimensional collections used by dashboards and data exploration.
- **FilterSelection**: User-selected region, product, channel, priority, and period criteria applied to dashboard and analysis views.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor can open the application and view populated Q1 dashboard data in under 2 minutes from startup.
- **SC-002**: At least 95 % of dashboard filter changes update visible KPIs, charts, and table results without a page crash.
- **SC-003**: Visitors can access all four quadrant menus while 100 % of sensitive write/export/load actions require authentication.
- **SC-004**: The platform can demonstrate Q1-Q4 navigation, one sales listing flow, one analysis flow, one data browsing flow, and one login/logout flow during a single demo.
- **SC-005**: The documented local or Docker startup path allows the app to run on port 5001 with MongoDB available on port 27017.

## Assumptions

- The existing Kiro specification remains the source of truth for academic scope and case-use traceability.
- Q1 Tablero is already implemented and should be preserved while extending the remaining quadrants.
- MongoDB `globtrade_dw` and the `globtrade-mongo` container are available locally for validation.
- The project remains a single Flask application with package-based blueprints and a static SPA frontend.
- Automated tests may be added where practical, but browser/API manual validation is acceptable for academic demo checkpoints.

## Deliberate exclusions

### Correo electrónico (simulado)

El envío de correo **no se integra con SMTP real** de forma intencional. Una integración
productiva exigiría cuentas de correo reales, credenciales gestionadas de forma segura
y, en muchos casos, dominio verificado (SPF/DKIM) para evitar que los mensajes se marquen
como spam. Eso añade fricción operativa y dependencias externas que no están disponibles
en el entorno de desarrollo del proyecto.

En su lugar, GLOBTRADE **modela** las notificaciones y confirmaciones (registro en base de
datos, mensajes en UI, flujos de soporte/pedidos) **sin disparar emails reales**. Esto
cubre el comportamiento demostrable de la aplicación sin salir a internet ni usar buzones
de terceros.

Para la defensa o revisión académica: la ausencia de correo real es una **decisión de
alcance**, no un fallo pendiente de implementación.
