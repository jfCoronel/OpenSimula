"""Command line entry point: `opensimula gui [project.json]`.

Starts the OpenSimula app (gui/app.py, a marimo notebook) in the browser. It
needs marimo, installed with the "gui" extra: `pip install "opensimula[gui]"`.
"""

import argparse
import importlib.util
import pathlib
import subprocess
import sys

APP = pathlib.Path(__file__).parent / "app.py"


def main(argv=None):
    """Parse the command line and run the requested command."""
    parser = argparse.ArgumentParser(prog="opensimula", description="OpenSimula command line.")
    commands = parser.add_subparsers(dest="command", required=True)
    gui = commands.add_parser(
        "gui",
        help="open the app to edit, simulate and look at the results of a project",
        description="Open the OpenSimula app in the browser. Relative file names in the "
        "project (weather, data) are read from the folder the command is run from.",
    )
    gui.add_argument("project", nargs="?", help="project file (JSON) to open")
    gui.add_argument("-p", "--port", type=int, help="port of the app server")
    gui.add_argument("--headless", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)

    if args.command == "gui":
        return run_gui(args.project, port=args.port, headless=args.headless)
    return 0


def run_gui(project=None, port=None, headless=False):
    """Run the app with marimo, until the server is stopped (Ctrl+C).

    Args:
        project (str, optional): project file (JSON) opened at the start.
        port (int, optional): port of the server; marimo picks a free one if None.
        headless (bool, optional): do not open a browser. Defaults to False.

    Returns:
        int: exit code of the marimo server.
    """
    if importlib.util.find_spec("marimo") is None:
        print('The app needs marimo: pip install "opensimula[gui]"', file=sys.stderr)
        return 1
    if project is not None:
        path = pathlib.Path(project).expanduser().resolve()
        if not path.is_file():
            print(f"No such file: {project}", file=sys.stderr)
            return 1
    command = [sys.executable, "-m", "marimo", "run", str(APP)]
    if port is not None:
        command += ["--port", str(port)]
    if headless:
        command.append("--headless")
    if project is not None:
        command += ["--", "--project", str(path)]
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
