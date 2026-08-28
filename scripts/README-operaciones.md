# Operaciones GLOBTRADE

## Carga inicial recomendada

Un solo comando para dejar el entorno listo para presentación:

```powershell
python scripts/bootstrap_demo.py
```

Opciones:

```powershell
python scripts/bootstrap_demo.py --skip-load        # no cargar CSV histórico
python scripts/bootstrap_demo.py --force-users    # recrear cuentas demo
python scripts/bootstrap_demo.py --skip-scenarios # sin escenarios operativos
```

O en CMD: `scripts\bootstrap_demo.cmd`

El proceso ejecuta de forma idempotente: usuarios de validación, carga ELT si `fact_ventas` está vacío, sincronización del catálogo, proveedores, escenarios operativos e índices.

## Respaldo MongoDB

Antes de cargar datos demo o ejecutar ELT destructivo:

```powershell
.\scripts\backup_mongo.ps1
```

O en CMD: `scripts\backup_mongo.cmd`

Usa `mongodump` local o el contenedor `globtrade-saas-mongo`. Respalda `globtrade_ops` y `globtrade_dw`; los dumps quedan en `backups/globtrade-YYYYMMDD-HHmmss/` con un `manifest.json` verificable.

Verificación de respaldos existentes:

```powershell
python scripts/verify_backups.py

Restauración protegida (crea antes un respaldo preventivo):

`powershell -File .\scripts\restore_mongo.ps1 -BackupId globtrade-AAAAMMDD-HHmmss -Confirm RESTAURAR-globtrade-AAAAMMDD-HHmmss`
```

Para automatizarlo diariamente en Windows, crea una tarea en el Programador de tareas que ejecute:
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\proyect6softwa\scripts\backup_mongo.ps1`.
La cuenta de la tarea debe tener acceso a Docker o a `mongodump` y permiso de escritura únicamente sobre `C:\proyect6softwa\backups`.

## Usuarios de validación

```bash
python scripts/seed_demo.py
python scripts/seed_demo.py --force   # recrea cuentas @globtrade.demo
```

Contraseña por defecto: `Demo1234!`

| Correo | Rol |
|--------|-----|
| admin@globtrade.demo | administrador |
| vendedor@globtrade.demo | vendedor |
| analista@globtrade.demo | analista |
| cliente@globtrade.demo | cliente |

## Flujos operativos

### Ventas y caja

1. Cliente hace checkout → solicitud en **Mis pedidos**.
2. Vendedor aprueba → cliente paga con tarjeta; `4000…0002` produce rechazo y `…9999` fondos insuficientes.
3. Convertir a venta (exige pago completo salvo canal Offline) → sync incremental a `fact_ventas`.
4. Movimientos de caja: `payment_in` al pagar, `refund_out` en devoluciones. Ver Compras → **Libro de caja** o reporte **RS-13**.

### Compras

- **Requisiciones**: borrador → aprobar → convertir a OC (borrador).
- **OC a proveedor**: borrador → Enviar → Recibir (parcial permitido).
- **Merma**: unidades dañadas en devoluciones (pestaña Merma en Compras).
- Reportes: **RS-14** (ventas vs devoluciones), **RS-15** (stock valorizado).

### Sync analítico automático

Con sesión y permiso `elt.run`, `ops-live.js` consulta cada 2 min si hay `strategic_lagging` y llama a `POST /api/analytics/sync-stale` (máx. una vez cada 5 min). También puedes sincronizar manualmente desde el tablero o Datos Q4.

## ELT con Airflow

DAG `globtrade_strategic_etl` en `airflow/dags/`. UI Airflow en `:8080` cuando el stack Airflow está levantado. Ver `airflow/README.md`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) ejecuta `pytest tests/test_smoke.py` con Mongo 7 en cada push/PR.

## Mongo — segunda base y réplicas

Ver [`README-mongo-ha.md`](README-mongo-ha.md): split `globtrade_ops` / `globtrade_dw`, migración y overlay `docker-compose.mongo-rs.yml`.
