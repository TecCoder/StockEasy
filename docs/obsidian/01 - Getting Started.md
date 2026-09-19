---
title: Getting Started
tags: [guide]
---

# Inicio

Requisitos: Python 3.12+, Node 22+ y Git. Windows PowerShell desde la raíz del repositorio:

```powershell
Copy-Item .env.example .env
./scripts/dev.ps1 install
./scripts/dev.ps1 migrate
./scripts/dev.ps1 seed
./scripts/dev.ps1 backend
```

Segundo terminal: `./scripts/dev.ps1 frontend`. Abrir `http://127.0.0.1:5173`. Crear usuario con una contraseña de 12–256 caracteres. No existen credenciales predeterminadas ni registro público. La aplicación no requiere claves para iniciar sesión.

Con Make: `make install`, `make migrate`, `make seed`, `make dev` muestra ambos procesos. La base debe migrarse antes de abrir la aplicación. No se ejecutan migraciones implícitas al importar el módulo.

Ver [[21 - Docker]], [[22 - Configuration]], [[24 - Troubleshooting]].
