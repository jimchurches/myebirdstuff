#!/usr/bin/env python3
"""
Copy eBirdChecklistNameFromGPS.py from the repo to the live install location.
Run on demand when you want to deploy changes. Path is in config_secret.py (or config_template.py).
Creates a timestamped backup of the existing script before overwriting; keeps 12 backups, prunes older ones.
"""
import shutil
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE = SCRIPT_DIR / "eBirdChecklistNameFromGPS.py"
MAX_BACKUPS = 12


def _load_destination():
    """Load DEPLOY_DESTINATION from config_secret or config_template."""
    try:
        try:
            from config_secret import DEPLOY_DESTINATION
        except ImportError:
            from config_template import DEPLOY_DESTINATION
        return Path(DEPLOY_DESTINATION)
    except ImportError as e:
        print(f"ERROR: Add DEPLOY_DESTINATION to config_secret.py (or config_template.py): {e}")
        raise SystemExit(1)


def main():
    if not SOURCE.exists():
        print(f"ERROR: Source not found: {SOURCE}")
        return 1

    dest = _load_destination()
    dest_dir = dest.parent
    dest_stem = dest.stem  # eBirdChecklistNameFromGPS
    dest_suffix = dest.suffix  # .py

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Backup existing file before overwriting
    if dest.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = dest_dir / f"{dest_stem}.{ts}.backup{dest_suffix}"
        shutil.copy2(dest, backup_path)
        print(f"Backed up to {backup_path.name}")

    shutil.copy2(SOURCE, dest)
    print(f"Copied to {dest}")

    # Prune old backups: keep only the 12 most recent
    backups = sorted(
        dest_dir.glob(f"{dest_stem}.*.backup{dest_suffix}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[MAX_BACKUPS:]:
        old.unlink()
        print(f"Pruned old backup: {old.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
