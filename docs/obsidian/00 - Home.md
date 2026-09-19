---
title: StockEasy — Local Investment Tracker
tags: [stockeasy, documentation]
---

# StockEasy

Aplicación local de seguimiento y análisis de acciones, ETFs, fondos y criptoactivos. El libro de transacciones es la fuente de verdad; los datos ausentes nunca se sustituyen por cifras de demostración.

## Leer primero

- [[01 - Getting Started]]
- [[02 - Architecture]]
- [[04 - Database Model]]
- [[06 - Market Data Providers]]
- [[26 - Roadmap]]
- [[29 - ADR Index]]
- [[Risks]]

## Principios

Datos monetarios con Decimal; precios y fechas de publicación separados; caché persistente; contratos de proveedor independientes; cookies de sesión HTTPOnly; aislamiento por usuario; sin ejecución de órdenes. SQLite y un solo proceso backend inicialmente.

> [!warning] Alcance
> Un endpoint documentado no garantiza acceso gratuito para cualquier símbolo. Las funciones financieras deben indicar su cobertura y los datos que faltan. Consultar el roadmap para distinguir implementación verificada de diseño futuro.

Financial data is provided for informational purposes only. This application does not provide investment advice.
