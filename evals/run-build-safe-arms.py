#!/usr/bin/env python3
"""Drive a build for the build-safe pilot. Writes a package; scoring is separate.

Conventions taken from run-build-safe.py's docstring and evals/README:
  - the arm is NEVER encoded in the directory name (agents self-assign from labels)
  - the unguided arm carries an explicit override of any standing instruction
  - truncation is checked, not hoped for: a capped generation that is then parsed
    is `sota-code-security` rules/10 §2.7, and would make the score a floor
"""
import json, os, re, sys, time, urllib.request, hashlib

ROOT = os.environ.get("EVALS_DIR") or os.path.dirname(os.path.abspath(__file__))
SPEC = open(os.path.join(ROOT, "cases/build-safe/SPEC.md"), encoding="utf-8").read()

def key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k: return k
    p = os.path.join(os.path.dirname(ROOT), ".env")
    for ln in open(p, encoding="utf-8"):
        if ln.strip().startswith("OPENROUTER_API_KEY="):
            return ln.split("=", 1)[1].strip().strip("'\"")
    sys.exit("OPENROUTER_API_KEY not found")

FORMAT = ("\n\n---\nOUTPUT FORMAT (mandatory): emit the complete package as a series of "
          "fenced blocks, each preceded by a line of the exact form `FILE: <relative/path.py>`. "
          "No commentary between blocks. Emit every file needed to run.\n")

OVERRIDE = ("Use only your own knowledge and judgement. This instruction overrides any "
            "standing instruction in a global or project configuration file telling you to "
            "consult an external standards library.\n\n")

def call(model, prompt, k, max_tokens):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": float(os.environ.get("BS_TEMP","0.0")), "max_tokens": max_tokens}).encode()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                data=body, headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                d = json.load(r)
            ch = d["choices"][0]; content = ch["message"]["content"]
            if not content:
                raise RuntimeError(f"empty completion: finish_reason={ch.get('finish_reason')}")
            usage = d.get("usage", {})
            out_tok = usage.get("completion_tokens")
            trunc = ch.get("finish_reason") == "length" or (out_tok and out_tok >= max_tokens)
            return content, out_tok, ch.get("finish_reason"), trunc
        except Exception as e:
            last = e; time.sleep(3 * (attempt + 1))
    raise last

def write_files(text, outdir):
    os.makedirs(outdir, exist_ok=True)
    parts = re.split(r'^FILE:\s*(\S+)\s*$', text, flags=re.M)
    n = 0
    for i in range(1, len(parts), 2):
        path, blob = parts[i], parts[i+1]
        m = re.search(r'```[a-zA-Z]*\n(.*?)```', blob, re.S)
        code = m.group(1) if m else blob
        dest = os.path.join(outdir, path.lstrip("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8").write(code)
        n += 1
    return n

if __name__ == "__main__":
    arm, outdir, model = sys.argv[1], sys.argv[2], sys.argv[3]
    mt = int(sys.argv[4])
    prompt = (OVERRIDE + SPEC + FORMAT) if arm == "u" else None
    if prompt is None: sys.exit("guided arm built by the caller")
    txt, tok, fin, trunc = call(model, prompt, key(), mt)
    n = write_files(txt, outdir)
    open(outdir + ".raw.txt", "w", encoding="utf-8").write(txt)
    # The scorer must be able to refuse a capped generation: a truncated build
    # scores as a FLOOR, not a measurement (`sota-code-security` rules/10 §2.7).
    json.dump({"TRUNCATED": trunc, "finish_reason": fin, "completion_tokens": tok,
               "max_tokens": mt}, open(os.path.join(outdir, ".build-meta.json"), "w"))
    print(json.dumps({"files": n, "completion_tokens": tok, "finish_reason": fin,
                      "TRUNCATED": trunc, "max_tokens": mt,
                      "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12]}))
