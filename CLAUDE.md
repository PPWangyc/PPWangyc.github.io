# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Local Preview

No build step. Serve locally with:
```
python3 -m http.server 8000
```
Do not open `index.html` directly via `file://` — some browser behaviors differ.

## Architecture

Single-page static site. All content lives in `index.html`; styling in `css/style.css`; interactivity in `js/script.js`. No package manager, no framework, no compilation.

**Section pattern in `index.html`:**
```html
<div class="sec-wrapper [section-class]" id="[section-id]">
  <div class="row section-head">...</div>
  <div class="row section-item">...</div>
</div>
```

**`js/script.js` behaviors:**
- Collapse/expand sections with auto-scroll
- Profile hover image cycling (keep at least one entry in `hoverImages` to avoid modulo-by-zero)
- Clipboard copy for BibTeX entries via Clipboard.js + Bootstrap Tooltip feedback
- Automatically sets `target="_blank" rel="noopener noreferrer"` on external links — no need to add these manually in HTML

**CDN dependencies** (do not replace with local installs unless asked):
- Bootstrap 5.3.3 (layout, collapse, modal, tooltips)
- Bootstrap Icons 1.11.3
- Academicons
- Clipboard.js 2.0.11

## CSS Conventions

- CSS variables in `:root` for colors (`--cardinal`: #750014, grays) and typography — extend these before using hard-coded values.
- Responsive container max-width: `768px`.
- Breakpoints: `max-width: 767.98px` (mobile), `min-width: 768px` (desktop).

## Content & Editing Scope

- Make minimal, targeted edits. Avoid broad reformatting of `index.html`, `css/style.css`, or `js/script.js`.
- Do not remove the footer template attribution unless explicitly asked.
- Preserve existing tone and content style for biography/publication text unless asked to rewrite.
- Assets are organized by project under `assets/` and referenced with relative paths.
