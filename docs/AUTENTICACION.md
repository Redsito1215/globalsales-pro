# GLOBTRADE — Autenticación

## Uso

1. Abre http://127.0.0.1:5000
2. Pulsa **Crear cuenta** (esquina superior derecha)
3. Completa nombre, correo y contraseña (mín. 8 caracteres, letra y número)
4. El **primer usuario** registrado recibe rol **administrador**; los siguientes, **analista**

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register` | Crear cuenta |
| POST | `/api/auth/login` | Iniciar sesión |
| POST | `/api/auth/logout` | Cerrar sesión |
| GET | `/api/auth/me` | Usuario actual (sesión) |

## Acciones protegidas

| Acción | Rol requerido |
|--------|----------------|
| Cargar dataset (ELT) | administrador |
| Construir tablas maestras | administrador |
| Generar ventas (cuando esté activo) | administrador |

Consulta (dashboard, filtros, gráficos, pedidos) sigue disponible **sin sesión**.

## Calidad (ISO/IEC 25010)

- **Seguridad:** contraseñas con hash (Werkzeug), cookie HttpOnly, límite de intentos de login
- **Adecuación funcional:** validación de correo, contraseña y nombre antes de persistir
- **Fiabilidad:** sesión con caducidad configurable (`SESSION_DAYS` en `.env`)

## Variables de entorno

```
FLASK_SECRET_KEY=clave-larga-aleatoria
SESSION_DAYS=7
```
