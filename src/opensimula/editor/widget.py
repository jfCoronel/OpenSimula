"""Interactive project editor widget.

Built on anywidget, so the same widget works in Jupyter (Lab, Notebook 7,
VS Code, Colab) and in Marimo, which supports anywidget natively::

    editor = project.editor()          # Jupyter: display it directly
    editor = mo.ui.anywidget(editor)   # Marimo

The whole project document lives in a single ``value`` traitlet, which is what
makes it reactive in Marimo and observable in Jupyter.
"""

import copy
import pathlib

import anywidget
import traitlets

from opensimula.editor.schema import project_json_schema
from opensimula.editor.validation import format_errors, validate_document

_STATIC = pathlib.Path(__file__).parent / "static"


def _components_by_name(document):
    return {
        component.get("name"): component
        for component in document.get("components", [])
        if isinstance(component, dict)
    }


def structural_changes(previous, current):
    """Edits the project cannot absorb in place, described one per line.

    Renaming, adding or removing a component, or changing its type, all mean
    the project has to be rebuilt: components refer to each other by name and
    those references are resolved when the definition is loaded.

    Returns:
        list of str: empty when every edit is a plain change of value.
    """
    before = _components_by_name(previous)
    after = _components_by_name(current)
    changes = [f"added {name}" for name in after if name not in before]
    changes += [f"removed {name}" for name in before if name not in after]
    changes += [
        f"{name}: type is now {component.get('type')}"
        for name, component in after.items()
        if name in before and before[name].get("type") != component.get("type")
    ]
    return sorted(changes)


def value_changes(previous, current):
    """Parameters whose value changed, as (component name or None, key, value).

    None as the name means a parameter of the project itself.
    """
    changes = [
        (None, key, value)
        for key, value in current.items()
        if key != "components" and previous.get(key) != value
    ]
    before = _components_by_name(previous)
    for name, component in _components_by_name(current).items():
        old = before.get(name)
        if old is None:
            continue
        changes += [
            (name, key, value)
            for key, value in component.items()
            if key not in ("name", "type") and old.get(key) != value
        ]
    return changes

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
    geometry = traitlets.Dict({}).tag(sync=True)
    pending = traitlets.List([]).tag(sync=True)

    def __init__(self, project=None, value=None, schema=None, **kwargs):
        if value is None:
            value = project.write_dict() if project is not None else {}
        if schema is None:
            schema = default_schema()
        super().__init__(value=value, schema=schema, **kwargs)
        self._project_ = project
        # The document as the project currently holds it, to tell an edit that
        # can be applied in place from one that needs a rebuild.
        self._applied_ = copy.deepcopy(self.value)
        self.refresh_geometry()
        self.observe(self._value_edited_, names="value")
        self.on_msg(self._handle_message_)

    def refresh_geometry(self):
        """Reload the 3D view from the project.

        The 3D view shows the project, not the document being edited: geometry
        needs a built model, with references resolved and origins placed
        relative to the building, which the document alone does not give. So it
        follows apply(), not every keystroke.
        """
        self.geometry = self._project_.geometry_dict() if self._project_ else {}

    @property
    def project(self):
        """The project the document was read from, if any."""
        return self._project_

    def validate(self):
        """Schema errors of the current document, checked here in Python.

        Not the "errors" traitlet: that one is filled by the browser, so it is
        empty until the widget has been displayed, and reads as valid for any
        document when it never was.

        Returns:
            list of dict: one entry per problem, empty if the document is valid.
        """
        return validate_document(self.value, self.schema)

    def is_valid(self):
        """True if the document satisfies the schema."""
        return len(self.validate()) == 0

    def error_report(self):
        """Validation errors as readable lines."""
        return format_errors(self.validate())

    def apply(self, project=None):
        """Load the edited document into the project, replacing its contents.

        The document is the source of truth: rather than working out which
        parameters changed, the project is rebuilt from it. That is what keeps
        renames working, since components refer to each other by name and the
        references are resolved on load.

        The project is left untouched if the document does not satisfy the
        schema, so a half-applied definition cannot happen. Simulation results
        held by the previous components are dropped either way: the definition
        they came from is gone.

        Args:
            project (Project, optional): project to load into. Defaults to the
                one the document was read from.

        Returns:
            list: schema errors, if any, in which case nothing was applied.
                Otherwise the messages returned by Project.check().
        """
        target = project if project is not None else self._project_
        if target is None:
            raise ValueError("No project to apply to: build the editor from one")

        errors = self.validate()
        if errors:
            return errors

        target.clear()
        # A copy, so the parameters cannot end up aliasing the widget document.
        target.read_dict(copy.deepcopy(self.value))
        messages = target.check()
        if target is self._project_:
            self._applied_ = copy.deepcopy(self.value)
            self.pending = []
            self.refresh_geometry()
        return messages

    # ____________________ keeping the project in step ____________________

    def _value_edited_(self, change):
        """Put a plain change of value straight into the project.

        Changing a number does not need the project rebuilding: it is a local
        assignment that keeps every component object, and its results, alive.
        Renaming, adding or removing does need it, and those wait for apply();
        the pending list is what the editor shows to say so.
        """
        if self._project_ is None:
            return

        structural = structural_changes(self._applied_, self.value)
        if structural:
            self.pending = structural
            return
        self.pending = []

        # A value that does not satisfy the schema must not reach the project.
        # It stays in the document, the editor marks it, and it is applied when
        # it is corrected.
        if self.validate():
            return

        geometry_touched = False
        for name, key, value in value_changes(self._applied_, self.value):
            target = self._project_ if name is None else self._project_.component(name)
            if target is None or key not in target.parameter_dict():
                continue
            target.parameter(key).value = value
            geometry_touched = geometry_touched or hasattr(target, "get_polygon_3D")

        self._applied_ = copy.deepcopy(self.value)
        if geometry_touched:
            self.refresh_geometry()

    def _handle_message_(self, widget, content, buffers):
        """The Apply button. The frontend cannot call a method, only send."""
        if isinstance(content, dict) and content.get("type") == "apply":
            self.apply()
