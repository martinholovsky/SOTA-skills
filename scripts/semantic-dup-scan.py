#!/usr/bin/env python3
"""Find instructions the library states more than once, by meaning rather than by wording.

Run at every release cut (RELEASING.md §2d). Local only: it needs an Ollama server with the
embedding model pulled, which CI does not have, the same way the routing baseline is local.

    uv run --no-project --with numpy python3 scripts/semantic-dup-scan.py           # check
    uv run --no-project --with numpy python3 scripts/semantic-dup-scan.py --report  # list every group
    uv run --no-project --with numpy python3 scripts/semantic-dup-scan.py --add-new-as-untriaged

WHAT IT DOES. Every paragraph and top-level bullet of at least 25 words in skills/*/SKILL.md and
skills/*/rules/*.md (code fences excluded, link targets dropped) is embedded. Pairs from two
different files whose cosine is at or above the threshold are joined into groups. Two kinds of pair
are classified without review and never form a group:
  skill-summary      one side is a skill's own SKILL.md (a top-10 item summarises its rules file)
  language-parallel  two different language skills, word overlap below 0.45 (the same check
                     written for another language: deliberate)
Every other group must carry a verdict in docs/semantic-duplicates.json:
  deliberate   the copy is required (a gated canonical line) or chosen (a per-skill template)
  consolidate  the same instruction in two places: keep one, link from the other
  distinct     the texts look alike and say different things
  untriaged    present when the file was first written (2026-10-30); debt that only shrinks
A group whose blocks are all covered by reviewed groups passes. A NEW block in a group, or a new
group, fails the check (exit 1) until it is given a verdict.

WHY THIS MODEL. Picked 2026-10-30 on 12 library rules, each paired with a paraphrase (same
instruction, other words) and a hard negative (same topic, different instruction). Only the larger
Qwen3 embedding models put every paraphrase above every hard negative: qwen3-embedding:8b by a
margin of 0.10, 4b by 0.03. nomic-embed-text, mxbai-embed-large, bge-m3 and qwen3-embedding:0.6b
all had a hard negative above a paraphrase. That set is embedded on EVERY run as the control: if
the model no longer separates it at the stored threshold, the run exits 2 instead of reporting.
A clean result from an instrument that cannot tell a paraphrase from a neighbour is not evidence.

TWO THRESHOLDS. The control threshold (0.71, the middle of the control set's gap: paraphrases
>= 0.737, hard negatives <= 0.635, unrelated <= 0.683) asks only whether the model still orders
paraphrase above neighbour. The review threshold (0.84) is where library pairs start to be worth a
reviewer's time: measured 2026-10-30 on the library, sampled pairs at 0.84-0.88 were mostly real
duplicates, at 0.80-0.84 mostly a general rule beside its language-specific form, and below 0.80
groups chain into blobs. The cost, stated rather than hidden: an instruction reworded so heavily
that it scores under 0.84 is not caught.

Exit codes: 0 clean, 1 new or unreviewed duplicates, 2 the instrument could not run or failed its
control (no Ollama, no model, empty scope, control not separated, model changed).
"""
import argparse, hashlib, ipaddress, json, os, pathlib, re, socket, subprocess, sys, time, urllib.parse, urllib.request, collections

try:
    import numpy as np
except ImportError:
    sys.exit("numpy is needed: run with `uv run --no-project --with numpy python3 %s`" % sys.argv[0])

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEWED = ROOT / "docs" / "semantic-duplicates.json"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if "://" not in OLLAMA:  # Ollama's own convention allows a bare host:port
    OLLAMA = "http://" + OLLAMA
MINW, LEX_PARALLEL = 25, 0.45
LANGS = {"sota-" + s for s in
         "rust golang c-cpp jvm python javascript-typescript dotnet php ruby swift".split()}
INSTRUCT = ("Instruct: Represent this engineering guideline so that guidelines giving the same "
            "instruction are close\nQuery:")

# The control set: (rule, paraphrase, hard negative). Keep it fixed; changing it is a recalibration.
CONTROL = [
 ("Never interpolate user input into a SQL string; pass every value as a bound parameter so the driver keeps code and data apart.",
  "Build queries with placeholders and bind the values separately: concatenating request data into SQL text lets the input become code.",
  "Connect the application with a database role that can only read and write its own tables, never as the owner or a superuser."),
 ("Authorize on permissions, not role names: check can(user, 'invoice:refund') rather than role == 'admin', so roles can change without code changes.",
  "Code should ask whether the caller holds the specific capability, not which role they have; mapping roles to capabilities stays in one place.",
  "Deny by default: an endpoint with no explicit authorization rule must reject every caller, including authenticated ones."),
 ("Kubernetes stores Secret objects base64-encoded in etcd, which is not encryption; enable encryption at rest with a KMS provider.",
  "A Secret in a cluster is only encoded, not encrypted, unless the API server is configured to encrypt etcd data with an external key service.",
  "Mount secrets into pods as files rather than environment variables, because environment variables leak into crash dumps and child processes."),
 ("Set a timeout on every outbound network call; a call without one can hang a worker forever when the dependency stalls.",
  "No request to another service may wait indefinitely: give each client call a deadline so a stuck dependency cannot pin your threads.",
  "Retry only idempotent operations, with exponential backoff and jitter, and cap the number of attempts."),
 ("A cache key must hash every input that determines the cached artifact; a key that omits one serves a stale artifact as if it were current.",
  "If anything that affects the build output is missing from the cache key, a restore will hand back outdated results that look valid.",
  "Print the cache hit statistics in the job log so you can tell whether the cache saves any time at all."),
 ("A restore through restore-keys is a partial match, not a hit: cache-hit is false, and the dependency install must still run and verify.",
  "When the cache was restored from a fallback prefix rather than the exact key, treat it as a miss and run the frozen install anyway.",
  "Pin every third-party action to a full commit SHA instead of a tag, because tags can be moved to point at different code."),
 ("A cache that a pull request can write must never be restored into a release or signing job.",
  "Untrusted branches may read the shared build cache but nothing they write may reach the job that publishes or signs artifacts.",
  "Run release jobs only from protected tags, and require a second reviewer before a release workflow can be changed."),
 ("Set timeout-minutes on every CI job; without it a hung job holds a runner for the 360-minute default before anything reports.",
  "Give each pipeline job an explicit time limit, because the platform default lets a stuck job occupy a runner for six hours.",
  "Cancel superseded pull-request runs with a concurrency group, but never cancel a run on the default branch."),
 ("A required job skipped by an if: condition reports success, so the gate passes without running; do change detection inside the job.",
  "If a required check's job is skipped by a condition, the platform counts it as passed, so filter inside the job and print why it did nothing.",
  "Shard a slow test suite by measured duration and keep one aggregator job under the required check's name."),
 ("Do not return the same constant from a function's not-found branch and its error branch; the caller can no longer tell absence from failure.",
  "If a lookup returns, say, -1 both when nothing matched and when the query failed, callers will treat an outage as an empty result.",
  "Make illegal states unrepresentable: model a payment as a sum type of pending, settled and refunded instead of a struct of nullable fields."),
 ("Never write passwords, tokens or API keys to logs; scrub them at the logging formatter, not at each call site.",
  "Credentials must not reach log output, so redact secret-bearing fields centrally in the log pipeline rather than trusting every caller.",
  "Log in a structured format with a request ID on every line so one request can be traced across services."),
 ("Strip or escape control characters in user-supplied strings before logging them, or an embedded newline can forge a fake log record.",
  "User text written to a log verbatim can inject line breaks that fabricate entries; neutralise CR, LF and terminal escapes first.",
  "Keep logs for a bounded retention period and delete them on schedule instead of scrubbing individual users' records."),
]


def blocks(path):
    out, cur, fence = [], [], False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            if cur:
                out.append(cur)
            cur = []
            continue
        if fence:
            continue
        if not line.strip() or re.match(r"^(- |\* |\d+\. |\| |#)", line):
            if cur:
                out.append(cur)
            cur = [line] if line.strip() and not line.startswith(("#", "|")) else []
        else:
            cur.append(line)
    if cur:
        out.append(cur)
    res = []
    for b in out:
        text = re.sub(r"\]\([^)]*\)", "]", re.sub(r"\s+", " ", " ".join(b)).strip())
        if len(re.findall(r"[A-Za-z0-9_]+", text)) >= MINW:
            res.append(text)
    return res


def shingles(t):
    w = re.findall(r"[a-z0-9_]+", t.lower())
    return frozenset(tuple(w[i:i + 5]) for i in range(len(w) - 4))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # a redirect from the embedding server is refused, not followed


_OPENER = urllib.request.build_opener(_NoRedirect)


def check_endpoint(allow_remote):
    """The embedding server is operator configuration (OLLAMA_HOST), but the default stays local:
    http(s) only, and a host that does not resolve to loopback needs --allow-remote-ollama."""
    u = urllib.parse.urlsplit(OLLAMA)
    if u.scheme not in ("http", "https") or not u.hostname:
        print("OLLAMA_HOST must be an http(s) URL with a host, got %r" % OLLAMA)
        sys.exit(2)
    try:
        addrs = {ipaddress.ip_address(a[4][0]) for a in socket.getaddrinfo(u.hostname, u.port or 11434)}
    except (socket.gaierror, ValueError) as e:
        print("cannot resolve the Ollama host %r (%s)" % (u.hostname, e))
        sys.exit(2)
    if not all(a.is_loopback for a in addrs) and not allow_remote:
        print("Ollama host %s is not loopback (%s); pass --allow-remote-ollama to send the library's "
              "text there" % (u.hostname, ", ".join(sorted(map(str, addrs)))))
        sys.exit(2)


def api(path, payload=None, timeout=900):
    req = urllib.request.Request(OLLAMA + path, headers={"Content-Type": "application/json"},
                                 data=None if payload is None else json.dumps(payload).encode())
    with _OPENER.open(req, timeout=timeout) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="list every group with its verdict")
    ap.add_argument("--add-new-as-untriaged", action="store_true",
                    help="first-run only: record current unreviewed groups as untriaged debt")
    ap.add_argument("--accept-model", action="store_true",
                    help="the model digest changed and you re-ran the control: record the new digest")
    ap.add_argument("--allow-remote-ollama", action="store_true",
                    help="permit an OLLAMA_HOST that is not loopback")
    args = ap.parse_args()
    check_endpoint(args.allow_remote_ollama)

    reviewed = json.loads(REVIEWED.read_text(encoding="utf-8")) if REVIEWED.exists() else {}
    model = reviewed.get("model", "qwen3-embedding:8b")
    threshold = float(reviewed.get("threshold", 0.84))
    control_threshold = float(reviewed.get("control_threshold", 0.71))

    try:
        tags = api("/api/tags", timeout=30)
    except Exception as e:  # noqa: BLE001 - any failure to reach the instrument is exit 2
        print("cannot reach Ollama at %s (%s). Start it, or set OLLAMA_HOST." % (OLLAMA, e))
        sys.exit(2)
    digest = next((m["digest"][:16] for m in tags.get("models", []) if m["name"] == model), None)
    if not digest:
        print("model %s is not pulled: `ollama pull %s`" % (model, model))
        sys.exit(2)
    if reviewed.get("digest") and reviewed["digest"] != digest and not args.accept_model:
        print("model digest changed (%s -> %s): cosines are not comparable to the reviewed file. "
              "Re-run with --accept-model only after the control below passes." % (reviewed["digest"], digest))
        sys.exit(2)

    # The cache lives in the MAIN checkout's .cache/ (git-ignored), found through git's common
    # directory, so a run from any worktree reuses it instead of re-embedding for hours.
    try:
        common = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                capture_output=True, text=True, check=True).stdout.strip()
        main_checkout = pathlib.Path(common).parent
    except (OSError, subprocess.CalledProcessError):
        main_checkout = ROOT
    cache_dir = main_checkout / ".cache" / "semantic-dup"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_p = cache_dir / ("semantic-dup-%s.json" % re.sub(r"[^A-Za-z0-9.]+", "-", model))
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    key = lambda t: hashlib.sha256((model + "\0" + INSTRUCT + t).encode()).hexdigest()

    def embed_all(texts):
        todo = list(dict.fromkeys(t for t in texts if key(t) not in cache))
        t0 = time.time()
        for i in range(0, len(todo), 64):
            batch = todo[i:i + 64]
            for t, v in zip(batch, api("/api/embed", {"model": model, "input": [INSTRUCT + t for t in batch]})["embeddings"]):
                cache[key(t)] = v
            if i % 1280 == 0:
                cache_p.write_text(json.dumps(cache))
                print("  embedded %d/%d new blocks (%.0fs)" % (i + len(batch), len(todo), time.time() - t0), flush=True)
        cache_p.write_text(json.dumps(cache))
        m = np.array([cache[key(t)] for t in texts], dtype=np.float32)
        return m / np.linalg.norm(m, axis=1, keepdims=True), len(todo)

    # 1. The control: the instrument must separate paraphrase from neighbour at this threshold.
    c, _ = embed_all([t for trip in CONTROL for t in trip])
    c = c.reshape(len(CONTROL), 3, -1)
    para = [float(c[i, 0] @ c[i, 1]) for i in range(len(CONTROL))]
    neg = [float(c[i, 0] @ c[i, 2]) for i in range(len(CONTROL))]
    unrel = [float(c[i, 0] @ c[j, 0]) for i in range(len(CONTROL)) for j in range(i + 1, len(CONTROL))]
    print("control: %d paraphrases min %.3f | %d hard negatives max %.3f | %d unrelated max %.3f | control threshold %.2f"
          % (len(para), min(para), len(neg), max(neg), len(unrel), max(unrel), control_threshold))
    if not (min(para) >= control_threshold > max(neg + unrel)):
        print("FAIL (exit 2): the model does not separate the control set at its threshold, "
              "so an empty result would mean nothing. Recalibrate before trusting a run.")
        sys.exit(2)

    # 2. The library.
    files = sorted(ROOT.glob("skills/*/rules/*.md")) + sorted(ROOT.glob("skills/*/SKILL.md"))
    items = [(str(f.relative_to(ROOT / "skills")), t) for f in files for t in blocks(f)]
    if not files or not items:
        print("empty scope: %d files, %d blocks (exit 2)" % (len(files), len(items)))
        sys.exit(2)
    E, fresh = embed_all([t for _, t in items])
    print("scope: %d skill files, %d blocks of >= %d words (%d newly embedded); model %s @ %s"
          % (len(files), len(items), MINW, fresh, model, digest))

    fpath = [f for f, _ in items]
    skill = [f.split("/")[0] for f in fpath]
    bid = ["%s#%s" % (f, hashlib.sha256(t.encode()).hexdigest()[:12]) for f, t in items]
    sh = [shingles(t) for _, t in items]
    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    classes = collections.Counter()
    for s in range(0, len(items), 1024):
        sim = E[s:s + 1024] @ E.T
        for i, j in zip(*np.nonzero(sim >= threshold)):
            a, b = s + int(i), int(j)
            if b <= a or fpath[a] == fpath[b]:
                continue
            if skill[a] == skill[b] and (fpath[a].endswith("SKILL.md") or fpath[b].endswith("SKILL.md")):
                classes["skill-summary"] += 1
                continue
            jac = len(sh[a] & sh[b]) / max(1, len(sh[a] | sh[b]))
            if skill[a] in LANGS and skill[b] in LANGS and skill[a] != skill[b] and jac < LEX_PARALLEL:
                classes["language-parallel"] += 1
                continue
            classes["review"] += 1
            parent[find(a)] = find(b)
    comp = collections.defaultdict(list)
    for i in range(len(items)):
        comp[find(i)].append(i)
    groups = [sorted(v, key=lambda i: bid[i]) for v in comp.values() if len({fpath[i] for i in v}) > 1]
    groups.sort(key=lambda v: bid[v[0]])
    print("pairs at >= %.2f across files: %d to review, %d skill-summary, %d language-parallel; %d groups"
          % (threshold, classes["review"], classes["skill-summary"], classes["language-parallel"], len(groups)))

    known = {}
    for g in reviewed.get("groups", []):
        for m in g["members"]:
            known[m] = g
    new_groups = [v for v in groups if any(bid[i] not in known for i in v)]
    current = {bid[i] for v in groups for i in v}
    stale = [g for g in reviewed.get("groups", []) if not any(m in current for m in g["members"])]
    verdicts = collections.Counter(g["verdict"] for g in reviewed.get("groups", []))
    print("reviewed file: %d groups (%s); %d no longer found (fixed or edited: remove them)"
          % (len(reviewed.get("groups", [])), ", ".join("%s %d" % kv for kv in sorted(verdicts.items())) or "none", len(stale)))

    def show(v, verdict=""):
        fl = sorted({fpath[i] for i in v})
        print("\n[%s] %d blocks in %d files: %s" % (verdict or "NEW", len(v), len(fl), ", ".join(fl[:6]) + (" ..." if len(fl) > 6 else "")))
        for i in v[:3]:
            print("   %s: %s" % (fpath[i], items[i][1][:160]))

    if args.report:
        for v in groups:
            g = known.get(bid[v[0]])
            show(v, g["verdict"] if g and all(bid[i] in known for i in v) else "")
    if args.add_new_as_untriaged and new_groups:
        reviewed.setdefault("groups", [])
        for v in new_groups:
            reviewed["groups"].append({"verdict": "untriaged", "note": "",
                                       "sample": items[v[0]][1][:120], "members": [bid[i] for i in v]})
    if args.add_new_as_untriaged or args.accept_model:
        reviewed.update({"model": model, "digest": digest, "threshold": threshold,
                         "control_threshold": control_threshold})
        reviewed["groups"] = [g for g in reviewed.get("groups", []) if g not in stale]
        REVIEWED.write_text(json.dumps(reviewed, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote %s" % REVIEWED.relative_to(ROOT))
        return
    if new_groups:
        for v in new_groups:
            show(v)
        print("\nFAIL: %d group(s) with blocks not yet reviewed. Give each a verdict in %s "
              "(deliberate / consolidate / distinct), or consolidate the text." % (len(new_groups), REVIEWED.relative_to(ROOT)))
        sys.exit(1)
    print("ok: every group above the threshold has a verdict")


if __name__ == "__main__":
    main()
