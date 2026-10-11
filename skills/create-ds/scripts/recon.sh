#!/usr/bin/env bash
# recon.sh — inventory a codebase's existing UI decisions.
# Usage: bash scripts/recon.sh [root] > design-system/RECON-raw.md
# Uses ripgrep if present, plain grep otherwise.

set -uo pipefail
ROOT="${1:-.}"
cd "$ROOT" || exit 1

EXCLUDES=(node_modules dist build .next out coverage .git vendor .venv __pycache__)

if command -v rg >/dev/null 2>&1; then
  ENGINE=rg
  RG_EX=(); for d in "${EXCLUDES[@]}"; do RG_EX+=(-g "!$d"); done
  RG_EX+=(-g '!*.min.*' -g '!*.map' -g '!*-lock.*')
  sm() { local p="$1"; shift; local g=(); for x in "$@"; do g+=(-g "$x"); done
         rg --no-messages -oIN -e "$p" "${RG_EX[@]}" "${g[@]}" . 2>/dev/null; }
  sf() { local p="$1"; shift; local g=(); for x in "$@"; do g+=(-g "$x"); done
         rg --no-messages -l -e "$p" "${RG_EX[@]}" "${g[@]}" . 2>/dev/null; }
else
  ENGINE=grep
  GR_EX=(); for d in "${EXCLUDES[@]}"; do GR_EX+=(--exclude-dir="$d"); done
  GR_EX+=(--exclude='*.min.*' --exclude='*.map' --exclude='*-lock.*')
  sm() { local p="$1"; shift; local g=(); for x in "$@"; do g+=(--include="$x"); done
         grep -rhoE "${GR_EX[@]}" "${g[@]}" -e "$p" . 2>/dev/null; }
  sf() { local p="$1"; shift; local g=(); for x in "$@"; do g+=(--include="$x"); done
         grep -rlE "${GR_EX[@]}" "${g[@]}" -e "$p" . 2>/dev/null; }
fi

sc()  { sm "$@" | wc -l | tr -d ' '; }
top() { sort | uniq -c | sort -rn | head -"${1:-25}" | sed 's/^ */    /'; }
hdr() { printf '\n\n## %s\n' "$1"; }
sub() { printf '\n### %s\n\n' "$1"; }

CODE=('*.tsx' '*.jsx' '*.ts' '*.js' '*.vue' '*.svelte' '*.astro')
STYLE=('*.css' '*.scss' '*.sass' '*.less')
ALLUI=("${CODE[@]}" "${STYLE[@]}" '*.html')

printf '# Recon (raw)\n\nGenerated %s in %s using %s\n' "$(date -u +%Y-%m-%dT%H:%MZ)" "$(pwd)" "$ENGINE"

hdr "Stack"
for f in package.json deno.json composer.json Gemfile go.mod; do [ -f "$f" ] && echo "    found: $f"; done
if [ -f package.json ]; then
  sub "Dependencies that matter"
  grep -oE '"(react|react-dom|vue|svelte|@angular/core|next|nuxt|astro|remix|vite|typescript|tailwindcss|styled-components|@emotion/[a-z]+|@vanilla-extract/[a-z-]+|sass|less|@stitches/[a-z]+|@radix-ui/[a-z-]+|@headlessui/[a-z]+|@mui/[a-z-]+|@chakra-ui/[a-z]+|@mantine/[a-z]+|antd|bootstrap|class-variance-authority|clsx|tailwind-merge|framer-motion|motion|gsap|@react-spring/[a-z]+|lucide-react|@phosphor-icons/[a-z]+|@heroicons/[a-z]+|@radix-ui/react-icons|@tabler/icons-react|react-icons|@fortawesome/[a-z-]+|iconoir-react|remixicon|storybook|@storybook/[a-z-]+|@floating-ui/[a-z-]+|vaul|sonner|cmdk|recharts|visx|d3|nivo)"' package.json | sort -u | sed 's/^/    /'
fi
for f in tailwind.config.js tailwind.config.ts tailwind.config.cjs tailwind.config.mjs; do
  [ -f "$f" ] && echo "    tailwind v3-style config: $f"
done
[ "$(sc '@theme' "${STYLE[@]}")" -gt 0 ] && echo "    tailwind v4 @theme block present"
[ -f components.json ] && echo "    shadcn/ui: components.json present"
[ -f tsconfig.json ] && echo "    typescript present"
[ -d .storybook ] && echo "    storybook present"

hdr "Component census"
sub "Exported PascalCase components"
sm 'export (default )?(function|const|class) [A-Z][A-Za-z0-9_]*' "${CODE[@]}" |
  sed -E 's/.*(function|const|class) //' | top 40
sub "Most-used JSX components"
sm '<[A-Z][A-Za-z0-9]*' '*.tsx' '*.jsx' | tr -d '<' | top 40
sub "Raw HTML controls (componentization candidates)"
sm '<(button|input|select|textarea|dialog|table|form)[ >]' "${ALLUI[@]}" | tr -d '<> ' | top 12

hdr "Measured values"
sub "Colors — hex"
sm '#[0-9a-fA-F]{3,8}' "${ALLUI[@]}" | tr 'A-F' 'a-f' | top 30
sub "Colors — functional"
sm '(rgba?|hsla?|oklch|oklab|color-mix)\([^)]{0,60}\)' "${ALLUI[@]}" | top 25
sub "Border radius"
sm '(border-radius: *[^;]{1,24}|rounded-[a-z0-9-]*)' "${ALLUI[@]}" | top 25
sub "Spacing — CSS values"
sm '(padding|margin|gap|row-gap|column-gap)[a-z-]*: *-?[0-9.]+(px|rem|em)' "${ALLUI[@]}" |
  grep -oE '^-?[0-9.]+(px|rem|em)$|[0-9.]+(px|rem|em)$' | top 30
sub "Spacing — utility classes"
sm '\b(px|py|pt|pr|pb|pl|mx|my|mt|mr|mb|ml|gap|p|m)-[0-9.]+' "${CODE[@]}" '*.html' | top 30
sub "Font sizes"
sm '(font-size: *[0-9.]+(px|rem|em)|text-(xs|sm|base|lg|xl|[0-9]xl))' "${ALLUI[@]}" | top 25
sub "Font weights"
sm '(font-weight: *[0-9]{3}|font-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black))' "${ALLUI[@]}" | top 15
sub "Letter spacing"
sm '(letter-spacing: *-?[0-9.]+(px|em)|tracking-[a-z0-9-]+)' "${ALLUI[@]}" | top 15
sub "Line heights"
sm '(line-height: *[0-9.]+(px|rem)?|leading-[a-z0-9-]+)' "${ALLUI[@]}" | top 15
sub "Shadows"
sm '(box-shadow: *[^;]{0,80}|shadow-[a-z0-9-]+)' "${ALLUI[@]}" | top 20
sub "Durations and easing curves"
sm '([0-9]+ms|cubic-bezier\([^)]{0,40}\)|ease-[a-z-]+|duration-[0-9]+|linear\([^)]{0,60}\))' "${ALLUI[@]}" | top 25
sub "z-index"
sm '(z-index: *-?[0-9]+|z-[0-9]+)' "${ALLUI[@]}" | top 20
sub "Breakpoints"
sm '@media[^{]{0,60}' "${STYLE[@]}" | top 20
sm '\b(sm|md|lg|xl|2xl):' "${CODE[@]}" | top 8

hdr "Typography assets"
sub "Font families declared"
sm "font-family: *[^;}\"']{0,60}" "${ALLUI[@]}" | top 15
sub "Loading strategy"
for q in 'next/font' '@font-face' 'fonts.googleapis' 'fontaine' 'capsize' 'font-display' 'size-adjust' 'ascent-override'; do
  printf '    %-24s %s\n' "$q" "$(sc "$q")"
done
sub "Font files on disk"
find . -type d \( -name node_modules -o -name .git -o -name dist -o -name .next \) -prune -o \
     -type f \( -name '*.woff2' -o -name '*.woff' -o -name '*.ttf' -o -name '*.otf' \) -print 2>/dev/null |
  head -20 | sed 's/^/    /'

hdr "Icons"
sub "Libraries imported"
sm "from ['\"](lucide-react|@phosphor-icons/[a-z]+|@heroicons/[a-z/]+|@radix-ui/react-icons|@tabler/icons-react|react-icons/[a-z0-9]+|@fortawesome/[a-z-]+|iconoir-react|remixicon|@mui/icons-material)" "${CODE[@]}" |
  sed -E "s/.*['\"]//" | top 15
sub "Inline SVG"
printf '    files with inline <svg>: %s\n' "$(sf '<svg' "${CODE[@]}" | wc -l | tr -d ' ')"
sub "Stroke widths in use"
sm 'stroke-?[Ww]idth=.{0,2}[0-9.]+' "${ALLUI[@]}" | grep -oE '[0-9.]+$' | top 10

hdr "Preference queries"
for q in 'prefers-reduced-motion' 'prefers-color-scheme' 'prefers-contrast' 'prefers-reduced-transparency' 'forced-colors' 'color-scheme'; do
  printf '    %-32s %s\n' "$q" "$(sc "$q")"
done

hdr "Accessibility and platform baseline"
for q in ':focus-visible' 'outline: *none' 'outline-none' 'aria-label' 'aria-live' 'aria-expanded' 'aria-invalid' 'aria-describedby' 'role=' 'tabIndex|tabindex' 'inputMode|inputmode' 'autoComplete|autocomplete' 'enterKeyHint|enterkeyhint' 'scrollbar-gutter' 'overscroll-behavior' 'safe-area-inset' 'min-width: *0|min-w-0' 'tabular-nums' 'text-wrap|text-balance' 'scroll-margin|scroll-mt' 'autofill' '100vh' '100dvh|100svh'; do
  printf '    %-32s %s\n' "$q" "$(sc "$q")"
done

hdr "Inline escapes (component APIs that failed someone)"
sm 'style=\{\{[^}]{0,50}' '*.tsx' '*.jsx' | top 15
sm '![a-z-]+-\[[^]]+\]' "${CODE[@]}" | top 15

printf '\n\nEnd of raw recon. Counts show frequency, not intent — read the code before drawing conclusions.\n'
