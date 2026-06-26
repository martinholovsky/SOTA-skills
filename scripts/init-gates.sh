#!/usr/bin/env bash
#
# init-gates.sh — generate a SOTA-aligned pre-commit / pre-push gate config for
# the project in the current directory.
#
# What it does:
#   1. Detects which languages the repo contains (by manifest + file extension).
#   2. Writes the matching gates into .pre-commit-config.yaml, between managed
#      markers, so re-running it after you add a language updates only that
#      block and leaves your own hooks untouched (idempotent).
#   3. Splits work the way the skills require: FAST checks (lint, format,
#      secrets) run on commit; HEAVY checks (type-check, tests, vuln scans) run
#      on push. See sota-python rules/01 §6 and sota-devsecops rules/05.
#
# Tools per language follow the SOTA skills exactly:
#   python  ruff (lint+format) · mypy · pytest · pip-audit
#   go      gofumpt · go vet · golangci-lint · go test -race · govulncheck
#   rust    cargo fmt · clippy -D warnings · cargo test · cargo audit
#   js/ts   eslint · tsc --noEmit · <pm> audit
#   shell   shellcheck · shfmt
#   always  gitleaks (secret scanning)
#
# The hooks call your project's own toolchain (language: system) — install the
# tools yourself; the script prints which ones each detected language needs.
# It does not pin tool versions you don't control; run `pre-commit autoupdate`
# to refresh the one upstream-pinned hook (gitleaks).
#
# Usage:
#   scripts/init-gates.sh [--dry-run] [--no-install] [--docs-gate] [--help]
#
#   --docs-gate   also add a pre-commit gate that blocks a commit which changes
#                 code without touching any docs (README/CHANGELOG/docs/*.md).
#                 Writes a small helper to .sota/docs-gate.sh. Heuristic and
#                 bypassable (SKIP=sota-docs-gate git commit) — opt-in on purpose.
#
set -euo pipefail

readonly CONFIG=".pre-commit-config.yaml"
readonly BEGIN_MARK="  # >>> sota-gates (managed by init-gates.sh — edits here are overwritten) >>>"
readonly END_MARK="  # <<< sota-gates <<<"
# Pinned because gitleaks is an upstream-managed hook; `pre-commit autoupdate`
# bumps it. Re-verify against the gitleaks releases page when you refresh.
readonly GITLEAKS_REV="v8.30.0"

DRY_RUN=0
DO_INSTALL=1
DOCS_GATE=0
readonly DOCS_GATE_HELPER=".sota/docs-gate.sh"

log()  { printf '  %s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; s/^#//; /^set -euo/d'
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)    DRY_RUN=1 ;;
    --no-install) DO_INSTALL=0 ;;
    --docs-gate)  DOCS_GATE=1 ;;
    -h|--help)    usage 0 ;;
    *)            die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

# --- collect the tracked/relevant file list once -----------------------------
# Prefer git (fast, already ignores vendored dirs); fall back to find with the
# usual heavy dirs pruned.
list_files() {
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # tracked + untracked-but-not-ignored, so a just-created manifest is seen
    git ls-files --cached --others --exclude-standard
  else
    find . -type f \
      -not -path '*/.git/*' \
      -not -path '*/node_modules/*' \
      -not -path '*/.venv/*' -not -path '*/venv/*' \
      -not -path '*/target/*' -not -path '*/dist/*' -not -path '*/build/*' \
      | sed 's|^\./||'
  fi
}
FILES="$(list_files)"

has() { printf '%s\n' "$FILES" | grep -qE "$1"; }

# --- language detection ------------------------------------------------------
USE_PY=0; USE_GO=0; USE_RUST=0; USE_JS=0; USE_TS=0; USE_SH=0
has '(^|/)(pyproject\.toml|setup\.py|setup\.cfg|requirements[^/]*\.txt)$' && USE_PY=1
has '\.py$'        && USE_PY=1
has '(^|/)go\.mod$' && USE_GO=1
has '\.go$'        && USE_GO=1
has '(^|/)Cargo\.toml$' && USE_RUST=1
has '(^|/)package\.json$' && USE_JS=1
has '\.(mjs|cjs|jsx)$'  && USE_JS=1
has '(^|/)tsconfig[^/]*\.json$' && { USE_JS=1; USE_TS=1; }
has '\.tsx?$'      && { USE_JS=1; USE_TS=1; }
has '\.(sh|bash)$' && USE_SH=1

# --- package-manager nuances -------------------------------------------------
# Python: prefer `uv run` when uv is in use, else call tools directly.
PYRUN=""
if has '(^|/)uv\.lock$' || (has '(^|/)pyproject\.toml$' && grep -qs '\[tool\.uv\]' pyproject.toml); then
  PYRUN="uv run "
fi
# JS: pick the audit command for the detected package manager.
JS_AUDIT="npm audit --audit-level=high --omit=dev"
has '(^|/)pnpm-lock\.yaml$' && JS_AUDIT="pnpm audit --audit-level high --prod"
has '(^|/)yarn\.lock$'      && JS_AUDIT="yarn npm audit --severity high"
has '(^|/)bun\.lockb$'      && JS_AUDIT="bun audit"

# --- block generation --------------------------------------------------------
emit_block() {
  cat <<YAML
  - repo: https://github.com/gitleaks/gitleaks
    rev: ${GITLEAKS_REV}
    hooks:
      - id: gitleaks            # secret scanning — fast, every commit
YAML

  if [ "$USE_PY" -eq 1 ]; then
    cat <<YAML
  # python — ruff fast on commit; mypy/pytest/pip-audit on push
  - repo: local
    hooks:
      - id: sota-ruff
        name: ruff (lint, autofix)
        entry: ${PYRUN}ruff check --fix
        language: system
        types: [python]
        require_serial: true
      - id: sota-ruff-format
        name: ruff format
        entry: ${PYRUN}ruff format
        language: system
        types: [python]
      - id: sota-mypy
        name: mypy (strict type check)
        entry: ${PYRUN}mypy .
        language: system
        types: [python]
        pass_filenames: false
        stages: [pre-push]
      - id: sota-pytest
        name: pytest
        entry: ${PYRUN}pytest -q
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
      - id: sota-pip-audit
        name: pip-audit (dependency CVEs)
        entry: ${PYRUN}pip-audit
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
YAML
  fi

  if [ "$USE_GO" -eq 1 ]; then
    cat <<'YAML'
  # go — gofumpt/vet fast on commit; golangci-lint/test/govulncheck on push
  - repo: local
    hooks:
      - id: sota-gofumpt
        name: gofumpt (format check)
        entry: gofumpt -l -d .
        language: system
        types: [go]
        pass_filenames: false
      - id: sota-go-vet
        name: go vet
        entry: go vet ./...
        language: system
        types: [go]
        pass_filenames: false
      - id: sota-golangci-lint
        name: golangci-lint
        entry: golangci-lint run
        language: system
        types: [go]
        pass_filenames: false
        stages: [pre-push]
      - id: sota-go-test
        name: go test -race
        entry: go test -race ./...
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
      - id: sota-govulncheck
        name: govulncheck
        entry: govulncheck ./...
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
YAML
  fi

  if [ "$USE_RUST" -eq 1 ]; then
    cat <<'YAML'
  # rust — fmt fast on commit; clippy/test/audit on push
  - repo: local
    hooks:
      - id: sota-cargo-fmt
        name: cargo fmt --check
        entry: cargo fmt --all --check
        language: system
        files: \.rs$
        pass_filenames: false
      - id: sota-clippy
        name: cargo clippy -D warnings
        entry: cargo clippy --all-targets --all-features -- -D warnings
        language: system
        pass_filenames: false
        stages: [pre-push]
      - id: sota-cargo-test
        name: cargo test
        entry: cargo test
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
      - id: sota-cargo-audit
        name: cargo audit
        entry: cargo audit
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
YAML
  fi

  if [ "$USE_JS" -eq 1 ]; then
    printf '  # javascript / typescript — lint/type-check/audit on push\n'
    printf '  - repo: local\n    hooks:\n'
    cat <<'YAML'
      - id: sota-eslint
        name: eslint
        entry: npx --no-install eslint .
        language: system
        types_or: [javascript, jsx, ts, tsx]
        pass_filenames: false
        stages: [pre-push]
YAML
    if [ "$USE_TS" -eq 1 ]; then
      cat <<'YAML'
      - id: sota-tsc
        name: tsc --noEmit
        entry: npx --no-install tsc --noEmit
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
YAML
    fi
    cat <<YAML
      - id: sota-js-audit
        name: dependency audit (high+)
        entry: ${JS_AUDIT}
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
YAML
  fi

  if [ "$USE_SH" -eq 1 ]; then
    cat <<'YAML'
  # shell — shellcheck + shfmt, fast on commit
  - repo: local
    hooks:
      - id: sota-shellcheck
        name: shellcheck
        entry: shellcheck --severity=style --external-sources
        language: system
        types: [shell]
      - id: sota-shfmt
        name: shfmt (diff)
        entry: shfmt -d -i 2 -ci
        language: system
        types: [shell]
YAML
  fi

  if [ "$DOCS_GATE" -eq 1 ]; then
    cat <<YAML
  # docs gate — block a commit that changes code but updates no docs
  - repo: local
    hooks:
      - id: sota-docs-gate
        name: docs updated with code?
        entry: bash $DOCS_GATE_HELPER
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-commit]
YAML
  fi
}

# --- the docs-gate helper (written only with --docs-gate) --------------------
write_docs_gate_helper() {
  mkdir -p "$(dirname "$DOCS_GATE_HELPER")"
  cat > "$DOCS_GATE_HELPER" <<'SH'
#!/usr/bin/env bash
# Generated by init-gates.sh --docs-gate. Fails a commit that changes code
# without touching any docs (README / CHANGELOG / docs/ / *.md). Heuristic:
# docstring-only edits inside a code file will trip it — that is the cost of a
# cheap check. Bypass once with:  SKIP=sota-docs-gate git commit   (or --no-verify)
set -euo pipefail
files=$(git diff --cached --name-only --diff-filter=ACMR)
[ -n "$files" ] || exit 0
code=$(printf '%s\n' "$files" | grep -E '[.](py|go|rs|ts|tsx|js|jsx|mjs|cjs|java|rb|php|cs|kt|swift|c|cc|cpp|h|hpp)$' || true)
docs=$(printf '%s\n' "$files" | grep -Ei '[.](md|mdx|rst)$|(^|/)docs/|(^|/)readme|(^|/)changelog|(^|/)agents[.]md' || true)
if [ -n "$code" ] && [ -z "$docs" ]; then
  printf 'sota-docs-gate: code changed but no docs/README/CHANGELOG updated.\n' >&2
  printf 'Update the docs in this commit, or bypass once: SKIP=sota-docs-gate git commit\n' >&2
  exit 1
fi
exit 0
SH
}

# --- assemble the file (create / replace-block / insert) ---------------------
assemble() {
  local block="$1" tmp
  tmp="$(mktemp)"

  # The block file holds only the hook entries; the markers are written here so
  # they can never be duplicated by a re-run.
  if [ ! -f "$CONFIG" ]; then
    {
      printf '# Managed in part by scripts/init-gates.sh. Hooks between the\n'
      printf '# sota-gates markers are regenerated on each run; add your own\n'
      printf '# hooks OUTSIDE the markers (still under the single repos: key).\n'
      printf 'default_install_hook_types: [pre-commit, pre-push]\n'
      printf 'repos:\n'
      printf '%s\n' "$BEGIN_MARK"
      cat "$block"
      printf '%s\n' "$END_MARK"
    } >"$tmp"
  elif grep -qF "$BEGIN_MARK" "$CONFIG" && grep -qF "$END_MARK" "$CONFIG"; then
    # Replace the existing managed block in place (markers kept, body swapped).
    awk -v b="$BEGIN_MARK" -v e="$END_MARK" -v f="$block" '
      $0==b {print; while ((getline line < f) > 0) print line; close(f); skip=1; next}
      $0==e {print; skip=0; next}
      skip!=1 {print}
    ' "$CONFIG" >"$tmp"
  elif grep -qE '^repos:' "$CONFIG"; then
    # Existing config without our markers: insert a fresh marked block after repos:.
    awk -v b="$BEGIN_MARK" -v e="$END_MARK" -v f="$block" '
      /^repos:[[:space:]]*$/ && !done {print; print b; while ((getline line < f) > 0) print line; close(f); print e; done=1; next}
      {print}
    ' "$CONFIG" >"$tmp"
    grep -qE '^default_install_hook_types:' "$CONFIG" \
      || warn "add 'default_install_hook_types: [pre-commit, pre-push]' to $CONFIG so both stages install"
  else
    die "$CONFIG exists but has no 'repos:' key — refusing to guess its shape; merge by hand"
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    printf '\n--- %s (dry run, not written) ---\n' "$CONFIG"
    cat "$tmp"
    rm -f "$tmp"
    return
  fi
  [ -f "$CONFIG" ] && cp "$CONFIG" "$CONFIG.bak"
  mv "$tmp" "$CONFIG"
}

# --- run ---------------------------------------------------------------------
detected=""
[ "$USE_PY" -eq 1 ]   && detected="$detected python(ruff,mypy,pytest,pip-audit)"
[ "$USE_GO" -eq 1 ]   && detected="$detected go(gofumpt,golangci-lint,govulncheck)"
[ "$USE_RUST" -eq 1 ] && detected="$detected rust(cargo fmt,clippy,cargo-audit)"
[ "$USE_JS" -eq 1 ]   && detected="$detected js/ts(eslint,tsc,audit)"
[ "$USE_SH" -eq 1 ]   && detected="$detected shell(shellcheck,shfmt)"

if [ -z "$detected" ]; then
  warn "no supported languages detected (python/go/rust/js-ts/shell) — only the gitleaks secret-scan gate will be written"
fi

log "detected:$detected gitleaks$([ "$DOCS_GATE" -eq 1 ] && echo ' +docs-gate')"
block_file="$(mktemp)"
emit_block >"$block_file"
assemble "$block_file"
rm -f "$block_file"

if [ "$DRY_RUN" -eq 1 ]; then
  [ "$DOCS_GATE" -eq 1 ] && log "(--docs-gate would also write $DOCS_GATE_HELPER)"
  exit 0
fi

if [ "$DOCS_GATE" -eq 1 ]; then
  write_docs_gate_helper
  log "wrote $DOCS_GATE_HELPER (the docs-gate hook runs this)"
fi

log "wrote $CONFIG (previous saved to $CONFIG.bak if it existed)"

if [ "$DO_INSTALL" -eq 1 ]; then
  if command -v pre-commit >/dev/null 2>&1; then
    pre-commit install --hook-type pre-commit --hook-type pre-push >/dev/null
    log "installed git hooks (pre-commit + pre-push)"
  else
    warn "pre-commit not found — install it (pipx install pre-commit) then run: pre-commit install --hook-type pre-commit --hook-type pre-push"
  fi
fi

cat <<'NEXT'

Next steps:
  - Install the per-language tools listed above (the hooks call your toolchain).
  - Review .pre-commit-config.yaml — it is a SOTA-aligned starting point, not law.
  - Run once over everything:  pre-commit run --all-files
  - Refresh the gitleaks pin:   pre-commit autoupdate
  - Re-run this script after adding a language; it updates only the managed block.
NEXT
