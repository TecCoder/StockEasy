---
title: Configuration
tags: [configuration]
---

# Configuración

`.env` en la raíz, excluido de Git. Pydantic Settings lee variables del proceso con prioridad. Las rutas SQLite relativas dependen del directorio de ejecución; los scripts inician el backend en `backend/`. El default sin `.env` usa ruta absoluta al `data/` del proyecto.

| Variable | Finalidad |
|---|---|
| DATABASE_URL | SQLite local o futuro PostgreSQL |
| ALLOWED_ORIGINS | Lista separada por comas, sin barra final |
| COOKIE_SECURE | false para localhost HTTP; true con HTTPS |
| SESSION_HOURS | Caducidad absoluta de sesión |
| ALPHA_VANTAGE_API_KEY / FMP_API_KEY / COINGECKO_API_KEY | Sólo backend |
| SEC_USER_AGENT | Aplicación, nombre y contacto real, obligatorio para SEC |
| QUOTE_TTL / HISTORY_TTL / FUNDAMENTAL_TTL / PROFILE_TTL / FX_TTL | Segundos |

Después de modificar `.env`, reiniciar backend. Las preferencias de apariencia/moneda se guardan en SQLite por usuario. No se guardan claves de API en tablas de preferencias.
