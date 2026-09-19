---
title: API Rate Limits
tags: [providers]
---

# Límites y fallos

Gateway mantiene por proveedor ventanas minuto/día UTC/mes UTC, failures, última petición, último éxito y retry_after. Reserva antes de HTTP y persiste. RLock protege reservas concurrentes dentro del único proceso soportado. SEC además espacia al menos 1 segundo entre peticiones. Varias instancias requieren un coordinador compartido; no lanzar varios workers.

429: respeta Retry-After numérico o fecha HTTP sin mantener bloqueada la petición del usuario. 401/402/403: pausa de 15min. HTTP200 con Note/Information/Error Message/error: no se trata como dato. 5xx/timeouts: máximo dos intentos, backoff corto y circuito de 30s tras fallo. Timeout por intento 12s. No registrar URL ni cuerpo externo (pueden incluir claves).

La pantalla Estado de datos muestra contadores y fecha del contador (los contadores se reinician al siguiente intento), caché y fallos. Un proveedor configurado no significa conexión verificada.
