---
title: ADR-006 Transaction ledger as source of truth
status: accepted
date: 2026-09-19
tags: [adr]
---

# ADR-006 Transaction ledger as source of truth

## Context

Posiciones e histórico deben ser reproducibles.

## Decision

Ledger cronológico con Decimal y coste medio ponderado. Validar la secuencia completa al editar o borrar.

## Alternatives

Guardar posiciones mutables pierde trazabilidad; FIFO queda como estrategia futura.

## Consequences

Reconstrucción determinista; ventas sin posición y operaciones incompatibles se rechazan; cash derivado.

[[29 - ADR Index]]

