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


def test_project_folder(tmp_path):
    # next to its weather: the folder of the project
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "w.met").write_text("")
    project = tmp_path / "a" / "p.json"
    project.write_text('{"components": [{"type": "File_met", "file_name": "w.met"}]}')
    assert gui.project_folder(project, tmp_path) == project.parent
    # names relative to another folder (ASHRAE 140 cases): the current one
    assert gui.project_folder(CASE_600, CASE_600.parents[1]) == CASE_600.parents[1]
    # found nowhere, no files or not a project: the folder of the project
    lost = tmp_path / "a" / "lost.json"
    lost.write_text('{"components": [{"type": "File_met", "file_name": "none.met"}]}')
    assert gui.project_folder(lost, tmp_path) == lost.parent
    bad = tmp_path / "a" / "bad.json"
    bad.write_text("{ not json")
    assert gui.project_folder(bad, tmp_path) == bad.parent


def test_app_reads_the_weather_next_to_the_project(monkeypatch, tmp_path):
    # started from another folder, the example finds its weather file
    folder = tmp_path / "examples"
    assert gui.copy_examples(str(folder)) == 0
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    defs = _run_app(monkeypatch, ["app.py", "--project", str(folder / "06_dx_system.json")],
                    elsewhere)
    assert defs["session"]["problems"] == []
    assert pathlib.Path.cwd() == folder.resolve()
