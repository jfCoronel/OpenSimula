# Building the editor widgets

`static/editor.js`, `static/results.js` and `static/plotly3d.js` are
generated files. Their sources are here: `editor.src.js` (project editor),
`results.src.js` (results viewer), `view3d.js` (3D view helpers shared by
both) and `plotly3d.src.js` (plotly's gl3d bundle as an ES module). Edit
those, then rebuild:

```bash
cd src/opensimula/editor/vendor
npm install
npm run build
```

## Why it has to be bundled

`editor.src.js` used to be shipped as-is and imported Ajv straight from
`https://esm.sh/ajv@8.17.1/dist/2020`. That worked in JupyterLab, but broke
in VS Code's notebook webview for two independent reasons:

- anywidget delivers `_esm` as a plain string and the front end runs it from
  a `blob:`/`data:` URL, which has no real path — a *relative* import like
  `./ajv2020.js` can't resolve from there either, so splitting Ajv into a
  sibling file doesn't work.
- VS Code's notebook webview CSP additionally blocks fetching third-party
  scripts, so even the original CDN import failed outright there (surfacing
  as `WidgetManager.loadClass` throwing with no further detail).

The only import that survives both constraints is none at all: `npm run
build` bundles `editor.src.js` and `ajv` into one dependency-free ESM
module. Rebuild after editing `editor.src.js` or bumping the `ajv` version,
and commit the resulting `static/editor.js`.

## plotly for the 3D views

The results viewer does not fetch plotly from a CDN either: `static/plotly3d.js`
ships with the package and Python sends it as a message buffer the first time a
3D view is opened (`receivePlotly()` in `view3d.js` imports it from a `blob:`
URL, the same way anywidget loads the widget itself). The project editor still
imports plotly from esm.sh, see the ROADMAP follow-up.
