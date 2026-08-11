# Operaciones GLOBTRADE

## Respaldo MongoDB

Antes de cargar datos demo o ejecutar ELT destructivo:

```powershell
.\scripts\backup_mongo.ps1
```

O en CMD: `scripts\backup_mongo.cmd`

Usa `mongodump` local o el contenedor `globtrade-saas-mongo`. Los dumps quedan en `backups/globtrade_dw-YYYYMMDD-HHmmss/`.

## Usuarios demo

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

## Sync analítico automático

Con sesión y permiso `elt.run`, `ops-live.js` consulta cada 2 min si hay `strategic_lagging` y llama a `POST /api/analytics/sync-stale` (máx. una vez cada 5 min). También puedes sincronizar manualmente desde el tablero o Datos Q4.

## ELT con Airflow

DAG `globtrade_strategic_etl` en `airflow/dags/`. UI Airflow en `:8080` cuando el stack Airflow está levantado. Ver `airflow/README.md`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) ejecuta `pytest tests/test_smoke.py` con Mongo 7 en cada push/PR.

## Mongo — segunda base y réplicas

Ver [`README-mongo-ha.md`](README-mongo-ha.md): split `globtrade_ops` / `globtrade_dw`, migración y overlay `docker-compose.mongo-rs.yml`.
