# Completeness on the current flagship — and why this one did *not* expire

**2026-08-21.** Defect-avoidance had just gone from **+0.19** to **+0.000** between
`claude-sonnet-4.6` (Feb 2026) and `claude-sonnet-5` (Jun 2026). The obvious worry was
that completeness — this project's most-cited number — had eroded the same way. It has
not.

| build model | `without` | `with` | lift |
|---|--:|--:|--:|
| `claude-sonnet-4.6`, run A | 0.60 | 0.99 | +0.39 |
| `claude-sonnet-4.6`, run B | 0.57 | 0.97 | +0.40 |
| **`claude-sonnet-5`** | **0.62** | **1.00** | **+0.38** |

Judge held constant at `anthropic/claude-opus-4.8` — the judge is the instrument, so only
the build model changed. `--samples 1 --temp 0.0 --max-tokens 64000`; **zero truncation
warnings**, so this is a measurement and not a floor.

+0.38 against +0.39/+0.40 is **unchanged** at this resolution: the noise floor here is
≈±0.03 at n=1, established the same day by the untreated arm moving 0.60 → 0.57 between
identical runs.

## Why one result expired and this one didn't

Look at what the newer model still forgets when nobody asks, across the 7 unguided builds:

| omitted item | cases (of 7) |
|---|--:|
| **tests** | **7** |
| transport / TLS | 5 |
| rate limiting | 5 |
| structured logging | 3 |

Those are the *same* blind spots `sonnet-4.6` had. A model that no longer writes SQL
injection or a missing ownership check **still omits tests in every single case**.

That is the distinction the two results draw together:

- **Knowledge gaps close with model progress.** "Do not interpolate into `ORDER BY`" is a
  fact about code. Newer models know it, and the library's defect-avoidance lift went to
  zero accordingly.
- **Salience gaps do not.** "Add rate limiting to an endpoint nobody mentioned" is not a
  knowledge failure — the model can state the rule if asked. It is an attention failure
  under a task that never raised the topic, and four months of capability gain did not
  touch it.

This is consistent with the project's own root-cause work
([WHY-COMPLETENESS-RESIDUAL.md](../../../docs/WHY-COMPLETENESS-RESIDUAL.md)): the residual
was a salience/attention effect, and *adding* the missing rule made it worse while a short
salient reminder fixed it.

**Consequence for the value proposition:** the durable part of this library is not telling
a model things it does not know. It is making the cross-cutting concerns *salient at the
moment of writing* — which is a failure mode that scales with task length and context
pressure, not with model weakness.

## Limits

- **n=1.** A change smaller than ≈0.05 is unresolvable here.
- One task set (7 build tasks), one judge model.
- The `with` arm hit **1.00** — at ceiling, so this design cannot detect further
  improvement, only erosion.
