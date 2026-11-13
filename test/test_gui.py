"""The `opensimula gui` command and the app it runs."""

import importlib.util
import pathlib
import sys

import pytest

from opensimula import gui

REPO = pathlib.Path(__file__).resolve().parents[1]
CASE_600 = REPO / "ASHRAE_140" / "LOAD_TEST" / "cases" / "case_600.json"


def test_command_needs_a_subcommand(capsys):
    with pytest.raises(SystemExit):
        gui.main([])


def test_missing_project_file(capsys, tmp_path):
    assert gui.run_gui(str(tmp_path / "nothing.json")) == 1
    assert "No such file" in capsys.readouterr().err


def test_without_marimo(monkeypatch, capsys):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert gui.run_gui() == 1
    assert "opensimula[gui]" in capsys.readouterr().err


def _run_app(monkeypatch, argv, cwd):
    """Run the cells of the app as a script; buttons are not pressed."""
    pytest.importorskip("marimo")
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", argv)
    spec = importlib.util.spec_from_file_location("opensimula_gui_app", gui.APP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, defs = module.app.run()
    return defs


def test_app_opens_the_project(monkeypatch):
    defs = _run_app(monkeypatch, ["app.py", "--project", str(CASE_600)], CASE_600.parents[1])
    session = defs["session"]
    assert session["problems"] == []
    assert session["project"].parameter("name").value == "Case 600"
    # the editor holds the document of the project, ready to be simulated
    editor = defs["editor_widget"]
    assert editor.project is session["project"]
    assert any(c["type"] == "File_met" for c in editor.value["components"])
    assert editor.is_valid()


def test_app_starts_empty(monkeypatch, tmp_path):
    defs = _run_app(monkeypatch, ["app.py"], tmp_path)
    assert defs["session"]["path"] is None
    assert defs["editor_widget"].value["components"] == []


def test_app_reports_a_bad_file(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    defs = _run_app(monkeypatch, ["app.py", "--project", str(bad)], tmp_path)
    assert any("Could not read bad.json" in p for p in defs["session"]["problems"])
