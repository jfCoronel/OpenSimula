# Development Roadmap

Working notes for resuming development on OpenSimula from any machine. This file is for
the maintainer, not end users — it is not part of the published docs (`mkdocs/`).

## Where things stand (2026-09-11, v0.8.7)

- The `pro.editor()` Jupyter widget's `_esm` module is now fully bundled (Ajv included), so
  it loads in VS Code notebooks as well as JupyterLab (was issue #1, fixed on
  `fix/editor-vscode-ajv-import`, merged in PR #2).
- 3D visualization is now Plotly-only: `vedo`/VTK have been fully removed (dependency,
  `get_vedo_mesh()`/`get_vedo_meshes()`, the desktop `Plotter` window). `Project.show_3D()`
  only shows and returns nothing; `Project.plotly_figure_3D()` returns the figure to compose
  or save instead. Removing `vedo` also uninstalled `matplotlib`, which was only a transitive
  dependency but is imported directly by `Environment_3D.show_sunny_fraction()` — it is now
  declared explicitly in `pyproject.toml`. Worth remembering if another dependency is ever
  dropped: check `uv sync`'s uninstall list for anything the code still imports directly.
- `README.md` was rewritten for GitHub/PyPI (badges, quick example, component overview).

## Known follow-ups

Concrete, verified items — not ideas, things already identified as needing attention:

- **Editor's lazy Plotly import may hit the same VS Code CSP as the Ajv bug.**
  `src/opensimula/editor/vendor/editor.src.js` does `import(PLOTLY_URL)` (from esm.sh) on
  demand when the 3D view is opened, separate from the Ajv static import that was bundled in
  PR #2. This dynamic import was not implicated in issue #1 (which failed at initial widget
  load), but it fetches from a remote origin the same way the old Ajv import did, so it may
  fail under VS Code's notebook CSP the first time someone opens the 3D view there. Not
  reproduced or confirmed either way — needs checking in an actual VS Code notebook. If it
  does fail, the fix is the same shape as PR #2: vendor `plotly.js-gl3d-dist-min` into the
  esbuild bundle instead of fetching it at runtime (trade-off: bundle size).
- **`mkdocs/index.md` release notes are stale.** The "Release notes" section's `Current
  Version` line and changelog entries stop at 0.8.5. Versions 0.8.6 (wheel packaging fix),
  the VS Code editor fix, the vedo removal, and 0.8.7 have no entries. Update this file
  whenever a version is actually released (not necessarily on every commit).
- **`Opening.py:79`** — `# TODO: Test surface_type EXTERIOR or INTERIOR` in `check()`: the
  validation that an Opening's `surface_type` is one of the expected values is not
  implemented yet.
- **`HVAC_DX_system.py:14`** — the `spaces` parameter's comment notes it should eventually
  also accept `Air_distribution` and `Energy_load` component types, neither of which exists
  yet in the codebase.

## Backlog / ideas

_Not yet populated — add priorities here as they come up, so the next session (on any
machine) can pick up from a written list instead of from memory._

## How to resume work here

- `uv sync` to install/refresh the environment, `uv run pytest test` to check everything
  still passes (should be green — see `CLAUDE.md` for the full command list).
- `CLAUDE.md` has the architecture overview (component/parameter/variable model, simulation
  loop, component categories) — read it first if returning after a long break.
- `git log --oneline -20` and open PRs/issues at
  https://github.com/jfCoronel/OpenSimula are the source of truth for what actually shipped;
  this file only tracks what has *not* shipped yet.
