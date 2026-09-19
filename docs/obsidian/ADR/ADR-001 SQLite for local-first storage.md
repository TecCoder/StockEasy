---
title: ADR-001 SQLite for local-first storage
status: accepted
date: 2026-09-19
tags: [adr]
---

# ADR-001 SQLite for local-first storage

## Context

La aplicación es local, privada y de un solo proceso.

## Decision

SQLAlchemy 2 y SQLite, migraciones Alembic explícitas. Importes Decimal exactos; migración posterior a PostgreSQL.

## Alternatives

PostgreSQL inicial exige administrar un servicio; archivos JSON carecen de integridad relacional.

## Consequences

Un único escritor; backups SQLite online con backup API. Antes de escalar workers revisar concurrencia y cuotas.

[[29 - ADR Index]]

