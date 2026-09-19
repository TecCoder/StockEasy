---
title: Docker
tags: [operations]
---

# Docker

`docker compose up --build -d`. Frontend nginx en `127.0.0.1:8080`, backend sólo red interna, SQLite en volumen nombrado `stockeasy-data`. Backend Python 3.12, frontend Node 24 durante build. Procesos sin root. Migraciones antes de uvicorn. Healthcheck antes de iniciar nginx.

Crear usuario: `docker compose exec backend python -m app.cli create-user --username tu_usuario`.

No borrar el volumen al detener (`docker compose down`, sin `-v`). Para revisar fallos: `docker compose logs backend` y `docker compose ps`. No hay despliegue Internet.

> [!warning] Validación del entorno
> El cliente Docker está instalado pero el daemon no era accesible durante la implementación inicial. La configuración debe ejecutarse con Docker Desktop activo antes de considerar verificada la ruta de contenedores.
