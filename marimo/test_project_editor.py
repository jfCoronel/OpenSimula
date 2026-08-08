# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.3",
#     "opensimula",
# ]
#
# [tool.uv.sources]
# # This checkout, not the release on PyPI: editor() is not published yet.
# opensimula = { path = "../", editable = true }
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    ## Probando el Editor en marimo
    """)
    return


@app.cell
def _():
    import marimo as mo
    import opensimula as osm

    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("proyecto")
    # Relative to this notebook, not to wherever marimo was launched from.
    pro.read_json(str(mo.notebook_dir() / ".." / "test" / "test_project_1.json"))

    editor = mo.ui.anywidget(pro.editor())
    editor
    return editor, mo


@app.cell
def _(editor, mo):
    # mo.ui.anywidget exposes the synced traits: value, schema and errors.
    _doc = editor.value["value"]
    _errors = editor.value["errors"]

    mo.md(f"""
    **{_doc["name"]}** — {len(_doc["components"])} components

    {"No problems" if not _errors else
     chr(10).join("- `/" + "/".join(str(p) for p in e["path"]) + "`: " + e["message"]
                  for e in _errors)}
    """)
    return


if __name__ == "__main__":
    app.run()
