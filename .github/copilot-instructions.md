# Project Guidelines

## Build And Test
- This repository is a static site (no package manager, no build step, no test runner).
- Use a local HTTP server for preview instead of opening `index.html` with `file://`.
- Preferred preview command: `python3 -m http.server 8000`.

## Architecture
- The site is centered on a single page in `index.html` with section wrappers.
- Main section pattern:
  - Wrapper: `sec-wrapper` with section-specific class and id.
  - Header row: `section-head`.
  - Content rows: `section-item`.
- Styling is in `css/style.css`.
- Interactivity is in `js/script.js` (collapse behaviors, profile hover image swap, clipboard buttons, external-link targeting).
- Assets are organized by project in `assets/*` and referenced with relative paths.

## Conventions
- Keep dependencies CDN-based unless explicitly requested otherwise.
- Preserve the current responsive layout conventions:
  - Shared container max width (`768px`).
  - Existing breakpoints (`max-width: 767.98px`, `min-width: 768px`).
- Prefer extending existing CSS variables in `:root` for colors and typography before introducing hard-coded values.
- Follow existing naming and structure conventions in `index.html` when adding new sections or publication entries.
- Keep JavaScript framework-free and consistent with current vanilla DOM event style.

## Content Safety And Consistency
- Do not remove attribution/footer credit unless explicitly asked.
- When adding external links in HTML, rely on existing script behavior that sets `target="_blank"` and `rel="noopener noreferrer"`.
- When adding profile hover images in `js/script.js`, keep at least one image in `hoverImages` to avoid modulo-by-zero behavior.

## Editing Scope
- Make minimal, targeted edits.
- Avoid broad reformatting of `index.html`, `css/style.css`, or `js/script.js`.
- Preserve existing tone and content style for biography/publication text unless asked to rewrite content.