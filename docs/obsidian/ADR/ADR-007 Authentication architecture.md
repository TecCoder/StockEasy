---
title: ADR-007 Authentication architecture
status: accepted
date: 2026-09-19
tags: [adr]
---

# ADR-007 Authentication architecture

## Context

Autenticación local preparada para usuarios independientes.

## Decision

Argon2id y sesiones opacas almacenadas como hash; cookie HTTPOnly SameSite=strict y CSRF; alta inicial por CLI.

## Alternatives

JWT en localStorage expone tokens a JavaScript y complica revocación; OAuth no requerido.

## Consequences

Sesiones revocables, caducidad, limitación de login; cambiar contraseña revoca sesiones; HTTPS exige Secure.

[[29 - ADR Index]]

