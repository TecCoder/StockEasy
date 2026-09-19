---
title: Caching
tags: [providers]
---

# Caché persistente

ApiCache persiste payload, proveedor, fetched_at y expires_at. La clave SHA256 usa proveedor/URL/parámetros funcionales y excluye la clave API. Las cabeceras no se persisten. Sin cache hit, Gateway reserva cuota antes de cada intento.

Quote 900s, history/fundamentals/FX 86400s, profile/search 604800s configurables. Refresh ignora TTL pero respeta todos los límites. Errores usan la última respuesta disponible con `stale=true` y warning. No se cachean 429 ni mensajes de error HTTP200.

AssetPrice conserva históricos descargados aunque venza la caché; upsert por activo/fecha/proveedor. Alpha Vantage compact no permite pedir sólo el tramo faltante, por lo que se recupera su ventana corta una vez al día. CoinGecko Demo recupera una ventana de 365 días diaria; no se descarga al abrir repetidamente. SEC companyfacts tampoco expone delta; se conserva caché diaria y se ingieren facts por accession.

[[17 - API Rate Limits]], [[06 - Market Data Providers]]
