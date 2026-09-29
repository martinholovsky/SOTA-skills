#!/usr/bin/env bash
#
# skill-listing-sources.sh — which SKILL.md files Claude Code's skill listing will
# actually contain on this machine, and how many characters their entries cost.
#
# One implementation for every consumer: plugin-budget-check.sh (the plugin's
# SessionStart notice), verify-setup.sh check 1b, and install.sh's budget offer. Each
# used to walk directories on its own, and all three were wrong the same way —
# field-reported 2026-09-29, measured on the reporter's machine:
#
#   - `find ~/.claude/plugins -maxdepth 4` reached NONE of 250 plugin SKILL.md files
#     (the shallowest sits at depth 5), so an enabled plugin cost nothing on paper.
#     The sota-skills plugin installed beside a clone doubled the library's listing
#     (38,642 chars twice) and every check said it fitted.
#   - ~/.claude/skills/synced/ held TWO account sets (27 files); only the signed-in
#     account's loads, so one set was counted that never reaches the listing.
#   - walking the whole plugins tree would count marketplace clones and every stale
#     cache version (15 of one plugin on that machine), which never load either.
#
# So this reads what the engine reads, not what is on disk:
#   personal   $CLAUDE_HOME/skills/*/SKILL.md
#   synced     $CLAUDE_HOME/skills/synced/<organizationUuid>_<accountUuid>/*/SKILL.md,
#              the account from .claude.json; unknown account -> every set (an upper
#              bound, and said so)
#   plugin     <installPath>/skills/*/SKILL.md for each installed_plugins.json entry
#              that settings.json does not disable; project-scoped entries only for
#              the current project
#   project    ./.claude/skills/*/SKILL.md
# Verified 2026-09-29 against a live session's own listing: 8 qdrant, 1 frontend-design,
# the 14-skill synced set, and both sota copies while the plugin was installed.
#
# NOT countable: built-in skills compiled into the binary. Consumers add an allowance.
#
# Usage:
#   skill-listing-sources.sh            key=value summary: totals per source, any
#                                       duplicate library, and the context window
#                                       (window=, window_source=; see context_window)
#   skill-listing-sources.sh --list     <source>\t<prefix-chars>\t<path>, one per skill
#
# awk only — no jq, no python3: the plugin hook runs this at every session start on
# machines we do not control. Always exits 0 with whatever it could read.
set -uo pipefail

CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
MODE="${1:-summary}"

# Minimal JSON tokenizer: one token per line — S<TAB>string, P<TAB>punct, L<TAB>literal.
# Enough for the two files we read (installed_plugins.json, settings.json) whatever
# their formatting; string escapes are honoured so a quoted path cannot end early.
json_tokens() {  # <file>
  [ -r "$1" ] || return 0
  awk 'BEGIN { RS = "\001" } {
    s = $0; n = length(s); i = 1
    while (i <= n) {
      c = substr(s, i, 1)
      if (c == "\"") {
        out = ""; i++
        while (i <= n) {
          c = substr(s, i, 1)
          if (c == "\\") { out = out substr(s, i + 1, 1); i += 2; continue }
          if (c == "\"") break
          out = out c; i++
        }
        print "S\t" out; i++; continue
      }
      if (index("{}[]:,", c)) { print "P\t" c; i++; continue }
      if (c ~ /[[:space:]]/) { i++; continue }
      lit = ""
      while (i <= n && substr(s, i, 1) !~ /[[:space:],}\]]/) { lit = lit substr(s, i, 1); i++ }
      print "L\t" lit
    }
  }' "$1"
}

# Flatten JSON to `<path>\t<scalar>` lines, path segments joined by \001 so a key that
# contains a dot (every plugin id does: `name@market.place`) stays one segment.
# Array elements are numbered from 0. Built on json_tokens, so formatting is irrelevant.
json_flat() {  # <file>
  json_tokens "$1" | awk -F'\t' '
    function path(   i, p) { p = ""; for (i = 1; i <= d; i++) p = p (i > 1 ? "\001" : "") key[i]; return p }
    $1 == "P" && ($2 == "{" || $2 == "[") {
      if (d > 0 && typ[d] == "a") key[d] = idx[d]++
      d++; typ[d] = ($2 == "{") ? "o" : "a"; idx[d] = 0; key[d] = ""; expect = (typ[d] == "a"); next }
    $1 == "P" && ($2 == "}" || $2 == "]") { d--; expect = (d > 0 && typ[d] == "a"); next }
    $1 == "P" && $2 == ":" { expect = 1; next }
    $1 == "P" && $2 == "," { expect = (typ[d] == "a"); next }
    typ[d] == "o" && !expect { key[d] = $2; next }
    { if (typ[d] == "a") key[d] = idx[d]++
      print path() "\t" $2; expect = (typ[d] == "a") }'
}

# settings.json: the plugin ids explicitly set to false under enabledPlugins.
disabled_plugins() {
  json_flat "$CLAUDE_HOME/settings.json" | awk -F'\t' '
    { n = split($1, k, "\001") }
    n == 2 && k[1] == "enabledPlugins" && $2 == "false" { print k[2] }'
}

# installed_plugins.json: <id> <scope> <projectPath> <installPath> per entry, joined by \037.
# NOT a tab: tab is IFS whitespace to `read`, so an empty projectPath (the usual case)
# collapsed and shifted installPath into the wrong field — every plugin read as absent.
# Observed while writing this: 56 skills counted, 0 of them plugins.
installed_plugins() {
  json_flat "$CLAUDE_HOME/plugins/installed_plugins.json" | awk -F'\t' '
    { n = split($1, k, "\001") }
    n == 4 && k[1] == "plugins" { e = k[2] "\001" k[3]; if (!(e in seen)) { seen[e] = 1; order[++m] = e }
      v[e, k[4]] = $2 }
    END { for (i = 1; i <= m; i++) { e = order[i]; split(e, p, "\001")
      if (v[e, "installPath"] != "") print p[1] "\037" v[e, "scope"] "\037" v[e, "projectPath"] "\037" v[e, "installPath"] } }'
}

# A plugin skill is listed as `<plugin.json name>:<skill>`; the prefix costs characters.
plugin_name() {  # <installPath>
  json_flat "$1/.claude-plugin/plugin.json" | awk -F'\t' '$1 == "name" { print $2; exit }'
}

account_set() {  # prints <org>_<acct>, or nothing
  local f
  for f in "$CLAUDE_HOME/.claude.json" "$HOME/.claude.json"; do
    [ -r "$f" ] || continue
    json_flat "$f" | awk -F'\t' '
      $1 == "oauthAccount\001organizationUuid" { o = $2 }
      $1 == "oauthAccount\001accountUuid" { a = $2 }
      END { if (o != "" && a != "") print o "_" a }'
    return 0
  done
}

list_sources() {
  local f set id scope proj path pname disabled here
  for f in "$CLAUDE_HOME"/skills/*/SKILL.md; do
    [ -e "$f" ] && printf 'personal\t0\t%s\n' "$f"
  done
  if [ -d "$CLAUDE_HOME/skills/synced" ]; then
    set="$(account_set)"
    if [ -n "$set" ] && [ -d "$CLAUDE_HOME/skills/synced/$set" ]; then
      for f in "$CLAUDE_HOME/skills/synced/$set"/*/SKILL.md; do
        [ -e "$f" ] && printf 'synced\t0\t%s\n' "$f"
      done
    else
      for f in "$CLAUDE_HOME"/skills/synced/*/*/SKILL.md; do
        [ -e "$f" ] && printf 'synced-all\t0\t%s\n' "$f"
      done
    fi
  fi
  disabled="$(disabled_plugins)"
  here="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  while IFS="$(printf '\037')" read -r id scope proj path; do
    [ -n "$id" ] && [ -d "$path/skills" ] || continue
    printf '%s\n' "$disabled" | grep -qxF -- "$id" && continue
    case "$scope" in
      project|local) [ "$proj" = "$here" ] || continue ;;
    esac
    pname="$(plugin_name "$path")"; [ -n "$pname" ] || pname="${id%@*}"
    for f in "$path"/skills/*/SKILL.md; do
      [ -e "$f" ] && printf 'plugin:%s\t%d\t%s\n' "$pname" $((${#pname} + 1)) "$f"
    done
  done <<EOF
$(installed_plugins)
EOF
  for f in ./.claude/skills/*/SKILL.md; do
    [ -e "$f" ] || continue
    # the personal dir IS ./.claude/skills when run from $HOME; do not count it twice
    [ "$(cd "$(dirname "$f")/.." && pwd -P)" = "$(cd "$CLAUDE_HOME/skills" 2>/dev/null && pwd -P)" ] && continue
    printf 'project\t0\t%s\n' "$f"
  done
}

# The context window the budget scales with (`contextTokens x 4 x fraction`), in order
# of trust. Only a live session knows it exactly; everything below that is a bound.
#   observed   the last context_window_size our status line saw (statusline.sh caches
#              it; exact, but "last seen" — a later /model switch is not reflected)
#   disabled   CLAUDE_CODE_DISABLE_1M_CONTEXT=1, which forces 200K on every model
#   model      a `[1m]` model: from the SessionStart hook's input (SOTA_SESSION_MODEL),
#              else settings.json `model`. A suffix PROVES 1M; its absence proves
#              nothing — Sonnet 5+, Opus 4.7+ and Fable run 1M natively with no suffix
#              (code.claude.com/docs/en/model-config, fetched 2026-09-29). No
#              model-to-window table on purpose: it would be wrong at the next release.
#   unknown    200K, the smaller window, so a verdict errs toward warning
context_window() {
  local f="$CLAUDE_HOME/sota-skills-data/context-window" size="" when="" now age flat m
  if [ -r "$f" ]; then
    read -r size when < "$f" 2>/dev/null || true
    case "$size" in ''|*[!0-9]*) size="" ;; esac
  fi
  if [ -n "$size" ]; then
    now="$(date +%s)"; age=$(( (now - ${when:-$now}) / 86400 ))
    printf 'window=%s\nwindow_source=observed\nwindow_age_days=%s\n' "$size" "$age"; return
  fi
  flat="$(json_flat "$CLAUDE_HOME/settings.json")"
  if [ "${CLAUDE_CODE_DISABLE_1M_CONTEXT:-}" = 1 ] \
     || printf '%s\n' "$flat" | grep -qx "env$(printf '\001')CLAUDE_CODE_DISABLE_1M_CONTEXT	1"; then
    printf 'window=200000\nwindow_source=disabled\n'; return
  fi
  m="${SOTA_SESSION_MODEL:-$(printf '%s\n' "$flat" | sed -n 's/^model	//p' | head -1)}"
  case "$m" in
    *'[1m]'*) printf 'window=1000000\nwindow_source=model\nwindow_model=%s\n' "$m"; return ;;
  esac
  printf 'window=200000\nwindow_source=unknown\n'
  [ -n "$m" ] && printf 'window_model=%s\n' "$m"
  return 0
}

if [ "$MODE" = "--list" ]; then
  list_sources
  exit 0
fi

# Summary. Each entry costs `- <prefix><name>: <description>` plus a newline — the same
# arithmetic the three consumers used before (cross-checked 2026-09-11 against the
# engine's own count: 38,507 measured vs 38,283 real, +0.58%, erring high).
list_sources | awk -F'\t' '
  { src = $1; pre = $2; f = $3
    n = f; sub(/\/SKILL\.md$/, "", n); sub(/.*\//, "", n)
    len = 0; fm = 0; ind = 0; lines = 0
    while ((getline l < f) > 0) {
      if (l ~ /^---[[:space:]]*$/) { fm = !fm; if (!fm) break; continue }
      if (fm && l ~ /^description:/) { ind = 1; sub(/^description:[[:space:]]*/, "", l); gsub(/^[[:space:]]+|[[:space:]]+$/, "", l); len += length(l); continue }
      if (fm && ind && l ~ /^[[:space:]]/) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", l); len += length(l) + 1; continue }
      if (fm) ind = 0
    }
    close(f)
    cost = len + length(n) + pre + 6
    total += cost; count++
    grp = src; sub(/:.*/, "", grp); chars[grp] += cost; num[grp]++
    # the same library reached twice: a personal/project copy and a plugin copy
    if (n == "sota" && grp != "plugin") local_router = 1
    if (n == "sota" && grp == "plugin") plugin_router = src
  }
  END {
    printf "total=%d\nskills=%d\n", total, count
    for (g in chars) printf "%s_chars=%d\n%s_skills=%d\n", g, chars[g], g, num[g]
    if (local_router && plugin_router != "") { p = plugin_router; sub(/^plugin:/, "", p); printf "duplicate_library=%s\n", p }
  }'
context_window
exit 0
