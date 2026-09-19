---
title: Authentication
tags: [security]
---

# Autenticación local

Usuarios creados por CLI con getpass. Username normalizado a minúsculas. Argon2id almacena un hash con salt aleatorio y parámetros incluidos; se actualiza tras login si cambia la política.

El login genera un token aleatorio de 256 bits, guarda sólo SHA256 del token, y entrega cookie `stockeasy_session`, HTTPOnly, SameSite=strict, Path=/. Caduca tras 12 horas configurables. CSRF se devuelve en login/me y se guarda únicamente en memoria de React, enviado como X-CSRF-Token en mutaciones.

Origin se valida en mutaciones (incluido login). Requests sin Origin son clientes CLI y necesitan sesión/CSRF para operaciones protegidas. TrustedHost limita DNS rebinding. Los intentos de login se cuentan por IP, incluso si el username no existe: máximo 20/15min, persistido. Un hash ficticio iguala el trabajo de verificación de usuarios desconocidos.

Logout elimina la sesión. Cambio de contraseña comprueba la anterior y revoca todas las sesiones. El frontend nunca almacena tokens en localStorage. Secure=false sólo para HTTP loopback; activar en futuras instalaciones HTTPS.

Ver [[ADR-007 Authentication architecture]], [[23 - Security]].
