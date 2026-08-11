# Airflow — GLOBTRADE

Orquesta el ETL estratégico que alimenta **Informes compuestos RC** y el Tablero.

Va **dentro del mismo** `docker-compose.yml` del proyecto (profile `airflow`).
No hay un segundo compose: al mover el repo a otra PC basta copiar este proyecto.

| Recurso | Valor |
|---------|--------|
| Compose | `docker-compose.yml` (raíz) |
| Arranque | `docker compose --profile airflow up -d --build` |
| DAG | `dags/globtrade_strategic_etl.py` |
| UI | http://localhost:8080 |
| Usuario demo | `admin` / `admin` |

Mongo del stack: hostname Docker `mongo` (`MONGO_URI=mongodb://mongo:27017`).

Ver también [`../etl_proceso/README.md`](../etl_proceso/README.md).
