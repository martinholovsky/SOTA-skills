#!/usr/bin/env bash
# Re-run the EXECUTABLE claims the skills make about tool behaviour.
#
# WHY THIS EXISTS. 218 claims across 92 skill files say "measured" or "verified".
# Most are not executable — they are network reads of third-party sites, runs that
# cost live API calls, or facts about a kernel. A few dozen ARE: they are statements
# about what a tool does, reproducible in a temp directory in milliseconds. Those
# are the ones that can rot silently when a tool changes, and nothing was watching.
#
# It failed for real on 2026-09-13: `sota-shell-scripting` rules/05 §3b shipped
# saying "perl -pi converts a symlink, BSD sed refuses" with GNU sed marked NOT
# VERIFIED because it was absent locally. The unverified cell was carrying the
# rule's advice — measuring GNU and BusyBox INVERTED the recommendation, because
# `sed -i` turns out to be safe only on BSD.
#
# SCOPE, deliberately narrow. Deterministic and platform-split claims only. NOT
# network claims (endoflife.date rows change BY DESIGN — asserting today's values
# makes CI red on a correct world) and NOT claims needing live API calls. A flaky
# gate gets disabled and leaves you worse off than the prose (docs/CONVENTIONS-LEDGER.md).
#
# PLATFORM SPLIT IS THE POINT for several claims: BSD sed refuses where GNU
# converts; BSD grep skips where GNU and ugrep follow. Each test asserts the
# behaviour documented for the implementation *actually present*, so macOS and
# Linux runners each cover their own half and together cover the table.
#
# CONVENTIONS (the same three this repo's other harnesses follow):
#   - a missing binary SKIPS with a printed reason; it never silently passes
#   - the denominator is printed: claims run / skipped / failed
#   - an empty scope FAILS: "0 checked, 0 failed, exit 0" is the signature of a
#     gate that verifies nothing (sota-code-security rules/11 §2.2)
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
ran=0; failed=0; skipped=0

pass() { printf '  [%s] %s — holds\n' "$1" "$2"; ran=$((ran + 1)); }
fail() {
  printf '  [%s] %s — CLAIM NO LONGER HOLDS\n' "$1" "$2"
  printf '        backs: %s\n' "$3"
  printf '        %s\n' "$4"
  ran=$((ran + 1)); failed=$((failed + 1))
}
skip() { printf '  [%s] %s — SKIPPED: %s\n' "$1" "$2" "$3"; skipped=$((skipped + 1)); }

fresh() { local d="$WORK/$1"; rm -rf "$d"; mkdir -p "$d"; printf '%s' "$d"; }

echo "Executable claims made by skills/ — re-run against the tools actually present"
echo "  host: $(uname -s) $(uname -r)"
echo
# --- 1. A hard link does not survive an atomic rename -----------------------
# sota-shell-scripting rules/05 §3c
d=$(fresh hardlink); (
  cd "$d" && printf 'v1\n' > real.txt && ln real.txt hard.txt
) 2>/dev/null
if [ ! -f "$d/hard.txt" ]; then
  skip 1 "hard link vs atomic rename" "ln refused to create a hard link here"
else
  ( cd "$d" && printf 'v2\n' > .t && mv -f .t real.txt )
  got_real=$(cat "$d/real.txt"); got_hard=$(cat "$d/hard.txt")
  if [ "$got_real" = "v2" ] && [ "$got_hard" = "v1" ]; then
    pass 1 "a hard link holds stale content after write-and-rename"
  else
    fail 1 "a hard link holds stale content after write-and-rename" \
      "sota-shell-scripting rules/05 §3c" \
      "expected real=v2 hard=v1 (divergence); got real=$got_real hard=$got_hard"
  fi
fi

# --- 2. A directory cannot be hard-linked -----------------------------------
# sota-shell-scripting rules/05 §3c
d=$(fresh hardlinkdir); mkdir -p "$d/sub"
if ( cd "$d" && ln sub sub2 ) 2>/dev/null; then
  fail 2 "ln refuses to hard-link a directory" "sota-shell-scripting rules/05 §3c" \
    "ln SUCCEEDED on a directory — the rule says this is impossible"
else
  pass 2 "ln refuses to hard-link a directory"
fi

# --- 3. In-place edit replaces a symlink with a regular file ----------------
# sota-shell-scripting rules/05 §3b. perl first, then whichever sed is present.
if ! command -v perl >/dev/null 2>&1; then
  skip 3 "perl -pi replaces a symlink" "perl not installed"
else
  d=$(fresh perlpi); ( cd "$d" && printf 'old\n' > t.txt && ln -s t.txt link.txt )
  ( cd "$d" && perl -pi -e 's/old/new/' link.txt ) 2>/dev/null
  if [ -L "$d/link.txt" ]; then
    fail 3 "perl -pi replaces a symlink with a regular file" \
      "sota-shell-scripting rules/05 §3b" "link.txt is STILL a symlink — perl now follows it?"
  elif [ "$(cat "$d/t.txt")" != "old" ]; then
    fail 3 "perl -pi leaves the symlink TARGET unmodified" \
      "sota-shell-scripting rules/05 §3b" "target changed; perl followed the link"
  else
    pass 3 "perl -pi replaces a symlink, target untouched"
  fi
fi

# --- 4. sed -i on a symlink: BSD refuses, GNU/BusyBox convert ---------------
# sota-shell-scripting rules/05 §3b — THE PLATFORM SPLIT. Detect the flavour and
# assert what the table says for THAT one; each runner covers its own row.
if ! command -v sed >/dev/null 2>&1; then
  skip 4 "sed -i on a symlink" "sed not installed"
else
  flavour="bsd"
  sed --version >/dev/null 2>&1 && flavour="gnu"
  sed --version 2>&1 | grep -qi busybox && flavour="busybox"
  d=$(fresh sedi); ( cd "$d" && printf 'old\n' > t.txt && ln -s t.txt link.txt )
  if [ "$flavour" = "bsd" ]; then ( cd "$d" && sed -i '' 's/old/new/' link.txt ) >/dev/null 2>&1
  else ( cd "$d" && sed -i 's/old/new/' link.txt ) >/dev/null 2>&1; fi
  rc=$?
  if [ "$flavour" = "bsd" ]; then
    if [ -L "$d/link.txt" ] && [ "$rc" -ne 0 ]; then
      pass 4 "BSD sed -i REFUSES a symlink (exit $rc, link intact)"
    else
      fail 4 "BSD sed -i refuses a symlink" "sota-shell-scripting rules/05 §3b" \
        "expected non-zero exit and an intact link; got exit=$rc symlink=$([ -L "$d/link.txt" ] && echo yes || echo no)"
    fi
  else
    if [ ! -L "$d/link.txt" ] && [ "$rc" -eq 0 ]; then
      pass 4 "$flavour sed -i CONVERTS a symlink silently (exit 0)"
    else
      fail 4 "$flavour sed -i converts a symlink silently" "sota-shell-scripting rules/05 §3b" \
        "expected exit 0 and the link gone; got exit=$rc symlink=$([ -L "$d/link.txt" ] && echo yes || echo no)"
    fi
  fi
fi

# --- 5. Recursive search vs a symlinked directory ---------------------------
# sota-shell-scripting rules/06 §2. The fixture's target is reachable ONLY through
# the link — a fixture whose target is also reachable directly is vacuous, because
# every tool "finds" it and the distinction under test disappears.
mk_link_fixture() {
  local d; d=$(fresh "grep_$1")
  mkdir -p "$d/scan" "$d/outside"
  printf 'NEEDLE plain\n'    > "$d/scan/plain.md"
  printf 'NEEDLE via link\n' > "$d/outside/target.md"
  ( cd "$d/scan" && ln -s ../outside linked )
  printf '%s' "$d"
}
# hits(cmd...) -> number of matching lines
hits() { "$@" 2>/dev/null | wc -l | tr -d ' '; }

check_grep() {  # <id> <label> <binary> <expect_r_traversal> <expect_r_argument>
  local id="$1" label="$2" bin="$3" exp_trav="$4" exp_arg="$5" d
  d=$(mk_link_fixture "$id")
  # POSITIVE CONTROL: the plain file must match, or the instrument is broken and
  # every "skipped" reading below would be a false negative.
  local ctl; ctl=$(cd "$d" && hits "$bin" -r NEEDLE scan/plain.md)
  if [ "$ctl" -lt 1 ]; then
    skip "$id" "$label" "positive control failed ($bin found nothing in a plain matching file)"
    return
  fi
  local trav arg
  trav=$(cd "$d" && hits "$bin" -r NEEDLE scan/)        # 2 = followed, 1 = skipped
  arg=$(cd  "$d" && hits "$bin" -r NEEDLE scan/linked)  # 1 = followed, 0 = skipped
  if [ "$trav" = "$exp_trav" ] && [ "$arg" = "$exp_arg" ]; then
    pass "$id" "$label (-r: traversal=$trav argument=$arg)"
  else
    fail "$id" "$label" "sota-shell-scripting rules/06 §2" \
      "expected traversal=$exp_trav argument=$exp_arg; got traversal=$trav argument=$arg"
  fi
}

# ugrep and GNU grep measured identical: -r follows an ARGUMENT, skips in TRAVERSAL.
if command -v ugrep >/dev/null 2>&1; then
  check_grep 5 "ugrep -r skips a symlink met in traversal, follows one named" ugrep 1 1
else
  skip 5 "ugrep -r symlink behaviour" "ugrep not installed"
fi

if command -v grep >/dev/null 2>&1 && grep --version 2>/dev/null | grep -qi 'GNU grep'; then
  check_grep 6 "GNU grep -r skips a symlink met in traversal, follows one named" grep 1 1
elif [ -x /usr/bin/grep ] && /usr/bin/grep --version 2>&1 | grep -qi 'BSD grep'; then
  # BSD: skips BOTH — and follows an argument only with a trailing slash.
  d=$(mk_link_fixture bsd)
  ctl=$(cd "$d" && hits /usr/bin/grep -r NEEDLE scan/plain.md)
  if [ "$ctl" -lt 1 ]; then
    skip 6 "BSD grep -r symlink behaviour" "positive control failed"
  else
    trav=$(cd "$d" && hits /usr/bin/grep -r NEEDLE scan/)
    arg=$(cd  "$d" && hits /usr/bin/grep -r NEEDLE scan/linked)
    slash=$(cd "$d" && hits /usr/bin/grep -r NEEDLE scan/linked/)
    exp_t=1 exp_a=0 exp_s=1
    if [ "$trav" = "$exp_t" ] && [ "$arg" = "$exp_a" ] && [ "$slash" = "$exp_s" ]; then
      pass 6 "BSD grep -r skips both, follows an argument only with a trailing slash"
    else
      fail 6 "BSD grep -r skips both; trailing slash follows" "sota-shell-scripting rules/06 §2" \
        "expected traversal=$exp_t argument=$exp_a trailing-slash=$exp_s; got $trav/$arg/$slash"
    fi
  fi
else
  skip 6 "system grep symlink behaviour" "neither GNU nor BSD grep identified"
fi

# --- 7. ripgrep: defaults skip a symlink met in traversal, --follow follows --
# sota-shell-scripting rules/06 §2
if ! command -v rg >/dev/null 2>&1; then
  skip 7 "rg symlink behaviour" "ripgrep not installed"
else
  d=$(mk_link_fixture rg)
  ctl=$(cd "$d" && hits rg NEEDLE scan/plain.md)
  if [ "$ctl" -lt 1 ]; then
    skip 7 "rg symlink behaviour" "positive control failed"
  else
    # Expectations as VARIABLES, and the message reads the same ones the comparison
    # does. A hardcoded "expected 1 and 2" in the message can drift from the test and
    # print a self-contradictory diagnostic ("expected 1/2; got 1/2") — watched happen
    # while this script was being written. sota-code-security rules/15 §2.1.
    exp_def=1 exp_fol=2
    def=$(cd "$d" && hits rg NEEDLE scan/)
    fol=$(cd "$d" && hits rg --follow NEEDLE scan/)
    if [ "$def" = "$exp_def" ] && [ "$fol" = "$exp_fol" ]; then
      pass 7 "rg defaults skip a symlinked dir; --follow follows it"
    else
      fail 7 "rg defaults skip a symlinked dir; --follow follows" "sota-shell-scripting rules/06 §2" \
        "expected defaults=$exp_def follow=$exp_fol; got defaults=$def follow=$fol"
    fi
  fi
fi

# --- 8. An empty value removes a PATTERN filter (not an identifier one) -----
# sota-shell-scripting rules/06 §2b. THIS TEST EARNED ITS KEEP ON ITS FIRST RUN:
# the rule originally claimed `ps -p ""` "ignores the filter and prints every
# process, exit 0". Measured on BSD ps AND procps-ng 4.0.4, both REJECT it with
# exit 1. The real split is pattern-vs-identifier, and the rule now says so.
if ! command -v git >/dev/null 2>&1 || ! git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
  skip 8 "an empty value removes a pattern filter" "git or a repo unavailable"
else
  total=$(git -C "$REPO" log --oneline 2>/dev/null | wc -l | tr -d ' ')
  empty=""
  filtered=$(git -C "$REPO" log --author="$empty" --oneline 2>/dev/null | wc -l | tr -d ' ')
  real=$(git -C "$REPO" log --author='no-such-author-zzz' --oneline 2>/dev/null | wc -l | tr -d ' ')
  if [ "$total" -lt 1 ]; then
    skip 8 "an empty value removes a pattern filter" "positive control failed: 0 commits in repo"
  elif [ "$filtered" = "$total" ] && [ "$real" -eq 0 ]; then
    pass 8 "an empty --author matches everything ($filtered of $total; a real non-match gives 0)"
  else
    fail 8 "an empty value makes a pattern filter match everything" \
      "sota-shell-scripting rules/06 §2b" \
      "expected empty=$total and a bogus author=0; got empty=$filtered bogus=$real"
  fi
fi

# --- 8b. ...while an IDENTIFIER filter rejects it --------------------------
# The other half of §2b's table, and the half that refuted the original rule.
if ! command -v ps >/dev/null 2>&1; then
  skip 8b "an identifier filter rejects an empty value" "ps not installed"
else
  empty=""
  ps -p "$empty" >/dev/null 2>&1; rc=$?
  n=$(ps -p "$empty" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$rc" -ne 0 ] && [ "$n" -le 1 ]; then
    pass 8b "ps -p \"\" is REJECTED (exit $rc), it does not list everything"
  else
    fail 8b "an identifier filter rejects an empty value" \
      "sota-shell-scripting rules/06 §2b" \
      "expected non-zero exit and no rows; got exit=$rc rows=$n"
  fi
fi

# --- 9. A trailing echo makes the shell's status 0 --------------------------
# sota-shell-scripting rules/01 §3 — `cmd; echo "EXIT=$?"` reports the echo.
( false; echo "EXIT=$?" ) >/dev/null 2>&1; trailing=$?
( false ) >/dev/null 2>&1; bare=$?
if [ "$trailing" -eq 0 ] && [ "$bare" -ne 0 ]; then
  pass 9 "a trailing echo makes a failed command's shell exit 0 (bare=$bare, with echo=$trailing)"
else
  fail 9 "a trailing echo masks a failure" "sota-shell-scripting rules/01 §3" \
    "expected bare!=0 and with-echo==0; got bare=$bare with-echo=$trailing"
fi

# --- 10. zsh does not word-split unquoted expansions ------------------------
# sota-shell-scripting rules/01 §3 — the claim is about ZSH specifically, so it
# skips (loudly) on a machine without one rather than asserting bash's behaviour.
if ! command -v zsh >/dev/null 2>&1; then
  skip 10 "zsh does not word-split unquoted expansions" "zsh not installed"
else
  z_plain=$(zsh -fc 'a="x y z"; printf "[%s]" $a' 2>/dev/null)
  z_split=$(zsh -fc 'a="x y z"; printf "[%s]" ${=a}' 2>/dev/null)
  b_plain=$(bash -c 'a="x y z"; printf "[%s]" $a' 2>/dev/null)
  if [ "$z_plain" = "[x y z]" ] && [ "$z_split" = "[x][y][z]" ] && [ "$b_plain" = "[x][y][z]" ]; then
    pass 10 "zsh passes one argument where bash passes three; \${=a} restores splitting"
  else
    fail 10 "zsh does not word-split; \${=var} does" "sota-shell-scripting rules/01 §3" \
      "expected zsh='[x y z]' zsh-split='[x][y][z]' bash='[x][y][z]'; got '$z_plain' '$z_split' '$b_plain'"
  fi
fi

# --- Result ----------------------------------------------------------------
echo
if [ "$ran" -eq 0 ]; then
  echo "FAIL: 0 claims were executed — every one skipped. A claims gate that checks"
  echo "      nothing passes silently; treat this as a broken environment, not a pass."
  exit 1
fi
printf 'claims run: %d   skipped: %d   failed: %d\n' "$ran" "$skipped" "$failed"
if [ "$failed" -ne 0 ]; then
  echo
  echo "FAIL: a claim the skills make about tool behaviour no longer holds."
  echo "      Re-measure, then correct the rule it backs — the rule is the deliverable,"
  echo "      not this script. An unverified cell that carries a recommendation is a"
  echo "      blocker, not a caveat (docs/ADOPTION-LOG.md, 2026-09-13)."
  exit 1
fi
echo "PASS: every executable claim still holds on this host."
