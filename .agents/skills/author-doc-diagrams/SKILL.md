---
name: author-doc-diagrams
description: Author GDSS documentation with hand-written SVG diagrams shown as images, with Mermaid source kept editable in a collapsible block. Use whenever creating or updating any Markdown doc (README, docs/*.md, harness docs) that would benefit from a diagram, or when the user asks for an "SVG-based" or "visual" doc like the README.
---

# Author Doc Diagrams (SVG-first)

GDSS docs render diagrams as **hand-authored SVG images**, not raw Mermaid fences.
Mermaid does not render on every surface (PyPI, some IDE previews, plain Git hosts),
so a committed SVG is the source of truth for display and the Mermaid is kept as the
editable source. Follow this pattern for every diagram in every doc.

## The required pattern

For each diagram, emit the image first, then the Mermaid source inside a
collapsible `<details>` block. The literal structure to produce is:

1. A centered image:
   `<p align="center"><img src="RELATIVE/PATH/assets/TOPIC/NAME.svg" alt="..." width="100%"></p>`
2. A blank line.
3. `<details>` then `<summary>🔄 Mermaid source (click to expand)</summary>`.
4. A blank line, then a fenced ` ```mermaid ` block with the diagram source.
5. A closing `</details>`.

Copy the exact HTML wrappers from any diagram in `README.md` or `docs/IO & VIZ.md`.

- The `<img>` and `<details>` block are plain HTML/Markdown, never indented.
- Keep the Mermaid source in sync with the SVG — it is the editable origin.
- Use a leading emoji in the `<summary>` to match README style (🔄 🧭 🕸️ 🗺️ 🏗️ ⚡ 🌀).

## Where files live

Assets are grouped by doc/topic under `assets/`:

```
assets/
  io/          # docs/IO & VIZ.md
  product/     # README.md (pipeline, roadmap, architecture, concepts)
```

- SVGs: `assets/<topic>/NAME.svg` (snake_case, descriptive: `change_flow.svg`).
- **New doc?** Create a matching subfolder: `assets/<topic>/` and wire paths from the doc.
- Referencing from `README.md` (repo root): `./assets/product/NAME.svg`.
- Referencing from `docs/*.md`: `../assets/<topic>/NAME.svg` (e.g. `../assets/io/pipeline.svg`).
- Get the relative depth right; a wrong `../` silently breaks the image.

## Authoring the SVG

Match the existing house style in `assets/` (see `assets/product/pipeline.svg`):

- Root: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" width="100%" height="H">`.
- Nodes: `<rect rx="12-14">` with a fill + darker `stroke`, white bold `<text>`.
- Define one arrowhead `<marker id="arrow">` and reuse it on `<line>`/`<path>`.
- Font: `font-family="Segoe UI, Roboto, Arial, sans-serif"`; monospace for code snippets.
- Reuse the shared palette so diagrams look consistent across docs:

| Role | Fill | Stroke |
|------|------|--------|
| Source / Git | `#06b6d4` | `#035e66` |
| Observer / IO | `#0ea5e9` | `#075985` |
| AST / parse | `#2563eb` | `#1e40af` |
| Transform / operator | `#7c3aed` | `#4c1d95` |
| Graph | `#f59e0b` | `#92400e` |
| Output / success | `#10b981` | `#065f46` |
| Runtime / neutral | `#475569` | `#334155` |

- Escape XML in text: `&amp;`, `&lt;`, `&gt;`.
- Add a short footer caption `<text>` when it aids comprehension.

## Checklist before done

```
[ ] Each diagram has BOTH a committed SVG and a <details> Mermaid source
[ ] <img> src path resolves from the doc's directory (../ depth correct)
[ ] SVG uses the shared palette + Segoe UI font + arrow marker
[ ] Mermaid source matches what the SVG depicts
[ ] SVG lives in assets/<topic>/ with a snake_case descriptive name
[ ] No raw ```mermaid fence left as the ONLY representation of a diagram
```

## Reference exemplars

- `README.md` — diagrams in `assets/product/`.
- `docs/IO & VIZ.md` — diagrams in `assets/io/`.
- `assets/<topic>/*.svg` — copy one as a starting scaffold.
