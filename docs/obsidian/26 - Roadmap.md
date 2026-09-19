---
title: Roadmap
tags: [roadmap]
---

# Roadmap y registro de entrega

## Fases

- [x] 0 — Arquitectura, ERD, proveedores, ADRs, riesgos y estructura.
- [ ] 1 — Foundation: implementación nativa verificada (4 tests backend, 1 frontend, lint, tipos, build y upgrade/downgrade Alembic); Docker preparado, ejecución pendiente de daemon.
- [ ] 2 — Assets & Market Data: contratos, fuentes, caché, cuotas, watchlists, gráficos.
- [ ] 3 — Technical Analysis: SMA, EMA, RSI, MACD, Bollinger, volumen.
- [ ] 4 — Fundamentals: SEC, períodos, revisiones, métricas e históricos.
- [ ] 5 — Historical Valuation: EPS point-in-time, PER, percentiles, peers y sector.
- [ ] 6 — Portfolio: ledger, coste medio, P/L, dividendos, FX e histórico.
- [ ] 7 — Analytics: allocation, performance, XIRR y TWR con cobertura suficiente.
- [ ] 8 — Screener local: filtros combinables y guardados sobre datos disponibles.
- [ ] 9 — Hardening: seguridad, backup/restore, CSV, documentación y rendimiento.

## Criterio por fase

Función utilizable, loading/error/empty states, tests deterministas, lint, typecheck, migración cuando proceda, documentación y commit. La ejecución Docker requiere un daemon disponible. Una fase con una comprobación pendiente no se declara completa.

## v0.1.0

Login; buscar y seguir acciones; histórico con rangos y SMA50/200/RSI cuando hay cobertura; fundamentales y evolución de ingresos/EPS/FCF; PER histórico cuando se puede construir sin sesgo; cartera con compras/ventas/dividendos y crypto; exportación; backup; documentación; CI; GitHub privado. No crear el tag hasta verificar los criterios.

## Futuro (fuera del alcance inicial)

PostgreSQL; OAuth; alertas de precio/valoración/filings; calendarios de resultados/dividendos; insiders e institucionales; ETF holdings; indicadores macro; dashboards personalizados; comparaciones múltiples; benchmarks S&P500/MSCI World/Bitcoin; Monte Carlo; escenarios; DCF y reverse DCF; aplicaciones móviles. Brokers sólo tras una petición posterior, nunca ejecución de órdenes en este proyecto inicial.
