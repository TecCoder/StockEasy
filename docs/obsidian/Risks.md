---
title: Risks
tags: [risk]
---

# Riesgos y mitigaciones

| Riesgo | Impacto | Decisión |
|---|---|---|
| Histórico gratuito insuficiente | SMA200/5Y no calculable | Mostrar cobertura, null y causa; proveedor intercambiable |
| EPS restatements y splits | PER falso | Mantener filing/accession; filtrar conocimiento y base de acciones |
| XBRL acumulado vs trimestre | TTM doble contado | Clasificar duración; derivar Q4 sólo con períodos compatibles; exigir continuidad |
| Divisas faltantes | Rentabilidad incorrecta | Nunca FX=1 salvo misma moneda; total incompleto |
| Tickers duplicados | Activo incorrecto | ID interno y exchange/provider mappings |
| Fallo/red/cuota | Bloqueo de UI | Timeout, backoff acotado, caché stale etiquetada |
| Cuotas tras reinicio | Exceso de peticiones | Contadores persistentes y único worker |
| Datos privados en Git | Exposición | Ignore, secret scan y repositorio privado |
| XSS/CSRF local | Mutaciones no autorizadas | Cookie HTTPOnly, SameSite, CSRF, verificación Origin, CSP |
| Restauración sobre DB viva | Corrupción/pérdida | Restore offline, integridad y backup previo |
| Poco universo sectorial | Sesgos/outliers | Mediana, cobertura explícita, mínimo de muestra |
| Docker no disponible | Validación incompleta | Camino nativo documentado; no afirmar Docker probado |
| GitHub sin permiso de creación | Entrega remota bloqueada | Mantener commits locales, comunicar evidencia exacta |

## Entorno observado

Windows, Python 3.14.3, Node 24.15.0, Git 2.40.0, cliente Docker 27.4.0. Docker daemon no accesible. La integración GitHub reconoce TecCoder pero devuelve lista vacía. Obsidian CLI instalado, aplicación no detectada. No había código previo; existe una bóveda de bienvenida que se preserva.
