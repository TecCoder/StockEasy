---
title: SEC EDGAR
tags: [providers, fundamentals, sec]
---

# SEC EDGAR

SEC EDGAR es la fuente primaria de empresas registradas y fundamentales XBRL de Estados Unidos. No requiere cuenta ni API key. Cada petición debe enviar un `User-Agent` que identifique la aplicación y un correo de contacto real.

## Configuración

```dotenv
SEC_USER_AGENT=StockEasy Nombre contacto@ejemplo.com
```

La variable vive únicamente en el backend. No es un secreto, pero no se envía al frontend.

## Descubrimiento de empresas

`GET /api/assets/search?q=...` consulta `company_tickers_exchange.json`, filtra localmente por ticker o razón social y devuelve hasta 30 coincidencias. Cada resultado incluye ticker, nombre, mercado, divisa USD y CIK. Al pulsar **Añadir**, el CIK se conserva en el activo y permite consultar fundamentales sin otra resolución.

La SEC no proporciona cotizaciones. Un activo descubierto mediante SEC necesita un proveedor de mercado separado o precios manuales para gráficos y valoración.

## Fundamentales

`companyfacts` proporciona hechos XBRL de formularios 10-K y 10-Q. StockEasy conserva concepto original, unidad, periodo, fecha de presentación, accession y descarga. Los ratios derivados solo se calculan con periodos y unidades compatibles.

## Caché y límites

El catálogo y los perfiles usan caché local. Los fundamentales se actualizan como máximo una vez al día salvo actualización manual. El gateway limita SEC de forma conservadora a una petición por segundo, por debajo del máximo publicado de diez peticiones por segundo.

## Fuentes oficiales

- [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC developer resources and fair access](https://www.sec.gov/about/developer-resources)

Última verificación: 2026-09-19.

Relacionado: [[06 - Market Data Providers]], [[ADR-004 SEC EDGAR fundamentals]], [[16 - Caching]], [[17 - API Rate Limits]].
