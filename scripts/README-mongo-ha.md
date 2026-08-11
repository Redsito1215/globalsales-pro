# MongoDB — segunda base y réplicas

GLOBTRADE puede usar **una sola base** (default) o **dos bases** + **réplica set** opcional.

## Modo default (sin cambios)

- URI: `mongodb://localhost:27017`
- Base: `globtrade_dw` (operativo + DW juntos)
- Docker: `docker compose up -d`

## Segunda base Mongo (ops vs DW)

Separa transaccional/gobernanza del data warehouse:

| Base | Colecciones |
|------|-------------|
| **`globtrade_ops`** | pedidos, tienda, compras, usuarios, roles, auditoría, notificaciones, soporte |
| **`globtrade_dw`** | `sales_records`, `fact_ventas`, dimensiones `dim_*`, KPIs |

### Activar

1. En `.env` o variables Docker:

```env
MONGO_DB=globtrade_dw
MONGO_OPS_DB=globtrade_ops
```

2. Respaldo antes de migrar:

```powershell
.\scripts\backup_mongo.ps1
```

3. Migrar datos existentes:

```bash
python scripts/migrate_split_mongo.py
python scripts/migrate_split_mongo.py --drop-source   # opcional: quita ops de globtrade_dw
```

4. Reinicia la web (`docker compose restart web`).

La app enruta automáticamente: `get_db()[colección]` va a ops o DW según la capa. El panel **Datos → capas** muestra `topology.split_enabled: true`.

## Réplicas (replica set)

Sirve para **alta disponibilidad** y probar **lecturas en secundario** (tablero/reportes usan `SECONDARY_PREFERRED` si hay `MONGO_REPLICA_URI`).

### Local con Docker (1 nodo rs0)

```bash
docker compose -f docker-compose.yml -f docker-compose.mongo-rs.yml up -d --build
```

Variables que añade el overlay:

- `MONGO_URI=mongodb://mongo:27017/?replicaSet=rs0`
- `MONGO_REPLICA_URI=...` (lecturas analíticas)
- `MONGO_REPLICA_SET=rs0`

El contenedor `mongo-rs-init` ejecuta `rs.initiate()` una vez.

### Producción (3 nodos)

En Atlas o VMs, usa una URI multi-host:

```env
MONGO_URI=mongodb://host1:27017,host2:27017,host3:27017/?replicaSet=rs0
MONGO_REPLICA_URI=mongodb://host1:27017,host2:27017,host3:27017/?replicaSet=rs0
MONGO_REPLICA_SET=rs0
```

Escrituras → primario. Tablero Q1 → preferencia secundario (misma réplica en local de 1 nodo).

## Combinar split + réplicas

```env
MONGO_URI=mongodb://mongo:27017/?replicaSet=rs0
MONGO_REPLICA_URI=mongodb://mongo:27017/?replicaSet=rs0
MONGO_REPLICA_SET=rs0
MONGO_DB=globtrade_dw
MONGO_OPS_DB=globtrade_ops
```

Orden: levantar stack con overlay RS → migrar split → reiniciar app.

## Verificación

- Logs al arrancar `frontend/app.py`: muestra bases ops/DW o “base única”.
- `GET /api/meta/data-layers` → campo `topology`.
- Smoke: `pytest tests/test_smoke.py::test_mongo_collection_routing -q`
