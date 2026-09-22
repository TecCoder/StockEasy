# StockEasy · Local Investment Tracker

Aplicación local de investigación y seguimiento de acciones, ETFs, fondos y criptomonedas. FastAPI + React + SQLite. Sin ejecución de órdenes ni conexión a brokers.

**Estado:** desarrollo incremental. Consulta [el roadmap](docs/obsidian/26%20-%20Roadmap.md) para ver las funciones verificadas y los límites pendientes. No hay datos de demostración en producción.

## Arquitectura y stack

Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic, httpx, Argon2id. React, TypeScript, Vite, Tailwind CSS, Lightweight Charts. Proveedores separados de los servicios y fórmulas financieras puras. SQLite persistente; ORM preparado para PostgreSQL.

## Inicio local en Windows

Después de instalar y crear el usuario, también puedes abrir **StockEasy** desde el acceso directo del escritorio. Este inicia backend y frontend, abre el navegador y mantiene ambos procesos vinculados. El botón **Salir** de la barra lateral cierra la sesión, detiene el backend y hace que el lanzador termine el frontend.

Para volver a crear el acceso directo manualmente:

```powershell
.\scripts\install-shortcut.ps1
```

Python 3.12+ y Node 22+ deben estar en PATH. Desde esta carpeta:

```powershell
Copy-Item .env.example .env
./scripts/dev.ps1 install
./scripts/dev.ps1 migrate
./scripts/dev.ps1 seed
./scripts/dev.ps1 backend
```

En un segundo terminal:

```powershell
./scripts/dev.ps1 frontend
```

Abre http://127.0.0.1:5173. No hay usuario o contraseña predeterminados. El comando `seed` pide una contraseña de al menos 12 caracteres sin escribirla en argumentos ni logs.

En macOS/Linux: `make install`, `make migrate`, `make seed`, y los dos comandos mostrados por `make dev`. Usa `.venv/bin/python` en lugar de `.venv/Scripts/python.exe`.

## Docker

```sh
docker compose up --build -d
docker compose exec backend python -m app.cli create-user --username tu_usuario
```

Abre http://127.0.0.1:8080. SQLite persiste en el volumen `stockeasy-data`. **No uses `docker compose down -v` si quieres conservar tus datos.** La validación de contenedores requiere Docker Desktop/daemon activo.

## Configuración

`.env.example` contiene las variables disponibles. Claves opcionales: `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`, `EODHD_API_KEY`, `TWELVE_DATA_API_KEY`, `COINGECKO_API_KEY`; `SEC_USER_AGENT` debe identificar tu aplicación y contacto. EODHD aporta búsqueda por ticker/ISIN y NAV histórico para fondos. Twelve Data aporta velas intradía de 1h y 4h y dispone de un plan Basic gratuito. Sin claves, la aplicación conserva funciones locales y muestra datos automáticos como no disponibles. Nunca pongas claves en variables `VITE_*`.

`DATABASE_URL` configura el almacenamiento. Los TTL, orígenes permitidos, duración de sesiones y Secure de cookies son configurables. El uso local HTTP requiere `COOKIE_SECURE=false`; cualquier futura instalación HTTPS debe activarlo.

## Pruebas y calidad

```powershell
./scripts/dev.ps1 test
./scripts/dev.ps1 lint
cd frontend
npm run build
```

Los tests usan fixtures y bases temporales; no dependen de APIs externas. OpenAPI: http://127.0.0.1:8000/api/docs.

## Proveedores y límites

Consulta [Market Data Providers](docs/obsidian/06%20-%20Market%20Data%20Providers.md), verificado el 2026-09-19. El histórico gratuito puede no cubrir SMA200, 5Y o 10Y. La ausencia de un dato nunca es cero. Las cotizaciones, estados financieros, fechas de publicación y cálculos deben conservar trazabilidad.

## Documentación

Abre `docs/obsidian/` como bóveda de Obsidian. Empieza por [00 - Home](docs/obsidian/00%20-%20Home.md). Incluye ERD, arquitectura, ADRs, fórmulas, proveedores, seguridad y roadmap. La carpeta preexistente `StockEasy/` se conserva fuera del repositorio.

## Seguridad

Sesiones opacas HTTPOnly/SameSite, CSRF, Argon2id, validación por propietario y límites de intentos de login. Sólo puertos loopback en el host. No registrar secretos, no subir `.env`, bases reales ni backups. El cifrado del disco y permisos de la cuenta del sistema protegen la base local.

## Capturas

Pendientes de incorporar tras verificar los primeros recorridos completos. No se utilizan capturas con datos ficticios para representar funciones terminadas.

## Licencia

Código bajo MIT; los datos financieros conservan los términos de sus respectivos proveedores.

Financial data is provided for informational purposes only. This application does not provide investment advice.
