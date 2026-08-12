from __future__ import annotations

import importlib.util
import subprocess
import sys

from nimo.cli.common import config_from_args


def register(subparsers):
    parser = subparsers.add_parser("dashboard", help="Launch the Streamlit dashboard")
    parser.set_defaults(handler=run)


def run(args) -> int:
    if importlib.util.find_spec("streamlit") is None:
        print("Streamlit is not installed. Install dashboard dependencies with: pip install -e '.[dashboard]'")
        return 2
    config = config_from_args(args)
    app_path = config.paths.project_root / "dashboard" / "app.py"
    command = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    return subprocess.call(command, cwd=config.paths.project_root)
