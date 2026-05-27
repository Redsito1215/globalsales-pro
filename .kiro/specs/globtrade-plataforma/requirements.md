# GLOBTRADE — Requisitos (plataforma web · fase Odoo + Steam)

## Objetivo

Evolucionar la plataforma en `C:\vicuna` con una **interfaz inspirada en Odoo Sales**, organizada en **cuatro bloques web (25% cada uno)**, manteniendo **MongoDB** (`globtrade_dw`) como única fuente de datos. El visitante puede **explorar sin cuenta**; acciones de **exportar, generar o modificar** requieren **inicio de sesión** (modelo **Steam**).

Documentación de apoyo (fuera del repo):

- `C:\documentacion\GLOBTRADE_Casos_de_Uso_Completos.docx` (referencia única CU-01…33)
- `C:\documentacion\GLOBTRADE_4_Cuadrantes_Pagina_Web.docx` (apoyo capacidades)
- `C:\documentacion\GLOBTRADE_Casos_Uso_Acceso_Steam.docx` (apoyo Steam resumido)

## Alcance

| Dentro de alcance | Fuera de alcance (esta fase) |
|-------------------|------------------------------|
| Web Flask (`frontend/`), misma BD | Migrar a PostgreSQL u Odoo real |
| Skin / menús estilo Odoo | Segundo proyecto en otra carpeta |
| Login visitante vs autenticado | PocketBase en producción |
| Casos de uso alineados al documento | Reescribir ELT desde cero |

---

## Requisitos funcionales

### 1. Cuadrante Q1 — Tablero principal (25%)

**1.1** La web debe mostrar en la pantalla **Dashboard** KPIs globales: total pedidos, ingresos, utilidad, costos, margen %, cobertura (países y tipos de producto).

**1.2** El dashboard debe permitir filtros por región, tipo de producto, canal de venta, prioridad y período (meses).

**1.3** El dashboard debe mostrar gráficos de resumen: ingresos por región, distribución por canal, prioridades, top países, tendencia mensual y productos.

**1.4** El dashboard debe incluir una tabla paginada de registros de venta sin salir de la pantalla principal.

**1.5** El visitante (sin sesión) debe poder ejecutar **1.1–1.4** en modo solo lectura.

**1.6** Solo usuarios autenticados con rol adecuado pueden usar **Generar más registros** en `sales_records` desde el dashboard.

### 2. Cuadrante Q2 — Análisis y reportes (25%)

**2.1** La web debe ofrecer pantalla **Tendencias** con serie temporal de ingresos y utilidad por mes.

**2.2** La web debe ofrecer pantalla **Regiones y países** con tablas y gráficos de ingresos, utilidad y margen.

**2.3** La web debe ofrecer pantalla **Productos** con ranking por categoría (`item_type`), unidades, ingresos y margen.

**2.4** El visitante debe poder ver **2.1–2.3** sin iniciar sesión.

**2.5** La exportación de informes (PDF, Excel o CSV) desde análisis debe requerir sesión (rol analista o administrador).

### 3. Cuadrante Q3 — Ventas y pedidos (25%)

**3.1** La web debe listar pedidos/ventas (`sales_records`) con paginación server-side y tamaño de página configurable.

**3.2** La web debe filtrar pedidos por país, tipo de producto, canal y prioridad.

**3.3** La web debe mostrar el total de registros que coinciden con los filtros activos.

**3.4** El visitante debe poder ejecutar **3.1–3.3** y ver detalle de un pedido en solo lectura.

**3.5** Crear, editar y eliminar pedidos debe requerir sesión de administrador.

### 4. Cuadrante Q4 — Catálogo y administración de datos (25%)

**4.1** La web debe ofrecer vista **Tablas maestras** con las dimensiones acordadas: `dim_region`, `dim_pais`, `dim_categoria`, `dim_producto`, `dim_canal`, `dim_prioridad`, `dim_cliente`, `dim_tiempo`, `product_categories`, `products`.

**4.2** En tablas maestras el usuario debe poder buscar, paginar y ver conteo por colección.

**4.3** El visitante debe poder explorar maestras en solo lectura.

**4.4** La acción **Construir tablas maestras** (`build_model` / transform ELT) debe requerir sesión de administrador.

**4.5** La web debe mostrar pantalla **Modelo BD** (documentación del esquema para el informe).

**4.6** La acción **Cargar dataset** / disparar ELT completo debe requerir sesión de administrador.

**4.7** La web debe indicar estado de conexión a MongoDB en la interfaz.

### 5. Acceso estilo Steam

**5.1** Cualquier usuario debe acceder al sitio y navegar los cuatro cuadrantes sin crear cuenta.

**5.2** Al intentar exportar, generar ventas, CRUD de pedidos, construir maestras o cargar ELT sin sesión, la web debe mostrar aviso **«Inicia sesión para continuar»** y no ejecutar la acción.

**5.3** La web debe ofrecer pantalla o modal **Iniciar sesión** (usuario/email y contraseña).

**5.4** La web debe ofrecer **Cerrar sesión** y volver a modo visitante.

**5.5** Los roles mínimos serán: **visitante**, **analista** (explorar + exportar), **administrador** (todo lo anterior + modificar datos y ELT).

### 6. Interfaz estilo Odoo (evolución visual)

**6.1** El menú lateral y la barra superior deben seguir convenciones visuales de Odoo Sales (colores, jerarquía, vistas lista).

**6.2** Los cuatro cuadrantes deben mapearse a entradas de menú reconocibles (Inicio, Informes, Ventas, Catálogo/Datos).

**6.3** Los cambios de UI no deben exigir cambio de motor de base de datos.

### 7. Integración con datos existentes

**7.1** Toda la web debe leer y escribir en `MONGO_URI` / `MONGO_DB` configurados en `.env` (por defecto `globtrade_dw`).

**7.2** Los endpoints actuales de Flask (`/api/summary`, `/api/orders`, `/api/master/*`, etc.) deben mantenerse o extenderse, no duplicar lógica en otro repositorio.

**7.3** Docker debe ejecutarse solo desde `C:\vicuna` (no depender de copia `C:\globtrade`).

---

## Requisitos no funcionales

**NFR-1** Puerto web por defecto **5000** (o `WEB_PORT` en `.env`); API FastAPI en **8000**.

**NFR-2** Desarrollo con **Kiro** usando esta spec (`globtrade-plataforma`) y specs existentes `globtrade-mongodb` / `globtrade-web-platform`.

**NFR-3** Documentación de casos de uso en `C:\documentacion` debe poder trazarse a requisitos **1.x–7.x**.

**NFR-4** Idioma de la interfaz: español.

---

## Criterios de aceptación globales

- Un visitante recorre dashboard, análisis, pedidos y maestras sin login.
- Un visitante que pulsa «Exportar» o «Generar ventas» ve solicitud de login.
- Tras login como admin, puede construir maestras y operar CRUD según rol.
- Los cuatro cuadrantes están identificables en menú y documentación.
- `vicuna` sigue siendo el único repositorio de código activo.
