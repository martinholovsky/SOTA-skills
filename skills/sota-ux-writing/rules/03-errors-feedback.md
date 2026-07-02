# 03 — Errors, Warnings & Feedback

Error copy is the highest-stakes writing in the product: the user is blocked,
stressed, and deciding whether to retry, rage-quit, or file a ticket. Every
error message is a tiny support agent — or a tiny liability.

## 1. The error contract: what happened → why → what now

Every user-facing error answers, in order, as much of this as is truthfully
known:

1. **What happened** — specific, in task terms: "Payment failed",
   "Couldn't upload sketch.png".
2. **Why** (when known and safe to say): "your card was declined",
   "the file is larger than 25 MB".
3. **What to do next** — an action, ideally a button: "Try another card",
   "Compress it or upgrade for 1 GB uploads".
4. **State the side effects**: after a failed payment, "No charge was made"
   is the sentence the user is actually looking for.

```text
BAD:  Error 4002: Transaction could not be processed.
GOOD: Payment failed — your card was declined by the bank. No charge was
      made. Try another card, or contact your bank and retry.
```

- A message that can't offer a next step isn't done: "Retry", "Contact
  support with code 4002", or "We're on it — check status.example.com" are
  all next steps. Dead ends are findings, always.
- Error **codes are for support, in fine print** — never the headline. Keep
  them (they make tickets resolvable); demote them.
- Never say "try again later" when retrying cannot help (validation errors,
  permissions) — it's a lie that costs the user a second failure.

## 2. Framing: the system takes the blame

- The product failed the user, not the reverse: "We couldn't save your
  changes", never "You entered invalid data". Grammatical subject = system.
- Banned framing: "Invalid input", "Bad request", "Illegal characters",
  "You failed to…", "Forbidden" as user-facing text — these are protocol
  vocabulary leaking into human space.
- No alarm styling in prose: no ALL CAPS, no exclamation marks, no red walls
  of text. The visual layer already signals severity.
- Humor: **never in errors.** "Oops!"/"Whoops!" atop lost work reads as
  mockery; the calmer the copy, the more competent the product feels
  (tone matrix: `rules/01` §5).
- Apologize once, when the product genuinely failed ("Sorry — this is on
  us"), not reflexively on every validation message.

## 3. Validation messages: state the rule, not the verdict

- The message teaches the constraint: "Use 8+ characters with at least one
  number", not "Password too weak" / "Invalid password".
- Include the offending value when it helps: "Card number must be 16 digits —
  you entered 15."
- Requirements the user could have known belong in hint text *before* the
  error (`rules/02` §2); validation copy is the fallback, not the reveal.
- Match the field's language: the error under "Work email" says "work email",
  not "identifier".
- Timing/mechanics (blur vs keystroke, focus management, `aria-describedby`)
  are `sota-frontend-design` rules/04 §3 — copy and mechanics fail together.

## 4. Security-sensitive errors: precise inside, vague outside

Copy here is a security control — coordinate with `sota-code-security`
rules/02 (authn) and rules/07 (data exposure):

- **Login failures never confirm account existence**: "Wrong email or
  password", never "No account with that email" (user-enumeration). The same
  applies to password-reset flows ("If that address has an account, we've
  emailed a link").
- Rate-limit and lockout messages state the fact and the wait, not the
  detection logic: "Too many attempts — try again in 15 minutes."
- **No internals ever reach the user**: stack traces, SQL fragments, file
  paths, hostnames, dependency names, "NullPointerException". The user-facing
  string and the logged diagnostic are two different strings by design.
- Permission denials name the *rule*, not the resource's existence when the
  user shouldn't know it exists: prefer 404-equivalent copy for unauthorized
  IDs (IDOR hygiene).
- Session expiry: say why re-auth is needed and preserve their work — copy
  and mechanics together ("Your session expired. Sign in again — your draft
  is saved.").

## 5. Warnings vs errors vs info: spend alarm carefully

- **Error** = the task failed or will fail. **Warning** = it will proceed
  but with a consequence worth weighing. **Info** = context, no decision.
  Escalating info to warning (or warning to error) to "make sure they read
  it" trains users to dismiss all three — alarm fatigue is a copy bug
  (`sota-detection-engineering` has the ops version of this law).
- A warning states the consequence and the choice: "This plan change takes
  effect immediately and is prorated. Continue?"
- Persistent warnings the user can't act on ("Your browser may be
  unsupported") are banned — either gate, fix, or stay silent.

## 6. Success & completion feedback

- Confirm the **object and the effect**, not the click: "Invoice #1042 sent
  to billing@acme.com", not "Success!".
- Include the reversal path in the same breath when one exists: "Archived —
  Undo" (undo-over-confirm pattern: frontend rules/04 §6).
- Report partial success honestly: "Imported 200 of 203 rows — 3 failed
  (download report)". Rounding partial failure up to "Done!" is a trust
  bug that surfaces as "the product loses data".
- Skip ceremony for micro-actions: a toggle that visibly flips needs no
  toast; feedback is proportional to consequence.

## 7. Asking for things: permissions, upsells, reviews

- Permission prompts (notifications, location, contacts) state the **user's
  benefit and the trigger**, and ask in context — "Get an alert when your
  build finishes" beside the build button, never a cold launch-time battery
  of dialogs (platform specifics: `sota-mobile` rules/03).
- Upgrade/paywall moments: name what the user just hit ("You've used all 3
  free projects"), what the paid tier changes, and keep the decline path
  neutral — **"Not now" / "No thanks", never confirmshaming** ("No thanks, I
  like losing data"). Confirmshaming is a dark pattern (regulatory context:
  `sota-copywriting` rules/04 §4) and a Critical finding here.
- Never gate the *decline* behind lower contrast, tiny type, or a delay —
  visual-hierarchy manipulation of consent is the same dark pattern in CSS.
- Review/feedback prompts: after a success moment, once, with a real
  dismiss-forever option.

## Audit checklist

- [ ] Every user-facing error has all applicable parts: what happened, why
      (if known), next step, side effects; zero dead ends
- [ ] Generic-error ban: `grep -riE '"(An error (has )?occurred|Something went
      wrong)"' src/ locales/` — each hit either enriched or justified
- [ ] System-blame framing: `grep -riE '"(Invalid|Illegal|Bad|Forbidden)[^"]*"'
      locales/` — no protocol vocabulary or user-blame in UI strings
- [ ] No humor/exclamations in errors:
      `grep -riE '"[^"]*(Oops|Whoops|!)[^"]*"' locales/` reviewed
- [ ] Validation messages state the rule and (where helpful) the offending
      value; constraints also appear as hints before first failure
- [ ] Login/reset/lockout copy confirms no account existence; user-facing
      error strings contain no stack traces, paths, hostnames, or exception
      names (pair with `sota-code-security` rules/07 greps)
- [ ] "Try again later" appears only where retry can actually succeed
- [ ] Severity honest: no info styled/worded as warning, no warning as error;
      no unactionable persistent warnings
- [ ] Success messages name object + effect; partial failures reported with
      counts and a path to the details
- [ ] Permission/upsell prompts state user benefit in context; decline
      options are neutral ("Not now") — grep for confirmshaming patterns:
      `grep -riE '"No thanks, I' locales/ src/`
