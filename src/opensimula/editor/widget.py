"""Interactive project editor widget.

Built on anywidget, so the same widget works in Jupyter (Lab, Notebook 7,
VS Code, Colab) and in Marimo, which supports anywidget natively::

    editor = project.editor()          # Jupyter: display it directly
    editor = mo.ui.anywidget(editor)   # Marimo

The whole project document lives in a single ``value`` traitlet, which is what
makes it reactive in Marimo and observable in Jupyter.
"""

import pathlib

import anywidget
import traitlets

from opensimula.editor.schema import project_json_schema

_STATIC = pathlib.Path(__file__).parent / "static"

_cached_schema = None


def default_schema():
    """The project JSON Schema, built once and reused.

    Generating it instantiates one of every component type, so it is worth
    keeping: the result only changes if the component classes change.
    """
    global _cached_schema
    if _cached_schema is None:
        _cached_schema = project_json_schema()
    return _cached_schema


class ProjectEditor(anywidget.AnyWidget):
    """Tree editor for an OpenSimula project document.

    Args:
        project (Project, optional): project to load. Its definition is read
            with write_dict(); the widget does not write back to it.
        value (dict, optional): project document, if no project is given.
        schema (dict, optional): JSON Schema to validate against. Defaults to
            the schema generated from the component classes.

    Attributes:
        value (dict): the edited document. Reassign it to change what is shown,
            never mutate it in place: traitlets detects changes by identity.
        errors (list): validation errors reported by the editor, each with
            "path", "message" and "severity".
    """

    _esm = _STATIC / "editor.js"
    _css = _STATIC / "editor.css"

    value = traitlets.Dict({}).tag(sync=True)
    schema = traitlets.Dict({}).tag(sync=True)
    errors = traitlets.List([]).tag(sync=True)

    def __init__(self, project=None, value=None, schema=None, **kwargs):
        if value is None:
            value = project.write_dict() if project is not None else {}
        if schema is None:
            schema = default_schema()
        super().__init__(value=value, schema=schema, **kwargs)
        self._project_ = project

    @property
    def project(self):
        """The project the document was read from, if any."""
        return self._project_

    def is_valid(self):
        """True if the document currently satisfies the schema."""
        return len(self.errors) == 0

    def error_report(self):
        """Validation errors as readable lines."""
        lines = []
        for error in self.errors:
            path = "/".join(str(part) for part in error.get("path", []))
            lines.append(f"/{path}: {error.get('message', '')}")
        return lines
