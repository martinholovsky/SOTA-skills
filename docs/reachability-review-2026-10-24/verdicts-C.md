# Refuter verdicts, batch C (15 Medium/Low findings)

Tree: `<repo>` at `f2cd26f9`, read-only. Every cite below was opened in full-section context this session.

### F15 — Go 05 §1: the UTF-8 validation rule's probe lives in 04, which 05 never points to
- **verdict:** CONFIRMED (Low)
- **evidence:** `skills/sota-golang/rules/05-security.md:13-15` states the rule with no pointer. The JSON bullet in the same section ends with "probe in `rules/04` (`04-http-services.md`) checklist" (05:36). `git grep -n -i 'utf8\|utf-8\|ValidString' skills/sota-golang/` returns only 04:375-378 (the probe) and 05:14 (the rule). Nothing in the 05 checklist covers it. Go SKILL.md AUDIT says "Work through each relevant rules file's audit checklist", and the 04 index row is scoped to "HTTP servers/clients", so a non-HTTP consumer has no reason to open 04. The probe's grep (`io\.ReadAll`, `string(body)`) is not HTTP-specific, which supports the finding.
- **if confirmed, minimal fix:** append "probe in `rules/04` (`04-http-services.md`) checklist" to the 05:14-15 bullet.

### F15 — Network AUDIT probes an "intended exposure list" that no BUILD rule tells builders to keep
- **verdict:** REFUTED
- **evidence:** The probe flags "any listening service not on the intended exposure list". BUILD rules do define intended exposure. `skills/sota-network-security/rules/05-edge-ingress-egress.md:34`: "**R2 — Minimal exposure and version hygiene at the edge.** Expose only 443 (and 80→443 redirect)". `rules/02-segmentation-blast-radius.md:38` (R3 zone table): "Edge/DMZ … Internet (north-south, 80/443 only)". R8 (02:113) says "Default-deny". Under these rules a team has a defined intended exposure. The probe would mark it down only for services those rules forbid, which is not the S2 shape ("an auditor would mark down a team that followed the library"). The reviewer's grep (`intended exposure|exposure list|external exposure`) searched for the noun phrase, not the obligation. The "repeat on a schedule" clause is about how the audit is run, not something a builder is asked to do.
- **if confirmed, minimal fix:** n/a. Optionally add "(intended = R3 / rules/05 R2)" to the probe.

### F4 — Mass assignment is stated in the JS and .NET files with no probe and no pointer to its owner
- **verdict:** DOWNGRADED. The JS half is refuted, the .NET half survives at Low.
- **evidence:** JS has a probe the reviewer did not list. `skills/sota-javascript-typescript/rules/01-typescript-config-and-types.md:260`: "`grep -rn "JSON.parse\|req.body\|req.query\|process.env" src/` — confirm each flows through a schema parse before typed use". `Model.update(req.body)` is an unparsed `req.body`, so this hit flags it. JS 04:114 also requires that "every route parses body/query/params with a schema". For .NET, `rules/04-security.md:216-217` has no probe, and `git grep -n -i -E 'over-?post|\[Bind\]|rules/07-data-exposure' skills/sota-dotnet` returns only the rule line. Two things lower the severity. The owner probe exists (`sota-code-security/rules/07-data-exposure.md:434`), and router cross-cutting rule 1 (`skills/sota/SKILL.md:234-235`, "Auditing a Go API server → sota-golang + sota-api-design + sota-code-security") stacks code-security on any language audit of a service.
- **if confirmed, minimal fix:** append "(probe: `sota-code-security` rules/07 (`../../sota-code-security/rules/07-data-exposure.md`) §3)" to the .NET 04:216-217 bullet.

### F11 — Wrong-section cite: on-device model signing points to mobile §4.9 (reverse engineering)
- **verdict:** REFUTED (ambiguous, so the default applies)
- **evidence:** The cite in `skills/sota-ml-engineering/rules/07-security-governance.md:127-128` reads "§4.9 **and its downloaded-content rule**". It names two targets, and the second one, described rather than numbered, is `sota-mobile/rules/04-security.md:198` §4.12 ("Downloaded config and content (… ML models) are checked for integrity", :204-ish). The ML bullet also covers encrypting weights on device, and §4.9 ("design like the binary is open source", :167) is a defensible target for that extraction concern. So the cite does reach the integrity rule, and §4.9 is not clearly wrong.
- **if confirmed, minimal fix:** "§4.9 and §4.12" (makes the second target explicit).

### F-S1-7 — cli-ux: three small BUILD rules with no checklist line
- **verdict:** CONFIRMED (Low)
- **evidence:** `git grep -n -i -E '\- \[ \].*(no args|no-args|--version|version|pager|PAGER|page)' skills/sota-cli-ux/` returns 01:216 ("`PAGER` … respected", which does not say never page when piped), 03:227 (no network on `--version`, which says nothing about its content), and 04:97/98/101 (pinning and install). None of these checks: no-args exits nonzero (01:180-183), release or source builds reporting a real version (04:22-24), or no paging when piped (02:94-96). The version rule hedges "if avoidable" only for source builds. "embed version + commit at build time" has no hedge.
- **if confirmed, minimal fix:** as proposed. Add one clause each to the 01 help item, a 04 item, and the 02 TTY/colour item.

### F3 — Python rules/05 §2 and §8 injection rules have no probe in the file and no pointer to the owner that has one
- **verdict:** CONFIRMED (Medium)
- **evidence:** The rules/05 checklist Subprocess item greps `shell=True`, `os.system|os.popen`, `RLIMIT_AS` and `check=True`, and has no `--` check. The checklist has no CRLF/header item. The only logging probes are in rules/03 (03 checklist: f-strings in logs, secrets reaching logs), and neither looks for control characters. `git grep -n 'sota-code-security' skills/sota-python/rules/05-security.md` returns pointers at :206, :217, :238 (SSRF), :278, :386 and :464, and none in §2 (:63-64) or §8 (:311-325). Router cross-cutting rule 1 and the router's "builds an email or a message header → cs rules/01" row (`skills/sota/SKILL.md:219`) partly mitigate this, so it stays at Medium rather than rising to High.
- **if confirmed, minimal fix:** append "(probe: `sota-code-security` rules/01 (`../../sota-code-security/rules/01-input-injection.md`) §3 / §11)" to the `--` bullet (:63) and the CRLF bullet (:323).

### F4 — Auto-retrain must pass the gate and progressive rollout: no probe
- **verdict:** CONFIRMED (Medium)
- **evidence:** The 06 checklist retraining item checks only `retrain|schedule|cron|airflow|trigger|cadence`, meaning a trigger exists. The 04 gate item checks only that a `threshold|gate|promote…` string exists somewhere in CI YAML. The 05 items check that registry/rollback and canary/shadow strings exist somewhere in the repo. `git grep -n -i retrain skills/sota-ml-engineering/rules/` outside 06 finds no probe that ties the retrain path to the gate. Every item can pass while the retrain job writes straight to serving.
- **if confirmed, minimal fix:** add a manual step to the 06 retraining item: "for each trigger, trace the job to promotion; does it call the 04 §4 gate and the 05 rollout?"

### F17 — The compliance SKILL cites named sections that do not exist
- **verdict:** CONFIRMED (Low). The proposed fix for :87 is wrong.
- **evidence:** `grep -n '^## ' rules/01-*.md rules/02-*.md` shows rules/01 §1-§6 (spine, crosswalk, inheritance, "**4. Encode controls as gates, not prose**", baselines, continuous) and rules/02 §1-§5. No section is named "evidence" or "scope". However, SKILL.md:85 is literally "**Encode controls as gates, not prose**", which is rules/01 **§4** (:88). The reviewer's "§2, §6" is the wrong replacement. For :105 the boundary content is rules/02 §2 (:66 "Define and isolate the CUI boundary") and §5 (:142 "Authorization boundary"), so "§2, §5" is right.
- **if confirmed, minimal fix:** SKILL.md:87 `§evidence` → `§4`. SKILL.md:105 `§scope` → `§2, §5`.

### F4 — Data engineering: AUDIT loads 04 only when "quality tooling" exists, so the missing-quality-checks probes never run where checks are missing
- **verdict:** REFUTED
- **evidence:** The trigger, `skills/sota-data-engineering/SKILL.md:65` "Load the rules files matching what exists (no Kafka → skip 03)", names only 03 as skippable. It matches files to what exists, and models and pipelines, the subject of 04's probes, always exist in a pipeline repo. "Quality tooling" is an inventory line, not a load condition. The same SKILL's severity list (:80) names "missing quality checks" as MEDIUM, which tells the auditor this is an absence check. 04 is also reached from 02, which every pipeline audit loads. 02:104 points to rules/04 for "control totals" (the HIGH probe the reviewer says is lost), and 02:186 says "Severity-tier them ([rules/04]…)". 06:44 does the same with "run the block-tier quality battery ([rules/04])".
- **if confirmed, minimal fix:** n/a. Optionally write "always load 02 and 04" in AUDIT step 2.

### F10 — JS auth rate limiting has no presence probe
- **verdict:** CONFIRMED (Medium)
- **evidence:** `git grep -n -i -E 'rate.?limit|brute' skills/sota-javascript-typescript/` returns only 03:23 (unrelated), 04:111 and 04:113. The only checklist item is 04:415, the `trust proxy` keying item, which presumes a limiter exists. JS 04 has no pointer to `sota-api-design` rules/07 (`git grep -n 'sota-api-design' skills/sota-javascript-typescript/rules/04-node-backend.md` returns nothing). The owner probe exists at `sota-api-design/rules/07-security-operations.md:407` ("unauth endpoints (login/token) IP-limited"), and the router's "adds a request handler or endpoint" row (`skills/sota/SKILL.md:230`) reaches it in BUILD. That is why this is Medium and not High, but under the S1 definition the gap is real.
- **if confirmed, minimal fix:** append "(probe: `sota-api-design` rules/07 (`../../sota-api-design/rules/07-security-operations.md`) §2)" to 04:113, or add the auth-route/limiter grep.

### F9 — Revocation must reach already-released secrets: no direct probe
- **verdict:** CONFIRMED (Medium)
- **evidence:** In the `skills/sota-confidential-computing/rules/03-remote-attestation.md` checklist, the closest items are "TCB status handled as graded policy (each grade → release/alert/deny with deadlines)", "Written TCB-recovery runbook … dual-validity reference-value rotation" and "secret releases leased rather than perpetual". None asks whether keys already released are rotated. The graded-policy item covers the `Revoked` row of the R3.4 table only indirectly, because that row (:161) carries "revoke previously released keys". The retired-measurement half of R7.3 (:286-289) has no probe at all. `git grep -n -i -E 'R7\.3|previously released|already.released'` returns only :161 and :286-288.
- **if confirmed, minimal fix:** add the proposed checklist item that cites R7.3.

### F7 — The prompt-injection classifier's per-language eval rule is unreachable from where the LLM skill sends injection work
- **verdict:** DOWNGRADED (Medium → Low)
- **evidence:** The missing back-pointer is real. `git grep -n 'sota-llm-engineering' skills/sota-code-security/` shows that cs rules/08 points only to llm rules/04 (:135), and cs08:66-75 (the classifier bullet) has no per-language guidance. Calling it unreachable overstates it. Router cross-cutting rule 8 (`skills/sota/SKILL.md:255-256`) reads "LLM features split three ways. Quality/architecture → sota-llm-engineering; security → cs rules/08". Building and evaluating a classifier is a quality/eval task, and the llm SKILL.md index row for rules/01 reads "...building ANY LLM feature (start here)". So the router reaches llm 01 by another path, and the gap is a hygiene back-pointer.
- **if confirmed, minimal fix:** add to cs08:66-75 "evaluate it per language: `sota-llm-engineering` rules/01 (`../../sota-llm-engineering/rules/01-evals.md`) §1".

### F10 — Ruby 02 §3: `JSON.load` and CSV formula injection have no probe
- **verdict:** CONFIRMED (Medium)
- **evidence:** The only JSON/CSV hit in the `skills/sota-ruby/rules/02-security.md` checklist is `grep -rn "create_additions" --include='*.rb' .`. `git grep -n -i -E 'JSON\.load|csv' skills/sota-ruby/` returns only the rule lines 02:106 and 02:125-126, plus an unrelated python one-liner in 04:307. A bare `JSON.load(params[:x])` has no `create_additions` token, so the grep misses the call the rule names. CSV emission has no probe at all.
- **if confirmed, minimal fix:** add `JSON\.load` to the deserialization grep, and add a CSV-emission item that asks for the leading-`'` guard.

### F13 — rules/16 §2.16 checklist item describes a different defect than its section
- **verdict:** CONFIRMED (Low), reclassified S3 → S2. The `§2.16` cite resolves to the right section. What is wrong is the description.
- **evidence:** The checklist item in `skills/sota-code-security/rules/16-where-no-ops-hide.md` reads "a mean, a rollup or a 'worst case' that makes a real signal disappear into the total". That describes a present signal being diluted. §2.16 (:236-288) describes the reverse: a sum over a mixed result stays non-empty when the detection field is empty ("12 of 35 controls were green on a result containing no detections"). Its discriminating question ("Which attribute would be empty if the detector were deleted…") is missing from the item. The item flags averaging and worst-case rollups, which no section of 16 tells builders to avoid. rules/10:217-220 words the item correctly.
- **if confirmed, minimal fix:** reword the rules/16 item to match rules/10:217-220 ("names the field that carries the detection…").

### F-S3-3 — identity rules/07 links "detection rules/07" to itself
- **verdict:** CONFIRMED (Low)
- **evidence:** `grep -n 'rules/07\](' skills/sota-identity-access/rules/07-active-directory.md` returns :12 → `../../sota-detection-engineering/rules/07-ad-attack-detection.md` (correct), and :69, :91, :116 and :175 → `07-active-directory.md`, which is this same file. The target `sota-detection-engineering/rules/07-ad-attack-detection.md` exists.
- **if confirmed, minimal fix:** repoint the four links to `../../sota-detection-engineering/rules/07-ad-attack-detection.md`.

---

**Tally: 15 judged — 10 CONFIRMED, 2 DOWNGRADED, 3 REFUTED** (precision on this sample: 12/15 real, 10/15 at the claimed severity). One confirmed finding (F17) carries a wrong proposed fix.
