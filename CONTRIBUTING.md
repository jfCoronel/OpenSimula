# Contributing to OpenSimula

Thanks for your interest in OpenSimula. Contributions of any size are welcome: bug reports,
fixes, new components, validation cases, examples and documentation.

## Reporting bugs and proposing features

Open an [issue](https://github.com/jfCoronel/OpenSimula/issues) using the bug report or
feature request form. For bugs, a minimal project (as a Python dict or JSON) that reproduces
the problem is the most useful thing you can include.

If you plan to implement something non-trivial (a new component, a change to an existing
model), open an issue first to discuss the approach before writing the code.

## Setting up a development environment

OpenSimula uses [uv](https://docs.astral.sh/uv/) and requires Python 3.12 or later.

```bash
git clone https://github.com/jfCoronel/OpenSimula.git
cd OpenSimula
uv sync              # creates .venv with all dependencies, including dev ones
uv run pytest test   # should be all green
```

## Workflow

1. Create a branch from `main` (or fork the repository if you do not have write access).
2. Make your changes, with tests.
3. Run `uv run pytest test` locally.
4. Open a pull request against `main` and fill in the checklist of the template.

Every pull request runs the test suite on Python 3.12 and 3.13 and checks that the
documentation builds. It must be green before it is merged.

### Changes that modify simulation results

OpenSimula is validated against ASHRAE 140 (notebooks in `ASHRAE_140/`). If your change
alters numerical results:

- Update the reference values of the affected tests in `test/` and say in the pull request
  how much they changed.
- Re-run the ASHRAE 140 notebooks related to the change and check the results stay within
  the range of the reference programs.

## Code conventions

- Follow the style of the surrounding code: component classes are named `Like_this`,
  parameters and variables `like_this`.
- Every parameter has a unit (when it has one) and `min`/`max` limits when they make sense.
- Errors detected in a component's `check()` are returned as `Message(..., "ERROR")`; do not
  raise exceptions for invalid user input.

## Adding a new component

1. Create `src/opensimula/components/My_component.py` with a class inheriting from
   `Component`.
2. In `__init__()`, set `type` and `description`, declare parameters with `add_parameter()`
   and output variables with `add_variable()`.
3. Implement `check()` to validate the parameters, calling `super().check()` first.
4. Implement the simulation methods it needs: `pre_simulation()`, `pre_iteration()`,
   `iteration()`, `post_iteration()`, `post_simulation()`.
5. Import it in `src/opensimula/components/__init__.py`. This makes it available to
   `read_dict()`/`read_json()` and to the project editor, whose JSON Schema is generated from
   the component classes.
6. If it must run at a specific point of each time step, add it to `DEFAULT_COMPONENTS_ORDER`
   in the same file.
7. Add tests in `test/test_My_component.py`.
8. Document its parameters and variables in the corresponding `mkdocs/component_list_*.md`.

`CLAUDE.md` has an overview of the architecture (components, parameters, variables and the
simulation loop) that is a good starting point.

## Documentation

The documentation source is in `mkdocs/` and the generated site in `docs/`, which GitHub
Pages publishes at <https://opensimula.jfcoronel.org>.

```bash
uv run mkdocs serve          # live preview at http://127.0.0.1:8000
uv run mkdocs build --clean  # regenerate docs/
```

Edit only the files in `mkdocs/`; `docs/` is regenerated.

## The project editor widget

`src/opensimula/editor/static/editor.js` is generated: edit
`src/opensimula/editor/vendor/editor.src.js` and rebuild it as explained in
`src/opensimula/editor/vendor/README.md`.

## Releasing a new version (maintainers)

1. Update the version number in `pyproject.toml` and `CITATION.cff` (`version` and
   `date-released`), and run `uv sync` so that `uv.lock` picks it up.
2. Add an entry to the release notes in `mkdocs/index.md` and update its
   "Current Version" line.
3. Run all the tests: `uv run pytest test`.
4. Regenerate the documentation: `uv run mkdocs build --clean`.
5. Commit with the version as message (e.g. `Version 0.8.8: ...`) and push.
6. Publish to PyPI:

   ```bash
   rm -rf dist
   uv build
   uv publish   # username: __token__, password: a PyPI API token
   ```

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE) of the project.
