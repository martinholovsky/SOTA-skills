# 19 — Anti-Automation & Abuse of Value-Granting Features

Scope: automated abuse that is not a volumetric DoS and not an injection — fake signups,
multi-accounting, credential-stuffing responses, self-hosted and hosted challenges
(CAPTCHA, proof-of-work), and business flows that hand out value (coupons, referrals,
trials, scarce inventory, card payments). Added 2026-09-25. Maps to the OWASP Automated
Threats catalogue (OAT) and CWE-799 (improper control of interaction frequency) with its
child CWE-837 (improper enforcement of a single, unique action).

Core principle: **you are not trying to stop every bot, you are trying to make abuse cost
more than it earns — and every value-granting action needs its own ceiling, because the
login rate limit does not protect the coupon endpoint.** Login throttling and lockout stay
in rules/02 §1; one-time-operation replay and workflow state stay in rules/03; atomic
check-then-act (double redemption) stays in rules/06; the detection counters that feed
these decisions stay in rules/07 §2.1.

## 1. Graduated responses to automation

A hard block on the first signal tells the operator of the bot exactly which request
tripped it, so they change one thing and try again. Scale the response to how sure you are:

| Confidence the client is abusive | Response |
|---|---|
| Weak signal | Record it, serve normally, mark the session for scoring |
| Moderate | Step up: a challenge (§3), MFA, or a proof-of-work puzzle |
| Strong | Tarpit: delay the response by a growing, jittered amount rather than refusing it; or serve cached, stale or deliberately imprecise data to a scraper |
| Very strong | Soft-block the valuable action only (checkout, redemption, posting) while leaving browsing alone |
| Confirmed | Hold the account for manual review; keep it rather than deleting it, because the record is the evidence |

- **Write the ladder down**, with the signal that moves a client from one rung to the next,
  and log every decision with its score and rule name. A rule nobody can see cannot be
  tuned, and an unlogged block cannot be appealed.
- **Tarpit instead of 403.** A delay that grows with confidence and carries random jitter
  collapses a bot's throughput without telling it that it was detected. Bound the delay
  server-side (async sleep, not a held worker thread) so the tarpit does not become your
  own resource exhaustion (rules/06).
- **Degrade the login path under attack.** The Credential Stuffing Prevention guidance
  lists slowing measures that need no user tracking: rising JavaScript work, a
  proof-of-work puzzle, long waits, oversized responses, randomised error text. Each raises
  the attacker's cost per attempt; judge each against its effect on real users.
- **Honeypot fields.** An extra input a human never sees (moved off-screen, not merely
  `type="hidden"`, which bots skip) that the server rejects when filled. Give it
  `aria-hidden="true"` on its container, `tabindex="-1"` and `autocomplete="off"`, and a
  label telling assistive-technology users to leave it empty — otherwise screen-reader and
  keyboard users, and browser autofill, can fill it and be rejected. Treat a filled
  honeypot as a strong signal that routes to the tarpit, not as proof.
- **Accessibility and privacy limits.** Blocking clients that do not run JavaScript, or
  whose browser is privacy-hardened, blocks some disabled users and privacy-conscious
  users; prefer challenge over block for those signals. Fingerprinting signals are personal
  data: minimise, hash or truncate, and keep them for days, not indefinitely
  (`sota-privacy-compliance`).
- **Unblock automatically.** IP-level mitigations expire and are lifted as abuse stops;
  addresses are reassigned and shared (carrier NAT, corporate egress).

OWASP: Bot Management and Anti-Automation cheat sheet; Credential Stuffing Prevention
cheat sheet.

## 2. Signup abuse and multi-accounting

- **Disposable email domains: risk, not a wall.** Any list of throwaway-mail domains is
  incomplete on the day it is published; new domains appear daily. If you use one, pull a
  maintained list on a schedule (a vendored file nobody refreshes decays silently), use a
  hit to raise the account's risk score or delay value-granting actions, and if you do
  refuse the address, tell the user why. If refusing throwaway mail is a hard requirement,
  the only complete form is an allowlist of accepted providers — and a large public
  provider on that list still hands out free addresses.
- **Do not strip `+tag` sub-addressing as an anti-multi-account control.** It is trivially
  bypassed (a second free mailbox, a throwaway domain, dots or aliases at some providers),
  it breaks the user's legitimate way of tracing who leaked their address, and it can
  change which mailbox receives a reset link if applied inconsistently. Store the address
  as entered; if you need a duplicate signal, compute a normalised form in a separate
  column used only for scoring, never for delivery or login.
- **Suspicious-address signals.** A random-looking, high-entropy local part at a domain
  that was registered recently is a common shape of scripted signups; feed it to the risk
  score rather than rejecting on it alone.
- **Velocity on more than one key.** Limit signups per IP, per network (ASN), and per
  device or client fingerprint, each with its own window — residential proxy pools defeat
  an IP-only limit, and an unexpected datacenter ASN on a consumer signup is itself a
  signal. Keep the buckets independent; one bucket keyed on the combination of all of
  them resets whenever any part changes.
- **Phone verification.** Look up the line type: virtual (VoIP) numbers are cheap in
  bulk, so a VoIP number earns more friction or no value-granting eligibility rather than
  automatic rejection (some real users only have one). SMS sending limits and SMS pumping
  are in rules/02 §7 and rules/06.
- **Identity beyond the email address.** Trials, referral rewards and one-per-customer
  offers keyed on email alone reset with a new mailbox. Tie eligibility to stronger signals:
  a verified phone, a payment-method fingerprint, a device signal, KYC where the value
  justifies it.
- **Friction proportional to value.** A free action (reading, browsing) gets none; an
  action that grants credit, a reward or scarce stock gets a challenge, a short delay or a
  verified-account requirement. The honest user pays that cost once; a script pays it on
  every request.

OWASP: Bot Management and Anti-Automation cheat sheet; Email Validation and Verification
cheat sheet; Input Validation cheat sheet; Business Logic Security cheat sheet.

## 3. Challenges: CAPTCHA and proof-of-work

A visible CAPTCHA is a last-resort step-up, not a primary control: solving services and
models defeat it cheaply, and it is an accessibility barrier (WCAG 2.2 SC 3.3.8 —
`sota-frontend-design` rules/05). Offer a non-visual alternative wherever one is shown.

- **Hosted challenge: the token means nothing until your server verifies it.** The widget
  posts a token (`g-recaptcha-response`, `h-captcha-response`, `cf-turnstile-response`);
  the backend must send it with the secret key to the provider's siteverify endpoint and
  proceed only on `success: true`. Check `hostname` and, where you set one, `action` in the
  response. Tokens are short-lived and single-use per the providers' documentation
  (reCAPTCHA: two minutes; hCaptcha: 120 seconds by default; Turnstile: 300 seconds), so a
  verification call that is skipped, cached or made fail-open on a provider error is a
  no-op control (rules/10). Decide the outage behaviour explicitly.
- **Self-hosted challenge: the answer never leaves the server.** Keep the expected answer
  in server-side state, or send only a token that carries an HMAC (keyed with a server
  secret) over the challenge ID, the answer and an expiry — never the answer, or an
  unkeyed hash of it, in a hidden field, cookie or JSON body.
- **One attempt per challenge.** Delete or mark the challenge used on the *first*
  submission, right or wrong, and issue a fresh one after a failure. A challenge that
  accepts several guesses, or that can be replayed after a correct solve, is guessable at
  the odds of its answer space (a pick-one-of-four image puzzle is a 25% free pass).
- **Pool size.** A fixed pool of images or questions is eventually harvested into an
  answer table; generate challenges, or rotate a pool large enough that harvesting costs
  more than it earns.
- **Proof-of-work construction.**
  - The challenge is at least 128 bits from a CSPRNG, issued by the server and recorded
    (or HMAC-bound, as above) together with its difficulty and a short expiry — tens of
    seconds to a few minutes.
  - **The server sets the difficulty**, never the client. Tune it so a typical real
    client spends on the order of a few hundred milliseconds, and raise it for a client or
    route under attack (§1). A difficulty field read back from the request lets the client
    pick zero.
  - Verification is server-side: recompute the hash, check the difficulty *that was
    issued*, reject an expired challenge, and consume it so one solution buys one request.
  - PoW prices requests; it does not identify anyone. Attackers with cheap compute pay
    it easily, so pair it with the per-key limits in §2, and budget the cost for
    low-end phones.

OWASP: Code Review Guide v2 (CAPTCHA); Bot Management and Anti-Automation cheat sheet.

## 4. Commerce and incentive abuse

- **No stacking by default.** Each coupon, promotion or credit declares whether it
  combines with others, and the default is exclusive. Apply combinations in a defined
  order on the server, and clamp the result to a price floor (cost, a minimum margin, or
  at least zero plus any non-discountable fees) so no combination can make an order
  free or negative. Compute discounts from codes server-side; never accept a discount
  amount or total from the client (rules/03).
- **Caps at every layer.** A per-action cap (one use per order), a per-account lifetime
  cap (total promotional value), and a per-source cap (per payment method, per device, per
  shipping address) — each layer catches what multi-accounting slips past the one above.
  Enforce each atomically (rules/06, conditional update or unique constraint).
- **Scarce inventory.** A reservation made by adding to a cart expires if unpaid within
  a set time and the stock is released, or bots camp the whole allocation (denial of
  inventory). Pair it with server-side per-account purchase limits that also count
  identity proxies (the same card, address or device), and for limited drops a waiting
  room with random admission (`sota-architecture` rules/04 §6).
- **De-duplicate orders by normalised identity.** Hash a normalised shipping address
  (case, whitespace, abbreviations, postcode) and a payment fingerprint (card BIN plus last
  four plus a holder hash, or the gateway's fingerprint) and count orders per value; one
  person with ten accounts shares these where the accounts do not.
- **Card testing (carding).** Bursts of small authorisations, many distinct cards from one
  session or device, and high decline ratios are the signature. Score payment attempts for
  risk before calling the gateway, rate-limit authorisation attempts per session, device
  and account, use the gateway's step-up cardholder authentication (for example 3-D
  Secure) where risk is elevated, and alert on the decline ratio (rules/07 §2.1).
- **Referrals: two people, not two accounts.** Before paying a referral reward, check the
  referrer and referee differ on the signals of §2 (payment method, device, verified
  phone, address), and pay only after the referee does something that costs them (a paid,
  unrefunded order), not on signup. Log every reward with both parties and the source.
- **Trials.** Tie free-trial eligibility to something more stable than an email address
  (§2), or a cancel-and-resignup loop keeps the free tier forever.

OWASP: Business Logic Security cheat sheet; Bot Management and Anti-Automation cheat
sheet; Third Party Payment Gateway Integration cheat sheet.

## Audit checklist

Probes print a lead list; read each hit before reporting it.

- [ ] **Graduated response (§1)** — MEDIUM. Is there a written ladder from log to challenge
      to tarpit to soft-block to hold, with each decision logged? Detections that answer
      with an immediate hard refusal:
      `grep -rnE -i '(bot|abuse|risk)_?(score|detected|suspect|flag)[^;]*(403|forbidden|abort|deny|block)' .`
- [ ] **Honeypot fields accessible (§1)** — LOW. Files that mention a honeypot field but
      never set `tabindex="-1"` on it:
      `grep -rliE 'honeypot|leave (this|it) (field )?(empty|blank)' . | while IFS= read -r f; do grep -q 'tabindex="-1"' "$f" || echo "$f"; done`
- [ ] **Plus-addressing not stripped as an anti-abuse control (§2)** — LOW. Code that
      cuts the `+tag` out of an email local part:
      `grep -rnE "split\(['\"][+]['\"]\)|[\\][+][^'\"]*@|indexOf\(['\"][+]['\"]\)" .`
- [ ] **Disposable-domain list refreshed and used as a signal (§2)** — LOW. Is any
      throwaway-domain list pulled on a schedule, and does a hit raise risk rather than
      silently reject? Where it lives: `grep -rniE 'disposable|throwaway|burner' .`
- [ ] **Signup velocity keyed beyond IP (§2)** — MEDIUM. Signup files that rate-limit
      but never mention an ASN, device or fingerprint key:
      `grep -rliE 'signup|sign_up|register' . | while IFS= read -r f; do grep -qiE 'rate.?limit|limiter|throttle' "$f" && ! grep -qiE 'asn|device|fingerprint' "$f" && echo "$f"; done`
- [ ] **Hosted CAPTCHA verified server-side (§3)** — HIGH. Files that read a challenge
      token but never call siteverify:
      `grep -rliE 'g-recaptcha-response|h-captcha-response|cf-turnstile-response' . | while IFS= read -r f; do grep -q 'siteverify' "$f" || echo "$f"; done`
      (a verifier in another file clears the hit — follow the call).
- [ ] **Self-hosted CAPTCHA answer server-side and single-attempt (§3)** — HIGH. The
      answer placed where the client can read it:
      `grep -rnE -i '(hidden|cookie|json)[^;]*captcha_?(answer|solution|text|code)|captcha_?(answer|solution|text|code)[^;]*(hidden|cookie|json|value=)' .`
      Then read the verify path: is the challenge consumed on the first submission, right
      or wrong?
- [ ] **Proof-of-work difficulty and challenge set by the server (§3)** — MEDIUM.
      Difficulty read from the request, or a challenge from a non-CSPRNG:
      `grep -rnE -i '(difficulty|pow_?bits|leading_?zeros)[^;]*(req|request|body|params|query|form)[.[]|(challenge|nonce)[^;]*(Math[.]random|random[.]randint|rand[(])' .`
      Also confirm verification rejects expired and already-used challenges.
- [ ] **Promotions exclusive by default and clamped (§4)** — HIGH where a combination can
      reach zero or below. Files that loop over several discounts with no floor or
      stacking flag in sight:
      `grep -rliE 'for[^:{]*(coupon|promo|discount|voucher)s' . | while IFS= read -r f; do grep -qiE 'stackable|combinable|exclusive|floor|min_?price|max\(0|Math[.]max' "$f" || echo "$f"; done`
- [ ] **Layered value caps (§4)** — MEDIUM. Is there a per-action, a per-account lifetime
      and a per-payment-method or per-device cap on each value-granting action, each
      enforced atomically? (Design question; read the redemption path.)
- [ ] **Inventory holds expire and purchase limits count identity proxies (§4)** — MEDIUM.
      Reservation code with no expiry in sight:
      `grep -rliE 'reserv(e|ation)|cart_?hold|hold_?stock' . | while IFS= read -r f; do grep -qiE 'expir|ttl|timeout|release' "$f" || echo "$f"; done`
- [ ] **Card-testing defences (§4)** — HIGH for a public checkout. Risk scoring before
      authorisation, per-session and per-device attempt limits, step-up authentication
      on elevated risk, and a decline-ratio alert.
- [ ] **Referral rewards check two people, not two accounts (§4)** — MEDIUM. A
      self-referral check that compares only account IDs:
      `grep -rnE -i '(referrer|inviter)_?(id)?[[:space:]]*(!=|!==|==|===)[[:space:]]*(referee|invitee|new_?user|user)_?(id)?' .`
