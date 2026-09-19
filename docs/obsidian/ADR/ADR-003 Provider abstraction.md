---
title: ADR-003 Provider abstraction
status: accepted
date: 2026-09-19
tags: [adr]
---

# ADR-003 Provider abstraction

## Context

Cobertura, licencias y cuotas cambian.

## Decision

Contratos normalizados y adaptadores independientes; cache y cuotas persistentes.

## Alternatives

Llamadas directas en controllers dificultan sustituir fuentes.

## Consequences

Datos ausentes explícitos; conservar origen, fecha y limitaciones de cada resultado.

[[29 - ADR Index]]

