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

# --- 11. An assignment prefix does not reach a process substitution ---------
# sota-shell-scripting rules/03 §2a. Executable and deterministic, so the
# convention in CONTRIBUTING.md says the check ships with the rule.
d=$(fresh procsub)
cat > "$d/h.sh" <<'HELPER'
#!/bin/sh
printf 'MY_VAR=%s\n' "${MY_VAR:-UNSET}"
HELPER
chmod +x "$d/h.sh"
for sh in bash zsh; do
  if ! command -v "$sh" >/dev/null 2>&1; then
    skip "11-$sh" "assignment prefix vs process substitution" "$sh not installed"
    continue
  fi
  # CONTROL FIRST: a prefix must reach a PLAIN command, or the helper is broken and
  # the UNSET below would be meaningless.
  ctl=$(cd "$d" && "$sh" -c 'unset MY_VAR; MY_VAR=secret ./h.sh' 2>/dev/null)
  sub=$(cd "$d" && "$sh" -c 'unset MY_VAR; MY_VAR=secret cat <(./h.sh)' 2>/dev/null)
  if [ "$ctl" != "MY_VAR=secret" ]; then
    skip "11-$sh" "assignment prefix vs process substitution" \
      "positive control failed: prefix did not reach a plain command (got '$ctl')"
  elif [ "$sub" = "MY_VAR=UNSET" ]; then
    pass "11-$sh" "$sh: a prefix reaches a plain command but NOT <(…)"
  else
    fail "11-$sh" "a prefix does not reach a process substitution" \
      "sota-shell-scripting rules/03 §2a" \
      "expected MY_VAR=UNSET inside <(…); got '$sub' (control was '$ctl')"
  fi
done

# =============================================================================
# 12-20 — the 2026-09-15/16 intake. Every one of these produces a SILENTLY FALSE
# ANSWER: the command succeeds, prints plausible output, and exits 0 or a status
# nobody reads. That is the selection rule for this block — not "interesting",
# but "would have changed a conclusion someone acted on". Each names the rule it
# backs, so a failure here points at the sentence to re-measure.
# =============================================================================

# --- 12. `rg -rn` parses as `-r n`: content rewritten, line numbers gone -----
# sota-shell-scripting rules/06 §2a — the mechanical tell that section ships.
if ! command -v rg >/dev/null 2>&1; then
  skip 12 "rg -rn eats the -n" "ripgrep not installed"
else
  d=$(fresh rgreplace)
  printf 'alpha Missing auth gate for deletion\n' > "$d/a.py"
  n_out=$(cd "$d" && rg -n 'Missing .*gate for' . 2>/dev/null)
  r_out=$(cd "$d" && rg -rn 'Missing .*gate for' . 2>/dev/null)
  case "$n_out" in
    *:1:*)
      case "$r_out" in
        *':1:'*) fail 12 "rg -rn rewrites content and drops the line number" \
                   "sota-shell-scripting rules/06 §2a" \
                   "-rn still printed a line number; the tell no longer works: $r_out" ;;
        *'n deletion'*) pass 12 "rg -rn rewrites content and drops the line number" ;;
        *) fail 12 "rg -rn rewrites content and drops the line number" \
             "sota-shell-scripting rules/06 §2a" \
             "expected the replacement template in the output; got: $r_out" ;;
      esac ;;
    *) skip 12 "rg -rn eats the -n" "positive control failed: rg -n printed no line number" ;;
  esac
fi

# --- 13. A pattern beginning with `-` is parsed as a flag -------------------
# sota-shell-scripting rules/06 §2c — a clean zero, reason on the stderr you hid.
if ! command -v rg >/dev/null 2>&1; then
  skip 13 "leading-dash pattern parsed as a flag" "ripgrep not installed"
else
  d=$(fresh dashpat)
  printf -- '- [ ] one\n- [ ] two\n' > "$d/t.md"
  bare_rc=0; ( cd "$d" && rg -c -F '- [ ]' . >/dev/null 2>&1 ) || bare_rc=$?
  safe_out=$(cd "$d" && rg -c -F -e '- [ ]' . 2>/dev/null)
  if [ "$bare_rc" -eq 0 ]; then
    fail 13 "a pattern beginning with '-' is parsed as a flag" \
      "sota-shell-scripting rules/06 §2c" \
      "the bare form succeeded (rc=0); the rule says it is consumed as a flag"
  elif [ -z "$safe_out" ]; then
    skip 13 "leading-dash pattern parsed as a flag" "positive control failed: -e form found nothing"
  else
    pass 13 "a leading-dash pattern is eaten as a flag; -e is the fix"
  fi
fi

# --- 14. `|| echo` cannot tell "absent" (1) from "unreadable path" (2) ------
# sota-shell-scripting rules/06 §2d — invariant 32 exists because of this.
d=$(fresh absidiom)
printf 'add_compile_options(-Werror)\n' > "$d/CMakeLists.txt"
present_rc=0; ( cd "$d" && grep -rnE 'Werror' CMakeLists.txt missing_path_xyz >/dev/null 2>&1 ) || present_rc=$?
absent_rc=0;  ( cd "$d" && grep -rnE 'ZZZNOPE' CMakeLists.txt >/dev/null 2>&1 ) || absent_rc=$?
combined=$(cd "$d" && grep -rnE 'Werror' CMakeLists.txt missing_path_xyz 2>/dev/null || echo "VERDICT-FIRED")
case "$combined" in
  *Werror*VERDICT-FIRED*)
    if [ "$present_rc" -eq "$absent_rc" ]; then
      fail 14 "grep's bad-path exit differs from its absent exit" \
        "sota-shell-scripting rules/06 §2d" \
        "found-plus-missing and truly-absent both exited $present_rc; the rule's branch is moot"
    else
      pass 14 "|| echo fires on exit $present_rc (bad path) as well as $absent_rc (absent)"
    fi ;;
  *) fail 14 "|| echo fires while the match is on screen" \
       "sota-shell-scripting rules/06 §2d" \
       "expected the match AND the verdict; got: $combined" ;;
esac

# --- 15. `pgrep -f` self-match is PLATFORM-SPLIT ---------------------------
# sota-shell-scripting rules/01 §3. Measured 2026-09-16: procps-ng never exits,
# BSD exits immediately. The SPLIT is the claim — a macOS-only test would have
# shipped the never-exiting loop into Linux CI.
if ! command -v pgrep >/dev/null 2>&1 || ! command -v timeout >/dev/null 2>&1; then
  skip 15 "pgrep -f self-match" "pgrep or timeout not installed"
else
  pat="ZZCLAIMPAT15"
  if pgrep -f "$pat" >/dev/null 2>&1; then
    skip 15 "pgrep -f self-match" "a stray process already matches the pattern — confounded"
  else
    loop_rc=0
    timeout 5 bash -c "while pgrep -f $pat >/dev/null 2>&1; do sleep 1; done" || loop_rc=$?
    case "$(uname -s)" in
      Linux)
        if [ "$loop_rc" -eq 0 ]; then
          fail 15 "pgrep -f matches the watching shell on Linux" \
            "sota-shell-scripting rules/01 §3" \
            "the loop exited on its own; the rule says procps-ng never lets it"
        else
          pass 15 "pgrep -f self-matches on Linux: the waiter never exits"
        fi ;;
      Darwin)
        if [ "$loop_rc" -eq 0 ]; then
          pass 15 "pgrep -f does NOT self-match on BSD: the waiter exits (the split holds)"
        else
          fail 15 "pgrep -f does not self-match on BSD" \
            "sota-shell-scripting rules/01 §3" \
            "the loop did not exit (rc=$loop_rc); the platform split is wrong"
        fi ;;
      *) skip 15 "pgrep -f self-match" "unknown platform $(uname -s)" ;;
    esac
  fi
fi

# --- 16. A pipeline's exit status is the LAST stage's ----------------------
# sota-shell-scripting rules/01 §3. This let a red gate run `git push`.
# MEASURED IN A DEFAULT SHELL ON PURPOSE. This harness runs with `set -uo pipefail`,
# under which a pipeline's status is the leftmost FAILING command's -- so testing here
# directly measures the harness's own options and reports rc=1, refuting a true rule.
# Caught by watching this claim fail on its first run: the instrument was the confound,
# which is the same shape as the claim itself (rules/06 §2, your instrument is a control).
pipe_rc=$(bash -c '(exit 1) | tail -1 >/dev/null 2>&1; echo $?')
chained=$(bash -c '(exit 1) | tail -1 >/dev/null 2>&1 && echo yes || echo no')
if [ "$pipe_rc" -eq 0 ] && [ "$chained" = "yes" ]; then
  pass 16 "a failing producer piped to tail exits 0, and the && arm still runs"
else
  fail 16 "a pipeline's status is the last stage's" "sota-shell-scripting rules/01 §3" \
    "expected rc=0 and the && arm to run; got rc=$pipe_rc chained=$chained"
fi

# --- 17. A leading-dash format string: bash rejects, zsh accepts -----------
# sota-shell-scripting rules/06 §2c. Shell-split, which is why "I tested it" is
# not an answer: a contributor checking in zsh concludes the trap is imaginary.
b_rc=0; bash -c 'printf "- [ ] box\n"' >/dev/null 2>&1 || b_rc=$?
if [ "$b_rc" -eq 0 ]; then
  fail 17 "bash printf rejects a leading-dash format" "sota-shell-scripting rules/06 §2c" \
    "bash printf accepted it (rc=0); the rule's shell split is wrong"
elif ! command -v zsh >/dev/null 2>&1; then
  pass 17 "bash printf rejects a leading-dash format (zsh half skipped: not installed)"
else
  z_rc=0; zsh -c 'printf "- [ ] box\n"' >/dev/null 2>&1 || z_rc=$?
  if [ "$z_rc" -eq 0 ]; then
    pass 17 "printf leading-dash: bash rejects (rc=$b_rc), zsh accepts — the split holds"
  else
    fail 17 "zsh printf accepts a leading-dash format" "sota-shell-scripting rules/06 §2c" \
      "zsh also rejected it (rc=$z_rc); the rule claims a split that does not exist"
  fi
fi

# --- 18. `rg --no-ignore` does not rescue a hidden directory ---------------
# sota-shell-scripting rules/06 §2 — the decoy. It searches MORE files and still
# misses a hidden dir, so the run reads as the more thorough one.
if ! command -v rg >/dev/null 2>&1; then
  skip 18 "rg --no-ignore vs hidden dirs" "ripgrep not installed"
else
  d=$(fresh rghidden)
  mkdir -p "$d/.hidden" "$d/visible"
  printf 'TARGETPAT\n' > "$d/.hidden/f.md"
  printf 'TARGETPAT\n' > "$d/visible/f.md"
  vis=$(cd "$d" && rg -l TARGETPAT . 2>/dev/null | wc -l | tr -d ' ')
  noi=$(cd "$d" && rg -l --no-ignore TARGETPAT . 2>/dev/null | wc -l | tr -d ' ')
  hid=$(cd "$d" && rg -l --hidden TARGETPAT . 2>/dev/null | wc -l | tr -d ' ')
  if [ "$vis" -lt 1 ]; then
    skip 18 "rg --no-ignore vs hidden dirs" "positive control failed: default found nothing"
  elif [ "$noi" = "$vis" ] && [ "$hid" -gt "$vis" ]; then
    pass 18 "--no-ignore does not reach a hidden dir ($noi); --hidden does ($hid)"
  else
    fail 18 "--no-ignore leaves hidden dirs excluded" "sota-shell-scripting rules/06 §2" \
      "expected no-ignore==default and hidden>default; got default=$vis no-ignore=$noi hidden=$hid"
  fi
fi

# --- 19. Two-dot `git diff` compares tips; three-dot uses the merge base ---
# sota-docs-workflow rules/03 §3a. It INVENTS regressions, and in a lockfile an
# invented regression reads as a supply-chain attack.
d=$(fresh twodot)
(
  cd "$d" && git init -q -b main . && git config user.email t@t && git config user.name t
  printf 'dep = "1.0.0"\nlib = "2.0.0"\n' > lock.toml && git add -A && git commit -qm base
  git checkout -qb feature
  printf 'dep = "1.0.1"\nlib = "2.0.0"\n' > lock.toml && git commit -qam bump
  git checkout -q main
  printf 'dep = "1.0.0"\nlib = "2.0.1"\n' > lock.toml && git commit -qam security
) >/dev/null 2>&1
if [ ! -d "$d/.git" ]; then
  skip 19 "two-dot diff invents a regression" "git init failed in the sandbox"
else
  two=$(cd "$d" && git diff main..feature -- lock.toml 2>/dev/null | grep -c '^-lib' || true)
  three=$(cd "$d" && git diff main...feature -- lock.toml 2>/dev/null | grep -c '^-lib' || true)
  if [ "$two" -ge 1 ] && [ "$three" -eq 0 ]; then
    pass 19 "two-dot renders main's security bump as a deletion; three-dot does not"
  else
    fail 19 "two-dot renders main's commits as deletions on the branch" \
      "sota-docs-workflow rules/03 §3a" \
      "expected two-dot to delete 'lib' and three-dot not to; got two=$two three=$three"
  fi
fi

# --- 20. A directory secret scan does not read `.gitignore` ----------------
# sota-secrets-management rules/04. The gitignored artifact that `git status`
# never shows is still in scope for the gate. Verified 2026-09-15 on gitleaks
# 8.30.1 -- and the FIRST attempt refuted it, because the fixture was the
# canonical AWS documentation key, which scanners allowlist. The fixture here is
# assembled at runtime so no credential-shaped literal sits in the repo.
if ! command -v gitleaks >/dev/null 2>&1; then
  skip 20 "a directory scan does not honour .gitignore" "gitleaks not installed"
else
  d=$(fresh glignore)
  (
    cd "$d" && git init -q -b main . && git config user.email t@t && git config user.name t
    printf '*.log\n' > .gitignore && git add -A && git commit -qm base
  ) >/dev/null 2>&1
  # Random body, not a repeated character: an entropy-poor fixture is INERT and the
  # positive control below catches that, exactly as it caught the allowlisted key.
  tok="glpat-$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20)"
  if [ ! -d "$d/.git" ]; then
    skip 20 "a directory scan does not honour .gitignore" "git init failed in the sandbox"
  else
    # POSITIVE CONTROL FIRST: the same fixture in a file the scanner plainly sees.
    printf 'token=%s\n' "$tok" > "$d/visible.txt"
    ctl_rc=0; ( cd "$d" && gitleaks dir --no-banner --redact . ) >/dev/null 2>&1 || ctl_rc=$?
    rm -f "$d/visible.txt"
    printf 'token=%s\n' "$tok" > "$d/junk.log"
    dirty=$(cd "$d" && git status --porcelain | wc -l | tr -d ' ')
    test_rc=0; ( cd "$d" && gitleaks dir --no-banner --redact . ) >/dev/null 2>&1 || test_rc=$?
    if [ "$ctl_rc" -eq 0 ]; then
      skip 20 "a directory scan does not honour .gitignore" \
        "positive control failed: the visible fixture was not detected (allowlisted?)"
    elif [ "$dirty" -ne 0 ]; then
      skip 20 "a directory scan does not honour .gitignore" \
        "fixture is not actually ignored (git status saw $dirty entries)"
    elif [ "$test_rc" -ne 0 ]; then
      pass 20 "gitleaks dir flags a gitignored file that git status never shows"
    else
      fail 20 "a directory scan does not honour .gitignore" \
        "sota-secrets-management rules/04" \
        "the ignored fixture was NOT flagged; the rule's scope claim needs re-measuring"
    fi
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
