#!/usr/bin/env bash
# audit.sh — mechanical checks over a finished design system.
# Usage: bash scripts/audit.sh [dir]        (default: design-system)
# Findings are not all defects. Read each one and decide.

set -uo pipefail
DIR="${1:-design-system}"
[ -d "$DIR" ] || { echo "No such directory: $DIR" >&2; exit 1; }

if command -v rg >/dev/null 2>&1; then
  s() { rg --no-messages -n -e "$1" -g '!node_modules' -g '!*.min.*' "$DIR" 2>/dev/null; }
else
  s() { grep -rnE --exclude-dir=node_modules --exclude='*.min.*' -e "$1" "$DIR" 2>/dev/null; }
fi

B=$'\033[1m'; Y=$'\033[33m'; R=$'\033[0m'
[ -t 1 ] || { B=""; Y=""; R=""; }
FLAGS=0

# flag "title" "why" "pattern"  — reports presence
flag() {
  local out n
  out="$(s "$3")" || true
  [ -z "$out" ] && return 0
  n="$(printf '%s\n' "$out" | wc -l | tr -d ' ')"
  FLAGS=$((FLAGS+1))
  printf '\n%s%s%s  (%s)\n  %s\n\n' "$B" "$1" "$R" "$n" "$2"
  printf '%s\n' "$out" | head -20 | sed 's/^/    /'
  [ "$n" -gt 20 ] && printf '    … %s more\n' "$((n-20))"
}

# want "title" "why" "pattern"  — reports absence
want() {
  local n
  n="$(s "$3" | wc -l | tr -d ' ')"
  [ "$n" -gt 0 ] && return 0
  FLAGS=$((FLAGS+1))
  printf '\n%s%s%s\n  %s\n    (nothing matches: %s)\n' "$Y" "$1" "$R" "$2" "$3"
}

echo "Auditing $DIR"
echo "==============================================================="
echo
echo "--- present but suspect -------------------------------------"

flag "Hardcoded hex colors" \
  "Components reference semantic tokens. Token definition files are the legitimate exception." \
  '#[0-9a-fA-F]{3,8}'

flag "Hardcoded rgb/hsl colors" \
  "Same reason. HSL ramps are also not perceptually even — see craft-color.md." \
  '\b(rgba?|hsla?)\('

flag "Numeric z-index" \
  "z-index belongs to the elevation token scale, or two overlays will disagree at 3am." \
  'z-index: *-?[0-9]'

flag "Literal durations in transitions" \
  "Durations come from motion tokens so they can be tuned in one place." \
  'transition[^;]*[0-9]+ms'

flag "outline removed" \
  "Check each: removing the outline without a :focus-visible replacement is the most common keyboard failure." \
  'outline: *none|outline-none'

flag "box-shadow used as a focus ring" \
  "box-shadow is dropped in forced-colors mode, so the ring vanishes in Windows high contrast. Use outline." \
  'focus[^;{]*\{?[^}]{0,80}box-shadow'

flag "Unguarded :hover" \
  "Hover sticks on touch. Wrap in @media (hover: hover) and (pointer: fine)." \
  ':hover'

flag "Animating layout properties" \
  "width/height/top/left/margin animations force layout every frame. Use transform and opacity." \
  'transition[^;]*(width|height|top|left|right|bottom|margin|padding)'

flag "Blanket motion kill" \
  "animation: none !important strands transitionend listeners and leaves overlays half-open. Use 0.01ms." \
  '(animation|transition): *none *!important'

flag 'type="number"' \
  "Spinners, scroll-wheel changes, stripped leading zeros. Use type=text with inputmode=numeric." \
  'type=.{1}number'

flag "Placeholders" \
  "Check each: a placeholder is not a label, and it must not carry the instruction." \
  'placeholder='

flag "100vh" \
  "On mobile this is the large viewport and the bottom is cut off. Use svh or dvh." \
  '100vh'

flag "Zoom disabled" \
  "user-scalable=no and maximum-scale=1 fail WCAG 1.4.4." \
  'user-scalable=no|maximum-scale=1'

flag "Positive tabindex" \
  "Any tabindex above 0 breaks the document's tab order globally." \
  'tab[Ii]ndex=.?\{?[1-9]'

flag "Handlers on non-interactive elements" \
  "onClick on a div needs a role, tabindex, and Enter/Space handling — or should be a button." \
  '<(div|span)[^>]*onClick'

flag "Inline style objects" \
  "Escapes the token layer and cannot be themed." \
  'style=\{\{'

flag "!important" \
  "In a design system this usually signals a specificity problem worth fixing properly." \
  '!important'

echo
echo "--- expected but missing ------------------------------------"

want "No prefers-reduced-motion handling" \
  "Every motion system needs it. See craft-motion.md." 'prefers-reduced-motion'

want "No forced-colors handling" \
  "Windows high contrast drops box-shadows and background images." 'forced-colors'

want "No :focus-visible" \
  "Focus rings should be keyboard-scoped, not removed." ':focus-visible'

want "No min-width: 0" \
  "Flex children need it or long strings blow out the layout. See craft-layout.md." 'min-width: *0|min-w-0'

want "No overscroll-behavior" \
  "Overlays chain their scroll into the page behind them without it." 'overscroll-behavior|overscroll-'

want "No tabular figures" \
  "Any table, timer, counter, or stat needs them." 'tabular-nums|tabular_nums'

want "No safe-area-inset" \
  "Bottom bars and sheets sit under the home indicator on notched devices." 'safe-area-inset'

want "No scroll-margin" \
  "Anchors and keyboard focus land under sticky headers without it." 'scroll-margin|scroll-padding|scroll-mt'

want "No autofill styling" \
  "Autofilled inputs keep the browser's forced background, which breaks dark mode." 'autofill'

want "No live region" \
  "Toasts, async results, and validation summaries need announcement." 'aria-live|role=.{1}status|role=.{1}alert'

want "No inputmode hints" \
  "Mobile keyboards default wrong without them." 'input[Mm]ode'

want "No autocomplete tokens" \
  "Password managers and address autofill need them; it is a bigger usability win than most polish." 'auto[Cc]omplete'

want "No text-wrap balance or pretty" \
  "Headings orphan without it." 'text-wrap|text-balance|text-pretty'

want "No dark theme definition" \
  "Expected [data-theme] or prefers-color-scheme somewhere in the token layer." \
  'data-theme|prefers-color-scheme'

want "No reduced-transparency or contrast handling" \
  "Worth supporting alongside reduced motion." 'prefers-contrast|prefers-reduced-transparency'

echo
echo "==============================================================="
printf 'Flagged %s categories.\n' "$FLAGS"
echo "None are automatic failures. Fix what is real; record deliberate exceptions in CRAFT.md."
