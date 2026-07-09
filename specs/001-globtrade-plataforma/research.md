# Research: Plataforma Web GLOBTRADE

## Decision: Mantener Flask como aplicacion principal

**Rationale**: `frontend/app.py` ya registra `auth_bp` y `tablero_bp`, sirve la SPA
en `frontend/static/index.html` y usa la configuracion existente. Extender con
blueprints por paquete reduce cambios y mantiene coherencia con Kiro.

**Alternatives considered**:
- Migrar todo a FastAPI: descartado porque Q1 y la UI actual ya estan integrados en Flask.
- Crear una segunda app: descartado por la constitucion de raiz unica.

## Decision: Reutilizar `backend/auth` para sesiones y roles

**Rationale**: Ya existen rutas `/api/auth/register`, `/api/auth/login`,
`/api/auth/logout`, `/api/auth/me` y decoradores `login_required` y
`admin_required`. Reutilizarlos evita duplicar seguridad en `paquetes/acceso`.

**Alternatives considered**:
- Crear `paquetes/acceso` desde cero: descartado por duplicacion; solo se usaria como fachada documental si el docente exige esa carpeta.

## Decision: Implementar Q3 antes que Q2/Q4

**Rationale**: Q3 usa las consultas de pedidos ya presentes en Q1 y entrega un
flujo operativo independiente. Es el siguiente incremento con menor riesgo.

**Alternatives considered**:
- Hacer Q2 primero: viable, pero agrega vistas analiticas antes de completar el flujo de ventas.
- Hacer Q4 primero: requiere ELT/modelado y permisos, mayor dependencia transversal.

## Decision: GET publico, acciones sensibles protegidas

**Rationale**: Los requisitos indican que el visitante explora sin cuenta, pero
exportar, generar o modificar datos requiere sesion. Los endpoints GET de lectura
se mantienen publicos; POST/PUT/DELETE usan decoradores de rol.

**Alternatives considered**:
- Proteger todo Q1-Q4: descartado porque contradice el requisito de visitante.
- Permitir escritura sin sesion durante demo: descartado por riesgo y por constitucion.

## Decision: Validacion manual enfocada para demo academica

**Rationale**: El proyecto actual no contiene suite de pruebas. Para avanzar sin
introducir infraestructura pesada, cada historia incluye criterios de validacion
manual en navegador/API y se pueden agregar pruebas Python puntuales si aparece
riesgo alto.

**Alternatives considered**:
- TDD completo: deseable, pero excede el estado actual del proyecto y no es requisito explicito.
