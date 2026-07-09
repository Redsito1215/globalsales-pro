# GLOBTRADE S.A. — Requisitos (plataforma web)

## Objetivo

Construir la plataforma en **`C:\proyect6softwa`** con interfaz inspirada en **Odoo Sales**, en **cuatro bloques web (25 % c/u)**, sobre **MongoDB** `globtrade_dw`. El visitante explora sin cuenta; exportar, generar o modificar datos requiere **inicio de sesión** (sin usar la palabra «Steam» en código ni UI).

Documentación: `C:\documentacion\` · CU: `GLOBTRADE_Casos_de_Uso_Completos.docx`

## Alcance

| Dentro | Fuera |
|--------|--------|
| Web Flask + paquetes | Migrar a PostgreSQL / Odoo real |
| Docker `globtrade-saas-web` / `api` | Segundo repo de código (vicuna obsoleto) |
| Login visitante / analista / admin | PocketBase en producción |

---

## Requisitos funcionales

### 1. Cuadrante Q1 — Tablero (25 %)

**1.1** KPIs: pedidos, ingresos, utilidad, costos, margen %, países, tipos de producto.  
**1.2** Filtros: región, producto, canal, prioridad, período (meses; default histórico si datos antiguos).  
**1.3** Gráficos: región, canal, prioridades, países, tendencia, productos.  
**1.4** Tabla paginada de ventas en la misma pantalla.  
**1.5** Visitante: solo lectura en 1.1–1.4.  
**1.6** Generar registros en `sales_records`: solo admin autenticado (fase acceso).

### 2. Cuadrante Q2 — Análisis (25 %)

**2.1** Tendencias · **2.2** Regiones y países · **2.3** Productos · **2.4** Visitante lee · **2.5** Exportar con sesión.

### 3. Cuadrante Q3 — Ventas (25 %)

**3.1–3.3** Listar, filtrar, contar pedidos · **3.4** Detalle lectura · **3.5** CRUD admin.

### 4. Cuadrante Q4 — Datos (25 %)

**4.1–4.3** Maestras lectura · **4.4–4.6** build_model, modelo BD, ELT admin · **4.7** Estado Mongo en UI.

### 5. Acceso y sesión

**5.1** Navegar Q1–Q4 sin cuenta · **5.2** Bloqueo con «Inicia sesión» · **5.3–5.4** Login / logout · **5.5** Roles visitante, analista, administrador.

### 6. UI estilo Odoo

**6.1–6.3** Menú cuatro cuadrantes, barra morada `#714B67`, misma BD.

### 7. Datos e infraestructura

**7.1** `MONGO_URI` / `globtrade_dw` · **7.2** API en `paquetes/*` · **7.3** Docker: app en `C:\proyect6softwa`; Mongo contenedor `globtrade-mongo` :27017.

---

## NFR

**NFR-1** Web **5001**, API **8001** (host).  
**NFR-2** Spec Kiro en `.kiro/specs/globtrade-plataforma/`.  
**NFR-3** Trazabilidad a CU en `C:\documentacion`.  
**NFR-4** UI en español.

---

## Criterios de aceptación (100 %)

- Cuatro cuadrantes en menú · visitante explora · acciones sensibles con login · 300k registros en `sales_records` (GA) · despliegue Docker documentado.
