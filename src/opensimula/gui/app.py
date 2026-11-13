"""OpenSimula app: open, edit, simulate and look at the results of a project.

A marimo notebook run as an app by `opensimula gui [project.json]`. It puts
together the widgets that also work in notebooks: the project editor (with its
3D and graph views) and the results viewer.

Each widget is shown by the cell that creates it, and no other cell names the
wrapped element: a cell that names a marimo UI element runs again whenever its
value changes, that is on every edit. The other cells use the plain widget
(`editor_widget`), which marimo does not follow.
"""

import marimo

__generated_with = "0.19.2"
app = marimo.App(width="full", app_title="OpenSimula")


@app.cell(hide_code=True)
def _():
    import json
    import pathlib
    import time

    import marimo as mo

    import opensimula as osm
    from opensimula.editor import format_errors

    return format_errors, json, mo, osm, pathlib, time


@app.cell(hide_code=True)
def _(mo, osm, pathlib):
    def open_project(path=None):
        """A new simulation holding the project read from path, or an empty one.

        Relative file names inside the project (weather files, data files) are
        resolved from the working folder, the one the app was started from.
        """
        sim = osm.Simulation()
        sim.console_print = False
        if path is None:
            project = sim.new_project("New project")
            return {"sim": sim, "project": project, "path": None, "problems": []}
        path = pathlib.Path(path)
        project = sim.new_project(path.stem)
        problems = []
        try:
            project.read_json(str(path))
        except Exception as error:  # a file that is not a project
            problems.append(f"Could not read {path.name}: {error}")
        problems += [
            f"{m.level}: {m.text}" for m in sim.message_list() if m.level in ("ERROR", "WARNING")
        ]
        return {"sim": sim, "project": project, "path": path, "problems": problems}

    def problem_list(lines, kind="warn"):
        """A callout with one line per problem."""
        items = "\n".join(f"- {line}" for line in lines)
        return mo.callout(mo.md(items), kind=kind)

    return open_project, problem_list


@app.cell(hide_code=True)
def _(mo, open_project, pathlib):
    _arg = mo.cli_args().get("project")
    get_session, set_session = mo.state(open_project(pathlib.Path(_arg) if _arg else None))
    return get_session, set_session


@app.cell(hide_code=True)
def _(mo, osm, pathlib):
    browser = mo.ui.file_browser(
        initial_path=pathlib.Path.cwd(),
        filetypes=[".json"],
        multiple=False,
        label="Project file (JSON)",
    )
    open_button = mo.ui.run_button(label="Open")
    new_button = mo.ui.run_button(label="New project")
    mo.vstack([
        mo.md(f"# OpenSimula <small>{osm.VERSION}</small>"),
        mo.accordion({
            "Open or create a project": mo.vstack([
                browser,
                mo.hstack([open_button, new_button], justify="start"),
            ]),
        }),
        mo.md(f"<small>Working folder: `{pathlib.Path.cwd()}`. Relative file names "
              "in the project (weather, data) are read from it.</small>"),
    ])
    return browser, new_button, open_button


@app.cell(hide_code=True)
def _(browser, mo, new_button, open_button, open_project, set_session):
    if open_button.value:
        if browser.value:
            set_session(open_project(browser.path(0)))
        else:
            mo.output.replace(mo.callout("Choose a project file first.", kind="warn"))
    elif new_button.value:
        set_session(open_project(None))
    return


@app.cell(hide_code=True)
def _(get_session, mo, problem_list):
    session = get_session()
    editor_widget = session["project"].editor()
    _name = session["project"].parameter("name").value
    _where = f"`{session['path']}`" if session["path"] else "not saved yet"
    mo.vstack([
        mo.md(f"## {_name}\n<small>{_where}</small>"),
        problem_list(session["problems"]) if session["problems"] else mo.md(""),
        mo.ui.anywidget(editor_widget),
    ])
    return editor_widget, session


@app.cell(hide_code=True)
def _(mo, session):
    save_path = mo.ui.text(
        value=str(session["path"]) if session["path"] else "project.json",
        label="Save as",
        full_width=True,
    )
    save_button = mo.ui.run_button(label="Save")
    simulate_button = mo.ui.run_button(label="Simulate", kind="success")
    mo.hstack([simulate_button, save_path, save_button], justify="start", align="end", widths=[0, 1, 0])
    return save_button, save_path, simulate_button


@app.cell(hide_code=True)
def _(editor_widget, json, mo, pathlib, save_button, save_path, session):
    mo.stop(not save_button.value)
    _path = pathlib.Path(save_path.value).expanduser()
    try:
        with open(_path, "w", encoding="utf-8") as _file:
            json.dump(editor_widget.value, _file, indent=4, ensure_ascii=False)
    except OSError as _error:
        mo.output.replace(mo.callout(f"Could not save {_path}: {_error}", kind="danger"))
    else:
        session["path"] = _path
        _errors = editor_widget.validate()
        _note = f" It has {len(_errors)} problems, marked in the editor." if _errors else ""
        mo.output.replace(mo.callout(f"Saved to `{_path}`.{_note}", kind="warn" if _errors else "success"))
    return


@app.cell(hide_code=True)
def _(
    editor_widget,
    format_errors,
    mo,
    problem_list,
    results_widget,
    session,
    simulate_button,
    time,
):
    mo.stop(not simulate_button.value)
    _project = session["project"]
    _sim = session["sim"]
    _first = len(_sim.message_list())
    # the project is rebuilt from the document, with every edit in it
    _errors = editor_widget.apply()
    if _errors and isinstance(_errors[0], dict):
        _out = problem_list(format_errors(_errors), kind="danger")
    elif _errors:
        _out = problem_list([m.text for m in _errors], kind="danger")
    else:
        _n = _project.parameter("n_time_steps").value
        _start = time.perf_counter()
        # a hundred updates at most: each one is a message to the browser
        _every = max(1, _n // 100)
        with mo.status.progress_bar(
            total=_n,
            title=f"Simulating {_project.parameter('name').value}",
            subtitle=f"{_n} time steps",
            remove_on_exit=True,
        ) as _bar:

            def _progress(step, n):
                if step % _every == 0 or step == n:
                    _bar.update(increment=step - _bar.current)

            _project.simulate(progress=_progress)
        _elapsed = time.perf_counter() - _start
        # same viewer, same variables and settings: the new values are drawn
        results_widget.refresh()
        _notes = [
            f"{m.level}: {m.text}" for m in _sim.message_list()[_first:] if m.level in ("ERROR", "WARNING")
        ]
        _done = mo.callout(f"Simulated {_n} time steps in {_elapsed:.1f} s.", kind="success")
        _out = mo.vstack([_done, problem_list(_notes)]) if _notes else _done
    _out
    return


@app.cell(hide_code=True)
def _(mo, session):
    # one viewer per project, kept across simulations: Simulate refreshes it,
    # so the variables plotted, the frequency and the interval stay as they are
    results_widget = session["project"].results(height=700)
    mo.vstack([mo.md("## Results"), mo.ui.anywidget(results_widget)])
    return (results_widget,)


if __name__ == "__main__":
    app.run()
