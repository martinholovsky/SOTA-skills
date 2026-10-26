# ADS: password spray

## Goal
Detect password spraying against the IdP.

## Technical context
Runs on IdP sign-in logs.

## Validation
Atomic Red Team T1110.003 replayed 2026-10-01; alert fired in 40 s.

## Response
Lock the source and notify the owner.
