---
title: Project Structure
tags: [architecture]
---

# Estructura

```text
backend/app/{api,auth,core,db,models,schemas,services,providers,analytics,portfolio}
backend/alembic/versions
backend/tests
frontend/src/{api,components,pages,hooks,types,utils}
docs/obsidian/ADR
scripts
docker
.github/workflows
```

Los tests usan bases temporales. `data/`, `.env`, claves y backups quedan fuera de Git. La bóveda preexistente `StockEasy/` se conserva separada; `docs/obsidian/` es la bóveda versionada del proyecto.
