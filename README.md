# GLOBTRADE

Plataforma web comercial-analítica (Flask + MongoDB): tablero, análisis, decisiones, ventas B2B, compras/stock y maestros.

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

Servicios: web `:5001`, API auxiliar `:8001`, Mongo `:27017`.

## Flujo comercial (demo)

1. Admin: Maestros → Sync catálogo (tienda) / Carga ELT o Construir modelo si el Tablero (fact_ventas) está vacío  
2. Cliente: Vitrina → checkout (sesión) → Mis pedidos (pago simulado + tracking)  
3. Vendedor/Admin: Solicitudes → aprobar → cliente paga (o crédito) → convertir → enviar → entregar  
4. Devolución: solo pedidos **entregados**; inspección (**apto / dañado / mixto**). Solo lo apto reingresa; dañado = merma.  
5. Compras/Stock (admin o vendedor): inventario, proveedores, OC **borrador → Enviar → Recibir** (parcial OK)  
6. Decisiones → stock bajo → **Crear OC** (prellena Compras). Sync catálogo **no** borra proveedores.  

### Capas de datos

- **Operativo**: vitrina, solicitudes, compras, soporte, **Reportes simples (RS-01…12)**  
- **Landing**: `sales_records` (CSV, generate, post-convertir; Explorar ventas / export)  
- **Estratégico**: Tablero (Workpanel), **Informes compuestos (RC-01…08)** sobre `fact_ventas` + dims; tras convertir hay sync incremental  

Pago y correo son **simulados** (inbox in-app); suficientes para demo académica.

## Tests smoke

```powershell
pip install -r requirements.txt
$env:PYTHONPATH="C:\proyect6softwa\backend;C:\proyect6softwa"
.\.venv\Scripts\pytest.exe -q
```

## Estructura

- `frontend/` — app Flask + SPA estática  
- `backend/` — auth, config, shared, ETL  
- `paquetes/` — tablero, analisis, decisiones, ventas, shop, compras, datos, soporte  
- `specs/` — Spec Kit académico  

## Puertos

| Servicio | Puerto |
|----------|--------|
| Web Flask | 5001 |
| API FastAPI (health) | 8001 |
| MongoDB | 27017 |
