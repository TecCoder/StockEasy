---
title: Technical Indicators
tags: [analytics]
---

# Indicadores técnicos

Implementaciones puras en `analytics/technical.py`, probadas con referencias numéricas. Ningún indicador se solicita a una API comercial.

| Indicador | Método | Warm-up |
|---|---|---|
| SMA20/50/100/200 | media aritmética móvil | N-1 |
| EMA20/50/200 | semilla SMA, alpha=2/(N+1) | N-1 |
| RSI14 | Wilder, medias recursivas de ganancias/pérdidas | 14 cambios |
| MACD12/26/9 | EMA12-EMA26 y EMA9 de valores válidos | línea 25; señal 33 |
| Bollinger20/2 | SMA20 ± 2 desviaciones población (ddof=0) | 19 |
| AverageVolume20 | SMA20 del volumen cuando todos los datos existen | 19 |

Flat RSI=50, sólo ganancias=100, sólo pérdidas=0. No interpolar. Se calcula toda la serie antes del recorte temporal para conservar warm-up. RSI y MACD en paneles separados; overlays sobre precio. La UI usa línea si no existen OHLC genuinos. Los precios raw pueden tener discontinuidades por splits; no se presenta como total return.

[[28 - Financial Formulas]], [[20 - Testing]]
