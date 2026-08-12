#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nimo.application.container import ApplicationContainer
from nimo.application.services.user_service import UserService
from nimo.config.loader import ConfigManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/update the current schema for every user")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    config = ConfigManager.discover(project_root=args.project_root, data_root=args.data_root)
    users = UserService(config).list()
    for user in users:
        ApplicationContainer.for_user(
            user,
            project_root=config.paths.project_root,
            data_root=config.paths.data_root,
        )
        print(f"Initialised schema: {user}")
    print(f"Processed {len(users)} users.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
