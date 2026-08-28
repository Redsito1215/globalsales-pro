# Research: Gestión Profesional en 11 Fases

## Decisión: consola integrada

**Rationale**: Las fases comparten filtros, búsquedas y entidades. Una consola reduce navegación y mantiene independencia mediante pestañas.

**Alternatives considered**: Once páginas independientes; ampliar el centro de decisiones. Una fragmenta la experiencia y la otra mezcla gestión táctica con análisis estratégico.

## Decisión: proyecciones sobre datos existentes

**Rationale**: Productos, clientes, proveedores, pedidos, inventario y auditoría ya tienen fuentes confiables. Las fichas deben componerlas, no copiarlas.

**Alternatives considered**: Colecciones duplicadas o materialización completa en ClickHouse; ambas añaden sincronización innecesaria.

## Decisión: persistir únicamente metas y aprobaciones

**Rationale**: Son las únicas entidades nuevas con ciclo de vida propio. Se guardan en colecciones operativas y se auditan con el servicio existente.

**Alternatives considered**: Archivos de configuración o notificaciones; no ofrecen ciclo de vida suficiente.

## Decisión: tolerancia por fuente

**Rationale**: Cada agregado captura fallos de su fuente y devuelve datos parciales, de modo que una caída analítica no inutiliza la gestión operativa.

**Alternatives considered**: Fallar toda la respuesta u ocultar el error.

## Decisión: no crear seguridad empresarial

**Rationale**: El usuario la excluyó expresamente. Se mantienen sesión y permisos vigentes como infraestructura, sin nuevas políticas, pantallas o endurecimiento.

**Alternatives considered**: Ninguna dentro del alcance.
