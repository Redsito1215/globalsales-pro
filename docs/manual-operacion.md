# Manual de operación y entrega — GLOBTRADE

Actualizado: 24 de agosto de 2026.

## 1. Preparación

Requisitos: Docker Desktop, puertos 5001 y 27017 disponibles, y el archivo `.env` creado desde `.env.example` con una clave de sesión propia.

```powershell
cd C:\proyect6softwa
docker compose up -d --build
docker compose exec web python scripts/verify_release.py
```

La aplicación queda disponible en `http://127.0.0.1:5001`. El primer usuario registrado recibe el rol administrador; después debe crearse al menos otro administrador para evitar depender de una sola cuenta.

## 2. Roles y recorridos

- Cliente: tienda, carrito, solicitudes propias, pago con tarjeta mediante autorización interna, seguimiento, notificaciones, perfil y soporte.
- Vendedor: aprobación de solicitudes, pedidos, despacho, entrega, devoluciones, inventario y compras según permisos asignados.
- Analista: tablero, análisis, decisiones, informes y exportaciones, sin escritura operativa.
- Administrador: acceso integral, usuarios y roles, maestros, políticas comerciales, contabilidad, auditoría, empresa, respaldos y estado del sistema.

Los roles personalizados se gestionan en “Roles y usuarios”. Las páginas controlan visibilidad y los permisos controlan acciones; ocultar un menú no sustituye la autorización del servidor.

## 3. Reglas críticas

1. Una solicitud debe aprobarse antes de aceptar el pago.
2. No puede convertirse, enviarse ni entregarse sin pago completo, salvo la excepción comercial expresamente configurada.
3. Los intentos de tarjeta no almacenan CVV ni el número completo.
4. Los pagos duplicados se rechazan por referencia e idempotencia.
5. Las devoluciones generan contrapartidas de caja e inventario; los productos dañados se registran como merma.
6. Los períodos contables cerrados no aceptan movimientos retroactivos.
7. Los maestros relacionados se inhabilitan; no se eliminan si romperían historial o referencias.
8. La auditoría conserva actor, fecha, módulo y comparación anterior/nueva con campos sensibles protegidos.

## 4. Operación diaria

- Revisar “Salud del sistema” y errores abiertos.
- Revisar solicitudes pendientes, pagos y cartera vencida.
- Confirmar stock disponible, comprometido, dañado y en tránsito.
- Conciliar pedido, pago, factura y caja.
- Atender notificaciones y soporte.
- Al final del período, verificar diferencias y ejecutar el cierre contable.

## 5. Respaldo y recuperación

```powershell
.\scripts\backup_mongo.ps1
python scripts\verify_backups.py
```

El respaldo incluye `globtrade_ops` y `globtrade_dw`. Antes de limpiar, cargar o reconstruir información se debe generar y verificar un respaldo. La restauración debe ejecutarse fuera de la aplicación por una persona autorizada y primero probarse en una base separada.

## 6. Validación

```powershell
docker compose run --rm -T `
  -v C:/proyect6softwa/tests:/app/tests:ro `
  -v C:/proyect6softwa/etl_proceso:/app/etl_proceso:ro `
  -v C:/proyect6softwa/airflow:/app/airflow:ro `
  -v C:/proyect6softwa/scripts:/app/scripts:ro `
  web python -m pytest -q
```

Última regresión registrada: 125 pruebas aprobadas, 0 fallos.

Histórico analítico vigente: 2.000.000 registros desde 2010-01-01 hasta 2026-08-24, distribuidos en 200 meses continuos. Su reconstrucción controlada se realiza con `scripts/replace_analytics_dataset.py` y requiere respaldo previo.

## 7. Límites de integración

- El procesamiento de tarjeta usa autorización interna y no comunica con un banco ni una pasarela externa.
- La contraseña solo puede cambiarse desde el perfil autenticado. No existe recuperación por correo ni integración con servicios externos.
- La emisión tributaria depende de la configuración fiscal y no reemplaza la certificación u homologación exigida por la autoridad tributaria.
- No se incluyen movimientos ni transferencias entre bodegas.

Estas condiciones no impiden validar el flujo funcional, contable y de permisos, pero deben resolverse antes de operar con dinero real o emitir documentos tributarios oficiales.
