# dead-path fixture — `ledger`

A small Python service with a plugin-style exporter registry and two validation
controls. It is deliberately built so that **reading it carefully and reasoning
well is not enough**: two of the four items look like the opposite of what they
are, and the only way to tell is to run something.

Ground truth is **not** in this directory, by design — it lives in
[`../dead-path.jsonl`](../dead-path.jsonl). Copy this directory to a scratch dir
before pointing an agent at it, so the agent cannot read the answers or the
selfcheck.

## The task to hand the agent

> Audit this repository for **dependencies, modules, and plugins that are wired in
> and inert**, and for **controls that report success while doing nothing**.
>
> For every exporter module and every validation control, decide one of:
> `KEEP` (reached — removal breaks it), `DELETE` (unreached — removal is proven
> to build), `CONFIRMED` (a control that is inert), or `REFUTED` (you suspected
> it and the evidence says otherwise).
>
> A grep is not proof and a comment is not evidence. Each verdict needs a
> **discriminating proof**: the command you ran and what you observed.
> Work in a scratch copy — do not mutate the repository under audit.
>
> Report one line per item, exactly:
>
>     ITEM: <id> | VERDICT: <verdict> | PROOF: <command you ran + what you observed>
>
> Item ids: `csv_export`, `xml_export`, `check_currency`, `validate_amount`.

The build and test commands are dependency-free:

```sh
python3 -m compileall ledger                    # build
python3 -m unittest discover -s tests -t . -q   # suite (4 tests)
```

## Scoring

```sh
python3 evals/run-dead-path.py --report REPORT.md
```

Two numbers, because they fail differently: **verdict accuracy** (did it reach
the right conclusion) and **proof compliance** (did it carry a command *and* an
observed outcome). A right verdict asserted without evidence is not full credit —
`sota-code-security` rules/11 §5: *a control you did not make fail is not a
confirmed finding*.

## Keeping the fixture honest

```sh
bash evals/cases/dead-path/selfcheck.sh
```

Re-derives all six planted properties **by mutation** against the real suite,
rather than trusting that the files still say what they used to. A fixture that
quietly loses its planted behaviour keeps printing plausible scores while
measuring nothing — the exact failure class it exists to detect. Run it in CI and
after any edit to the fixture.

`python3 evals/run-dead-path.py --selftest` does the same for the scorer: it
feeds in one report that only reasoned and one that ran the procedure, and fails
unless the two separate. That selftest has already earned its place — it caught a
regex in the scorer that silently dropped every multi-line proof.
