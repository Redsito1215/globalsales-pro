# Quickstart: Validación de las 11 fases

## Prerrequisitos

- MongoDB operativo accesible con los datos actuales.
- Dependencias instaladas desde `requirements.txt`.
- Usuario interno con sesión iniciada.

## Ejecución

1. Ejecutar `python frontend/app.py`.
2. Abrir `http://127.0.0.1:5001` e iniciar sesión.
3. Entrar en **Táctico → Gestión profesional**.
4. Recorrer las pestañas 1–11 y confirmar carga, vacío y error comprensibles.
5. Buscar fichas de producto y cliente existentes.
6. Crear una meta y comprobar avance.
7. Crear una aprobación y resolverla.
8. Buscar el cambio en Historial.
9. Ejecutar una búsqueda global de al menos dos caracteres.
10. Reducir el ancho del navegador y confirmar que la interfaz sigue siendo utilizable.
11. Abrir Experiencia y comprobar logística, pronóstico, rentabilidad y fidelización.
12. Editar transportista, guía y fecha estimada de un envío activo.
13. Abrir Calidad y comprobar las reglas de registros incompletos o inválidos.
14. Confirmar en Airflow que el DAG conserva ejecución manual y programación diaria a las 02:00.
15. Crear una requisición desde una fila del pronóstico y comprobar que aparece en Compras.
16. Crear campañas para VIP, frecuentes y clientes por reactivar.
17. Revisar comparaciones por producto, categoría, cliente y región.
18. Descargar el PDF de Operación avanzada.
19. Registrar un lote con fecha de caducidad y abrir su trazabilidad.
20. Crear una lista de precios para un cliente o canal y comprobar su aplicación al comprar.
21. Devolver una cantidad de un solo producto y confirmar que el pedido queda en devolución parcial.
22. En Operación avanzada, pulsar **Verificar ahora** y comprobar las filas publicadas en ClickHouse.
23. Crear una lista con varios productos y comprobar un ajuste porcentual.
24. Crear una meta de vendedor y revisar avance, ventas netas y comisión.
25. Entregar la prueba guiada a una persona, marcar las tareas realizadas y guardar su observación.
26. Abrir Decisiones: la primera carga debe completarse alrededor de un segundo y una actualización con los mismos filtros debe usar caché inmediata.
27. Conciliar una existencia mediante conteo físico y comprobar el movimiento de inventario.
28. Crear un cierre mensual y revisar el resumen financiero, inventario y comisiones congelado.
29. Verificar un respaldo y ensayar el comando de restauración protegida con su confirmación exacta.

## Pruebas automatizadas

Ejecutar `pytest -q tests/test_professional_center.py`.

## Resultado esperado

Las once fases están accesibles, los fallos parciales no bloquean toda la vista y metas/aprobaciones conservan trazabilidad.
