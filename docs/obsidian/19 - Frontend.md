---
title: Frontend
tags: [frontend]
---

# Frontend

React y TypeScript estricto, Vite, Tailwind y CSS con variables semánticas. Dark mode por defecto y light mode persistido por usuario. Sidebar en escritorio, compacta en tablet. Formularios con labels, foco visible y mensajes de error; no sustituir errores de carga por cifras cero.

`api/client.ts` concentra fetch, cookie same-origin, CSRF y traducción de errores. `hooks/useAuth.tsx` contiene la sesión en memoria y recupera `/auth/me` al cargar. `components/UI.tsx` define loading, empty, error y formato numérico. Las fórmulas monetarias pertenecen al backend; el navegador sólo presenta importes.

Vite proxy `/api` evita CORS permisivo. Docker usa nginx. Los rangos de gráfico se limitan a datos reales; Lightweight Charts conserva zoom, desplazamiento y crosshair.

Pruebas: Vitest + Testing Library + jsdom. `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`.
