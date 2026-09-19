---
title: CoinGecko
verified: 2026-09-19
tags: [providers, crypto]
---

# CoinGecko Demo

Base `https://api.coingecko.com/api/v3`; cabecera `x-cg-demo-api-key`. Endpoints: `/search`, `/simple/price`, `/coins/{id}/market_chart`, `/coins/{id}`. El identificador es el ID de CoinGecko, no BTC/ETH; se conserva en ProviderMapping. Un ticker crypto puede identificar múltiples monedas.

Documentación [Demo history](https://docs.coingecko.com/demo/reference/coins-id-market-chart) y [Rate limits](https://docs.coingecko.com/docs/errors-and-rate-limits), consultadas 2026-09-19: Demo anuncia 100/min y 365 días de histórico; todos los HTTP cuentan, incluidos errores. La aplicación usa límites conservadores 30/min, 300/día y 9000/mes, no una afirmación de cuota comercial mensual. Revalidar el plan en la cuenta.

Mapping: `prices: [[timestamp_ms, price]]` se convierte en fecha UTC + cierre muestreado. No crear velas a partir de una observación. `simple/price` conserva moneda solicitada, fecha last_updated_at, market_cap y cambio de 24h si existe. TTL quote 15min, history 24h, metadata 7d. Errores de clave/plan/límite se muestran saneados; fallback a caché etiquetada como antigua.

La UI incluye atribución. Datos para uso informativo local; revisar términos antes de redistribución. [[06 - Market Data Providers]]
