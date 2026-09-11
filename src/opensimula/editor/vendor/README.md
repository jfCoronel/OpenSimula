# Building the editor widget

`static/editor.js` (what anywidget actually ships to the front end) is a
generated file. `editor.src.js` here is the source: edit that one, then
rebuild:

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
