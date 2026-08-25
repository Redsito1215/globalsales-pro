# Plan de pruebas — GLOBTRADE

**Aplicación:** plataforma comercial GLOBTRADE (Flask + MongoDB + SPA)  
**Ambiente:** local — http://127.0.0.1:5001  
**Versión de referencia:** 2026-08-24  
**Tipo:** pruebas funcionales (manuales + automatizadas)  
**Objetivo:** verificar que cada rol puede completar su trabajo y que las reglas de negocio se cumplen.

---

## 1. Alcance

### Incluido
- Autenticación y menús por rol
- Tienda, carrito y checkout
- Rebaja 25 % por producto
- Pedidos: aprobar → pagar → convertir → enviar → entregar → devolver
- Compras (requisición, OC, inventario, caja)
- Tablero, informes, reportes PDF
- Gestión de maestros, roles, empresa
- Notificaciones y soporte
- Restricciones de acceso (401 / 403)

### Fuera de alcance
- Pasarela de pago bancaria real
- Servicios externos de correo
- Pruebas de carga masiva / seguridad ofensiva
- Entorno de producción en internet

---

## 2. Precondiciones

1. Docker Desktop en marcha.
2. MongoDB: `docker compose up -d mongo` (puerto 27017).
3. Datos y usuarios de validación:

```powershell
cd C:\proyect6softwa
python scripts\bootstrap_demo.py
.\scripts\iniciar-web.ps1
```

4. Abrir http://127.0.0.1:5001 y recargar con **Ctrl+F5**.

### Cuentas de prueba

| Rol | Correo | Contraseña |
|-----|--------|------------|
| Administrador | `admin@globtrade.demo` | `Demo1234!` |
| Vendedor | `vendedor@globtrade.demo` | `Demo1234!` |
| Analista | `analista@globtrade.demo` | `Demo1234!` |
| Cliente | `cliente@globtrade.demo` | `Demo1234!` |

---

## 3. Criterios de éxito

| Nivel | Criterio |
|-------|----------|
| Automatizado | `python -m pytest tests/test_smoke.py -q` → todos los tests en verde |
| Manual | Todos los casos **P0** y **P1** en estado Pass |
| Acceso | El cliente no ve tablero, reportes, compras ni auditoría |
| Flujo de venta | No se puede pagar sin aprobar; no se puede enviar/entregar sin pagar |
| Tienda | Solo productos con interruptor ON muestran «¡Rebajado!» y precio tachado |

Un caso **falla** si hay error de pantalla, mensaje incorrecto, dato que no persiste o acción permitida sin permiso.

---

## 4. Pruebas automatizadas

**Comando:**

```powershell
cd C:\proyect6softwa
python -m pytest tests/test_smoke.py -q
```

**Qué cubre (resumen):**
- Cálculo de rebaja 25 %
- Prorrateo de descuentos
- Estados de solicitud y pago
- Devoluciones (apto / dañado / mixto)
- Auth en checkout, pago, auditoría, reportes
- Recorrido API por rol (`test_demo_role_walkthrough`)
- Catálogo de reportes y capas de datos

**Resultado esperado:** 125 o más tests `passed`.

---

## 5. Casos de prueba manuales

Leyenda: **P0** bloqueante · **P1** importante · **P2** menor  
Resultado: Pass / Fail / N/A

### 5.1 Visitante (sin sesión)

| ID | Pri | Pasos | Resultado esperado |
|----|-----|-------|--------------------|
| VIS-01 | P0 | Abrir la URL | Se ve la tienda (hero + catálogo) |
| VIS-02 | P0 | Agregar al carrito y pedir checkout | Pide iniciar sesión |
| VIS-03 | P1 | Intentar entrar a Tablero o Gestión por URL/menú | No aparecen o se bloquean |

### 5.2 Cliente

| ID | Pri | Pasos | Resultado esperado |
|----|-----|-------|--------------------|
| CLI-01 | P0 | Login con `cliente@globtrade.demo` | Entra; nav: Tienda, Mis pedidos, Notificaciones, Soporte |
| CLI-02 | P0 | No ve Tablero, Informes, Compras, Gestión | Menús de staff ocultos |
| CLI-03 | P0 | Agregar 2 productos, checkout con destino | Solicitud creada; aparece en Mis pedidos |
| CLI-04 | P0 | Intentar pagar una solicitud **pendiente** (no aprobada) | No permite pagar; mensaje de que debe estar aprobada |
| CLI-05 | P0 | Con solicitud **aprobada**, pagar con tarjeta (13–19 dígitos, vencimiento MM/AA) | Estado de pago pasa a pagada |
| CLI-06 | P1 | Nombre en modal de pago | Viene prellenado con el nombre del cliente |
| CLI-07 | P1 | Abrir Notificaciones y filtrar por categoría | Lista y filtro funcionan |
| CLI-08 | P1 | Enviar mensaje de soporte | Hilo visible; respuesta del staff llega después |

### 5.3 Vendedor

| ID | Pri | Pasos | Resultado esperado |
|----|-----|-------|--------------------|
| VEN-01 | P0 | Login vendedor | Ve Ventas, Compras, Reportes, Decisiones; **no** ve Auditoría ni Gestión de roles |
| VEN-02 | P0 | Pedidos: aprobar solicitud del cliente | Estado **aprobada**; el cliente ya puede pagar |
| VEN-03 | P0 | Convertir **sin** pago | Error: el cliente debe pagar primero |
| VEN-04 | P0 | Tras pago: convertir → enviar → entregar | Transiciones válidas; Offline no exige envío |
| VEN-05 | P1 | Intentar enviar/entregar sin pago | Bloqueado |
| VEN-06 | P1 | Devolver pedido entregado (apto / dañado / mixto) | Stock y caja se actualizan según condición |
| VEN-07 | P1 | Compras: crear requisición y OC | Flujo guarda y lista registros |
| VEN-08 | P2 | Abrir un reporte y exportar PDF | Descarga o vista PDF sin error |

### 5.4 Analista

| ID | Pri | Pasos | Resultado esperado |
|----|-----|-------|--------------------|
| ANA-01 | P0 | Login analista | Ve Tablero, tendencias, regiones, productos, reportes |
| ANA-02 | P0 | Intentar Compras / inventario | 403 o menú oculto |
| ANA-03 | P1 | Filtro «Todo el histórico» en tablero | KPIs y gráficos con datos |
| ANA-04 | P1 | Exportar análisis | Exporta estando autenticado |
| ANA-05 | P2 | Catálogo analítico por categoría | Lista productos de la categoría |

### 5.5 Administrador

| ID | Pri | Pasos | Resultado esperado |
|----|-----|-------|--------------------|
| ADM-01 | P0 | Login admin | Acceso a todas las páginas |
| ADM-02 | P0 | Gestión → Productos: interruptor de rebaja **ON** en un SKU | En tienda: badge «¡Rebajado!», precio tachado = base, precio = 75 % |
| ADM-03 | P0 | Mismo SKU **OFF** | Precio único, sin badge |
| ADM-04 | P0 | Recargar tienda (otra pestaña) tras el interruptor | El cambio se ve sin depender de caché de página |
| ADM-05 | P1 | Empresa: cambiar tagline / banner | Se refleja en tienda y documentos |
| ADM-06 | P1 | Roles: ver usuarios y no romper roles de sistema | Lista correcta; no se desactiva el único admin |
| ADM-07 | P1 | Auditoría | Eventos de pago / edición aparecen |
| ADM-08 | P2 | Sincronizar catálogo (sin reset de stock) | Mensaje de éxito; stock no se borra |

### 5.6 Tienda y rebaja

| ID | Pri | Pasos | Resultado esperado |
|----|-----|-------|--------------------|
| SHP-01 | P0 | Catálogo con 100 productos | Imágenes, precio, Ver detalles, Agregar |
| SHP-02 | P0 | Buscar por nombre | Filtra resultados |
| SHP-03 | P1 | Colección completa al carrito | Varias líneas; cantidades ≥ 1 |
| SHP-04 | P1 | Producto en rebaja al carrito y checkout | Total usa precio rebajado, no el tachado |
| SHP-05 | P2 | Ficha de producto | Nombre, SKU, stock, precio coherente con la tarjeta |

### 5.7 Pagos y validación de tarjeta

| ID | Pri | Pasos | Resultado esperado |
|----|-----|-------|--------------------|
| PAY-01 | P0 | Número < 13 dígitos | Rechazo de formato |
| PAY-02 | P0 | Vencimiento inválido (mes 13 o fecha pasada) | Error de vencimiento |
| PAY-03 | P1 | Solicitud ya pagada | No permite pagar de nuevo |
| PAY-04 | P2 | Cerrar modal y reabrir | Campos coherentes; no se duplica el cobro |

### 5.8 Datos y ELT (admin)

| ID | Pri | Pasos | Resultado esperado |
|----|-----|-------|--------------------|
| DAT-01 | P1 | Abrir Gestión → Productos | Tabla paginada, buscar, editar |
| DAT-02 | P2 | Carga ELT / sync fact | Completa o muestra error claro |
| DAT-03 | P2 | Schema / capas | Distingue operativo vs estratégico |

---

## 6. Recorrido de demostración (15–20 min)

Orden recomendado para una sesión viva:

1. **Visitante:** tienda pública.  
2. **Cliente:** pedido → espera aprobación → (tras paso 3) paga.  
3. **Vendedor:** aprueba → no convierte aún → tras pago convierte y envía.  
4. **Admin:** activa rebaja en un producto → cliente ve precio nuevo.  
5. **Analista:** tablero e informe.  
6. **Cerrar sesión:** vuelve a tienda (hero en inicio).

---

## 7. Registro de ejecución

Fecha: ________  Tester: ________  Build / commit: ________

| ID | Resultado | Evidencia / nota | Defecto # |
|----|-----------|------------------|-----------|
| VIS-01 | | | |
| CLI-01 | | | |
| CLI-03 | | | |
| CLI-04 | | | |
| CLI-05 | | | |
| VEN-02 | | | |
| VEN-03 | | | |
| VEN-04 | | | |
| ADM-02 | | | |
| ADM-03 | | | |
| SHP-04 | | | |
| *…copiar IDs P0/P1 restantes…* | | | |

**Smoke automático:** Pass / Fail   Tests: ____ / ____

---

## 8. Plantilla de defecto

| Campo | Valor |
|-------|--------|
| ID | DEF-___ |
| Caso | p. ej. ADM-02 |
| Rol | |
| Pasos | |
| Esperado | |
| Obtenido | |
| Severidad | Bloqueante / Alta / Media / Baja |
| Captura | Sí / No |

---

## 9. Riesgos conocidos (no son fallos si coinciden)

- El cobro con tarjeta es interno al sistema (no hay banco real).
- El sistema no ofrece recuperación de contraseña ni utiliza servicios externos de correo.
- Usuarios y datos de ejemplo viven en Mongo local; si la base está vacía, ejecutar `bootstrap_demo.py`.
- Tras cambiar JS/CSS, hace falta **Ctrl+F5**.

---

## 10. Cierre

El plan se da por **cumplido** cuando:

1. Smoke automático en verde.  
2. Todos los P0 en Pass.  
3. P1 fallidos documentados (ninguno bloqueante sin justificación).  
4. Recorrido de demostración ejecutado una vez de punta a punta.
