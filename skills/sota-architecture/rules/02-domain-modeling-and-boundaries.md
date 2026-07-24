# 02 — Domain Modeling & Boundaries (DDD, Hexagonal, Clean Layering)

Rules for carving the domain into bounded contexts, modeling aggregates, and
keeping dependencies pointed the right way. These rules apply identically inside
a monolith module and across services.

## 1. Bounded contexts first, services second

**Rule:** Identify bounded contexts (areas where a model and its language are
internally consistent) before drawing any service or module boundary. A service
boundary that splits a bounded context, or fuses two, will generate chatty calls
and translation bugs forever.

**Rule:** One term, one meaning per context. If "Customer" means payer in
Billing and recipient in Shipping, those are two models in two contexts —
never one shared `Customer` class with 40 nullable fields.

```text
BAD:  shared `Customer` entity used by Billing, Shipping, Support
      → every change fans out to all three; fields nobody owns.
GOOD: Billing.Payer, Shipping.Recipient, Support.Contact
      Each context maps from `CustomerRegistered` events into its own model.
```

**Rule:** Maintain a context map: which contexts exist, who owns each, and the
relationship type at every seam (customer/supplier, conformist, anti-corruption
layer, published language, separate ways). Unlabeled seams default to accidental
conformist coupling.

## 2. Use ubiquitous language end to end

**Rule:** Code, schema, APIs, and events use the domain experts' vocabulary
exactly. If the business says "quote expires," the code says `quote.expire()`,
not `setStatus(3)`. Translation between business language and code language is
where requirements bugs breed.

**Rule:** When the business distinguishes two things, the model distinguishes
them (no boolean flags standing in for missing concepts: `isReturn && isExchange`
means you're missing a `ResolutionType`).

## 3. Aggregates: small, consistent, the only write path

**Rule:** An aggregate is a consistency boundary: the set of objects that must
be transactionally consistent with each other. Keep aggregates small — usually
one entity plus value objects. Big aggregates serialize writes (lock contention)
and bloat loads.

**Rule:** One transaction modifies one aggregate. Cross-aggregate consistency is
eventual, coordinated by domain events or sagas (rules/03). If you "need" to
update two aggregates atomically, your boundary is wrong or the invariant is
weaker than you think — interrogate the invariant first.

**Rule:** Reference other aggregates by ID, never by object pointer. Loading an
order must not drag the customer, the product catalog, and the warehouse into
memory.

**Rule:** All writes go through aggregate methods that enforce invariants.
No service-layer code mutating aggregate fields directly; no "anemic" model
where entities are bags of getters and the rules live in 12 service classes.

```text
GOOD: order.addLine(product_id, qty)   # enforces max-lines, status checks inside
BAD:  order.lines.append(line); order.total += price   # invariants enforced nowhere
```

**Rule:** Enforce uniqueness and cross-aggregate invariants at the right layer:
DB unique constraints for identity invariants; reservation patterns or eventual
checks for the rest. Don't pretend an aggregate can guard an invariant spanning
millions of rows.

## 4. Hexagonal architecture: ports and adapters

**Rule:** The domain core depends on nothing but itself. Define **ports**
(interfaces the core needs: `OrderRepository`, `PaymentGateway`, `Clock`,
`EventPublisher`) inside the core; implement **adapters** (Postgres, Stripe,
Kafka, system clock) outside it. Frameworks, ORMs, and SDK types never appear
in core signatures.

**Rationale:** This is what makes the core testable without infrastructure and
makes Type 1 dependencies (rules/01 §6) swappable. It is also the cheapest
insurance against vendor lock-in you can buy.

**Rule:** Ports are defined by the consumer's need, not the provider's API.
`PaymentGateway.charge(order_id, amount) -> ChargeResult`, not a passthrough of
Stripe's 40-field request object. A port that mirrors the vendor SDK is a leaky
abstraction (rules/07).

```text
        inbound adapters              core                outbound adapters
  HTTP handler ──► CommandHandler ──► Domain ──► OrderRepository (port)
  Kafka consumer ─► (use case)        model      └─► PostgresOrderRepo (adapter)
                                          └─► PaymentGateway (port)
                                               └─► StripeAdapter
```

## 5. Layering and the dependency rule

**Rule:** Dependencies point inward only: `adapters → application (use cases) →
domain`. Nothing in domain imports application; nothing in application imports
adapters. Enforce with architecture tests (rules/01 §2), not convention.

**Rule:** Use cases (application services) orchestrate: load aggregate, call
domain method, persist, publish events. They contain no business rules and no
I/O details. If a use case has an `if` encoding a business policy, push it into
the domain; if it builds SQL, push it into an adapter.

**Rule:** Don't over-layer. A CRUD-only context doesn't need aggregates, ports,
and four layers — a transaction script over a table is honest and cheaper.
Match modeling rigor to domain complexity: core domains get full DDD; supporting
and generic subdomains get the simplest thing that works. Applying ceremony
uniformly is itself an anti-pattern.

## 6. Anti-corruption layers at external seams

**Rule:** Every integration with an external system or legacy model goes through
an anti-corruption layer (ACL): a translator that maps their model to yours at
the boundary. External DTOs, vendor enums, and legacy field names stop at the
ACL; they never propagate into the domain.

**Rule:** When consuming another context's events, translate to your own types
in the consumer adapter. Storing someone else's event payload as your domain
state couples your model to their release schedule.

## 7. Domain events as first-class outputs

**Rule:** Aggregates record domain events (`OrderPlaced`, `QuoteExpired`) as
part of their state changes; the application layer publishes them after commit
(via outbox — rules/03 §4). Events are named in past tense, in ubiquitous
language, and carry the data consumers need without forcing a callback query
for every field ("event-carried state transfer" for hot fields, IDs for the rest).

**Rule:** Events published across context boundaries are a public contract:
versioned, schema-checked, additive-only changes by default (see rules/03 §8).
Internal events can change freely; published ones cannot.

## 8. Value objects and invariant-encoding types

**Rule:** Model domain values as types that cannot exist in invalid states:
`Money(amount, currency)`, `EmailAddress`, `DateRange(start <= end)`. Parse,
don't validate — convert raw input into rich types once at the boundary, then
trust the types everywhere inside.

**Rule:** Never represent money as a float, identity as a bare string/int passed
through five layers, or a state machine as a string column with stringly-typed
transitions. Encode the state machine: explicit states, explicit allowed
transitions, transition methods on the aggregate.

## 9. Repositories and persistence

**Rule:** One repository per aggregate (not per table). Repositories return
whole aggregates, accept whole aggregates, speak domain language
(`findOverdueInvoices()`, not `query(sql)`).

**Rule:** The database schema serves the aggregate, not the other way around.
ORM convenience (lazy loading across aggregates, shared base entities, bi-
directional mappings spanning contexts) must not redraw your consistency
boundaries. If the ORM fights the aggregate shape, map manually at the adapter.

**Rule:** Use optimistic concurrency (version column) on aggregates by default.
Lost updates are a modeling failure, not a tuning detail.

## 10. Explicit state machines

**Rule:** Any entity with a lifecycle (order, subscription, claim, deployment)
gets an explicit state machine: enumerated states, enumerated transitions,
transition methods that reject invalid moves, and a domain event per transition.

```text
GOOD:
  states: Draft -> Submitted -> Approved -> Fulfilled
                      └-> Rejected (terminal)
  order.approve(approver)   # raises if state != Submitted; emits OrderApproved

BAD:
  order.status = "approved"   # any code can set any string at any time
  if order.status in ("approved", "aproved", "APPROVED"): ...
```

**Rule:** Persist the state machine honestly: a `state` column with a CHECK/enum
constraint, plus a transition history table (who/when/why) for anything audited
or money-touching. Reconstructing "how did it get into this state" from logs is
not a design.

## 11. Domain services, factories, and where logic goes

**Rule:** Logic placement, in priority order: (1) value object, (2) aggregate
method, (3) domain service — only for rules genuinely spanning aggregates
(`PricingPolicy`, `TransferService`), (4) application use case — orchestration
only. Each step down loses cohesion; justify the descent.

**Rule:** Complex aggregate creation goes through a factory (function or class)
that returns only valid instances; "create empty then set fields" construction
makes invalid intermediate states representable and they will escape.

**Rule:** Resist `Helper`, `Manager`, `Util`, `Processor` classes in the domain.
Each is usually an aggregate method or value object that hasn't found its home;
the name is the smell.

## 12. Queries and read models inside the architecture

**Rule:** Don't force reads through aggregates. Queries that cross aggregates
(dashboards, lists, search) bypass the domain model via dedicated read models /
query services that return DTOs — read side may join freely against tables or
projections (lightweight CQRS, see rules/03 §6). Loading 500 aggregates to
render a list is the standard self-inflicted performance bug of strict-DDD
codebases.

**Rule:** Read models never feed writes. A write decision is made by loading the
aggregate (current, invariant-protected state), not by trusting a possibly-stale
projection that a list view rendered.

## 13. Sizing modules and avoiding entity-service decomposition

**Rule:** Cut boundaries around *capabilities and change-reasons*
("Pricing", "Fulfillment", "Risk"), not around nouns ("UserService",
"OrderService", "ProductService"). Noun-services force every real use case to
choreograph three services and own no invariant (rules/07 §13).

**Rule:** A bounded context should be explainable in one sentence naming its
responsibility and its key invariants. If the sentence needs "and", consider
splitting; if two contexts' sentences keep mentioning each other, consider
merging or formalizing the seam (customer/supplier with a contract).

## 14. The testability boundary (humble object)

**Rule:** Every system has a shell that automated tests cannot meaningfully
drive — GUI and rendering, external devices, real clocks and networks, process
spawning, anything that opens a window, needs a display, or hangs without one.
Draw that boundary **explicitly** and keep the shell **thin**: all decisions
move inward to the testable core, and the shell degenerates into a translator
with no branches worth asserting (the "humble object"). This is §4's adapter
rule stated as a testability constraint rather than a dependency one.

**Rule:** No business `if` in the shell. A conditional, loop, or calculation in
a UI callback, device driver wrapper, or CLI entrypoint is logic that has
escaped the core — move it in and leave a call behind.

**Rule:** Make the boundary **machine-readable** — a package/module split the
build understands, not a convention in someone's head. Coverage, mutation, and
complexity tooling then measure the core only. Measuring the untestable shell
distorts every number in both directions and buries the signal (see
`sota-testing` rules/07 §7.2 and rules/06 §6.3).

**Rationale:** this is the precondition for any test metric meaning anything.
"62% coverage" over a codebase where a third is an untestable UI shell is not
a number, it's noise; the same 62% over an explicitly bounded core is a signal
you can act on. Teams that skip this step end up either gaming the metric or
disbelieving it — and disbelieving it is the more expensive outcome.

```text
BAD:  render_invoice_row(inv):          # in the view layer
        if inv.total > credit_limit and not inv.customer.is_exempt:
          badge = "OVER LIMIT"          # a business rule, untestable without a UI

GOOD: core:  invoice.limit_status(customer) -> OverLimit | Ok   # unit-tested
      shell: render_invoice_row(inv) -> badge_for(inv.limit_status(cust))
             # no branch of its own; one smoke test proves it is wired
```

**Rule:** The shell still needs *some* verification — a small number of
end-to-end or smoke tests that prove it is wired up (`sota-testing` rules/05),
not unit metrics. And treat shell growth as an **architecture** finding: if the
untestable region keeps expanding, logic is leaking outward, and no amount of
test discipline will reach it.

## Audit checklist

- Can the team produce a context map? Are seam relationship types (ACL, conformist, published language) explicit?
- Does any domain term ("customer", "order", "account") have different meanings sharing one class/table across contexts?
- Are aggregates small, referenced by ID, and modified one-per-transaction? Search for transactions touching multiple aggregates.
- Are business invariants enforced inside aggregate methods, or scattered across service classes (anemic model)?
- Does domain code import frameworks, ORM types, vendor SDKs, or transport types (HTTP requests, Kafka records)?
- Are ports defined by consumer need, or do they mirror vendor APIs one-to-one?
- Is the dependency rule (adapters → application → domain) enforced by an automated architecture test?
- Do external/legacy models cross into the domain without an anti-corruption layer?
- Are cross-context events versioned, past-tense, schema-validated public contracts?
- Is money a float anywhere? Are state machines stringly-typed with unguarded transitions?
- Is modeling rigor proportional: full DDD on core domains, simple transaction scripts on CRUD subdomains — or uniform ceremony/uniform mud?
- Do repositories use optimistic concurrency, or can concurrent writers silently lose updates?
- Are entity lifecycles explicit state machines with guarded transitions and history, or free-form status strings?
- Do `Helper`/`Manager`/`Util` classes in the domain hold logic that belongs on aggregates or value objects?
- Do list/dashboard reads go through dedicated read models, or do they load aggregates in bulk?
- Do any write decisions consume read-model/projection data instead of loading the aggregate?
- Are services/modules named after capabilities or after entities (noun-services)?
- Is the boundary between the testable core and the environment-bound shell (GUI, device, IO, process spawn) explicit in the build, or only in convention? Does business branching live in that shell?
- Does the shell keep growing release over release (logic leaking outward), and do coverage/mutation/complexity tools measure the core or the whole tree?
