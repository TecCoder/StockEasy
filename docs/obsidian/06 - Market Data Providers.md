---
title: Market Data Providers
aliases: [Market Data Providers]
verified: 2026-09-19
tags: [providers]
---

# Estrategia de proveedores

Verificación documental: **2026-09-19**. Las cuotas comerciales y permisos pueden cambiar. No se han verificado derechos de una clave concreta porque no hay claves configuradas.

| Fuente | Uso previsto | Autenticación | Restricción comprobada / política local |
|---|---|---|---|
| Alpha Vantage | Búsqueda, cotización EOD, histórico OHLCV, perfil | API key backend | 25 solicitudes/día; daily compact 100 observaciones; full y daily adjusted premium |
| FMP | Alternativa de búsqueda/perfil/EOD | API key backend | Basic anuncia 250/día y EOD; acceso depende del endpoint/símbolo; no asumir cobertura universal |
| SEC | companyfacts, submissions, identificación CIK | User-Agent con contacto real | Máximo publicado 10/s agregado; aplicación limita conservadoramente y cachea 24h |
| CoinGecko Demo | Búsqueda, cotización y serie de precios crypto | Demo key backend | Ver [[08 - CoinGecko]]; precios muestreados no son OHLC |
| Frankfurter v2 / ECB | FX diario | Sin API key | Sin cuota diaria publicada, protección antiabuso; caché por fecha |
| Manual | NAV/precio y FX | Sesión local | Propiedad del usuario, trazabilidad de autor y fecha |

## Interfaces

`MarketDataProvider`: search_assets, get_quote, get_historical_prices, get_company_profile.
`FundamentalDataProvider`: get_historical_fundamentals y proyecciones de income, balance, cash flow, ratios.
`CryptoDataProvider`: quote, market_history, metadata, search. `FXProvider`: tipo de cambio fechado. Los endpoints llaman a servicios; sólo los adaptadores conocen URLs y campos externos.

## Elección

Alpha Vantage es el contrato gratuito explícito para OHLC diario corto; FMP es un fallback optativo. SEC aporta fundamentales estadounidenses. CoinGecko evita mezclar ticker con ID de moneda. Frankfurter se consulta fijando ECB, manteniendo la fecha efectiva. Sin clave, la interfaz permite activos y precios manuales, y explica la ausencia de datos automáticos.

## Fuentes oficiales

- [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)
- [Alpha Vantage support / cuota](https://www.alphavantage.co/support/)
- [FMP planes](https://site.financialmodelingprep.com/developer/docs/pricing)
- [FMP EOD](https://site.financialmodelingprep.com/developer/docs/stable/historical-price-eod-full)
- [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC fair access](https://www.sec.gov/about/developer-resources)
- [CoinGecko Demo histórico](https://docs.coingecko.com/demo/reference/coins-id-market-chart)
- [CoinGecko límites](https://docs.coingecko.com/docs/errors-and-rate-limits)
- [Frankfurter](https://frankfurter.dev/)

## Límites de producto

SMA200 no estará disponible con sólo 100 sesiones. No rellenar con precios repetidos. Series de 5–10 años dependen de cobertura real o importación. El PER histórico requiere además EPS contemporáneo y bases de acciones compatibles. El histórico sectorial exige un universo fechado suficiente; sin él se muestra no disponible. La aplicación es privada/local; revisar términos específicos antes de redistribuir datos.
