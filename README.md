# Altavia Trade

Plataforma web comercial-analítica (Flask + MongoDB + ClickHouse): tablero, análisis, decisiones, ventas B2B, compras/stock y maestros.

## Requisitos

- Python 3.12+
- MongoDB en `localhost:27017` (o URI en `.env`)
- (Opcional) Docker Desktop

## Arranque rápido (Windows)

```powershell
cd C:\proyect6softwa
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # ajusta FLASK_SECRET_KEY y MONGO_URI si hace falta
```

### MongoDB

Asegura que Mongo esté en marcha (`27017`). Con Docker:

```powershell
docker compose up -d mongo
```

### Web (puerto 5001)

```powershell
.\scripts\iniciar-web.ps1
# o:
$env:PYTHONPATH="C:\proyect6softwa\backend;C:\proyect6softwa"
.\.venv\Scripts\python.exe -m flask --app frontend.app run --host 0.0.0.0 --port 5001
```

Abre http://127.0.0.1:5001  

El **primer usuario** registrado queda como **administrador**.

## Docker completo

```powershell
.\scripts\docker-up.cmd
```

Servicios: web `:5001`, API auxiliar `:8001`, Mongo `:27017` y ClickHouse HTTP `:8123`.

Para comprobar ClickHouse sin usar comandos, abre **Táctico → Gestión profesional → Experiencia** y pulsa **Verificar ahora**. Ahí se muestran conexión, última carga y filas por tabla. Para revisar ejecuciones del proceso abre Airflow en `http://localhost:8080` (`admin` / `admin`). ClickHouse no incluye una interfaz gráfica en este proyecto; su endpoint HTTP es `http://localhost:8123` y la base usada es `globtrade_analytics`.

Por defecto Docker usa **dos bases** en el mismo Mongo:

| Base | Contenido |
|------|-----------|
| `globtrade_ops` | Tienda, pedidos, compras, usuarios, roles, auditoría |
| `globtrade_dw` | `sales_records`, `fact_ventas`, dimensiones `dim_*` |

Al arrancar la web, si `globtrade_ops` está vacío y los datos operativos siguen en `globtrade_dw`, se **copian automáticamente** (ver log `[mongo] split ops/DW`). Opcional después:

```powershell
python scripts/migrate_split_mongo.py --drop-source
```

Detalle: [`scripts/README-mongo-ha.md`](scripts/README-mongo-ha.md).

## Informes con asistente IA

En **Informes simples** e **Informes compuestos** → botón **Asistente IA**:

- **OpenAI Responses API**: define `OPENAI_API_KEY` en `.env` para activar el asistente de informes. El navegador nunca recibe la clave y el sistema muestra un error claro si falta configuración, autenticación o cuota. Sin una API configurada, el asistente permanece deshabilitado y no simula respuestas locales.

Los informes **RS** (simples) y **RC** (compuestos) se eligen por separado en el asistente.

## Flujo comercial

**Carga inicial recomendada** (usuarios, datos históricos si están vacíos, catálogo y escenarios de validación):

```powershell
python scripts/bootstrap_demo.py
# Cuenta inicial: admin@globtrade.demo / Demo1234!
```

1. Admin: Maestros → Sync catálogo (tienda) / Carga ELT, Construir modelo, o DAG Airflow `globtrade_strategic_etl` si el Tablero (`fact_ventas`) está vacío  
2. Cliente: Vitrina → checkout (sesión) → Mis pedidos (autorización interna de tarjeta + seguimiento)  
3. Vendedor/Admin: Solicitudes → aprobar → cliente paga (o crédito) → convertir → enviar → entregar  
4. Devolución: solo pedidos **entregados**; inspección (**apto / dañado / mixto**). Solo lo apto reingresa; dañado = merma.  
5. Compras/Stock: inventario, **requisiciones internas** (borrador → aprobada → OC), proveedores, OC **borrador → Enviar → Recibir** (parcial OK), **libro de caja** y merma  
6. Decisiones → stock bajo → **Crear OC** (prellena Compras). Sync catálogo **no** borra proveedores.  

### Contabilidad

- Al pagar una solicitud se registra un movimiento `payment_in` en `cash_movements`; devoluciones generan `refund_out`.  
- Convertir a venta exige pago completo (salvo canal Offline).  
- Consulta el libro en Compras → **Libro de caja** o reporte **RS-13**.

### Capas de datos

- **Operativo**: vitrina, solicitudes, compras, soporte, **Reportes simples (RS-01…15)**  
- **Landing**: `sales_records` (CSV, generate, post-convertir; Explorar ventas / export)  
- **Estratégico**: Tablero sobre `fact_ventas` + dimensiones en Mongo; **Informes compuestos (RC-01…08)** publicados y consultados en ClickHouse mediante Airflow (`globtrade_strategic_etl`).

El pago usa autorización interna y no existe integración con banco, pasarela externa ni servicios de correo.

### Niveles del sistema

- **Operativo**: tienda, pedidos, ventas, compras, inventario, notificaciones y soporte.
- **Táctico**: informes operativos, exploración detallada, catálogo analítico, exportaciones y maestros.
- **Estratégico**: tablero ejecutivo, decisiones, informes compuestos y tendencias agregadas.
- **Administración**: configuración, carga de datos, modelo, auditoría, usuarios y roles.

El **Centro de decisiones** clasifica el portafolio por producto (estrella, oportunidad,
volumen con margen débil o revisar), calcula cobertura, inventario estancado y una reposición
sugerida con 14 días de entrega más 7 días de seguridad. Cada señal incluye la cifra que la
origina y una decisión recomendada; la fuente analítica es ClickHouse.

## ETL orquestado por Airflow (capa estratégica)

Alimenta `fact_ventas` + dimensiones para el Tablero y publica ventas, compras, inventario, logística y cupones en ClickHouse para los **Informes compuestos RC**. La publicación es idempotente mediante **truncate + reload**.

Todo va en el **mismo** `docker-compose.yml` (profile `airflow`):

```powershell
# App + Mongo + Airflow (un solo comando / un solo archivo)
docker compose --profile airflow up -d --build

# Solo app (sin Airflow), si no lo necesitas ahora:
# docker compose up -d --build
```

1. Abre http://localhost:8080 (`admin` / `admin`)
2. El DAG `globtrade_strategic_etl` se ejecuta diariamente a las 02:00 y también permite ejecución manual. La carga idempotente reemplaza de forma controlada la publicación estratégica.
3. Ver Informes compuestos RC en http://127.0.0.1:5001

Detalle del pipeline: [`etl_proceso/README.md`](etl_proceso/README.md).

## Tests smoke

```powershell
pip install -r requirements.txt
$env:PYTHONPATH="C:\proyect6softwa\backend;C:\proyect6softwa"
.\.venv\Scripts\pytest.exe -q
```

Con Docker y verificación final:

```powershell
docker compose exec web python scripts/verify_release.py
docker compose run --rm -T -v C:/proyect6softwa/tests:/app/tests:ro web python -m pytest -q
```

Manual de operación y entrega: [`docs/manual-operacion.md`](docs/manual-operacion.md).

## Estructura

- `frontend/` — app Flask + SPA estática  
- `backend/` — auth, config, shared, ETL  
- `etl_proceso/` — wrappers del ETL estratégico (Airflow + CLI)  
- `airflow/dags/` — DAG `globtrade_strategic_etl`  
- `paquetes/` — tablero, analisis, decisiones, ventas, shop, compras, datos, soporte, reportes, empresa  
- `specs/` — Spec Kit académico  

## Puertos

| Servicio | Puerto |
|----------|--------|
| Web Flask | 5001 |
| API FastAPI (health) | 8001 |
| MongoDB | 27017 |
| Airflow UI | 8080 |
