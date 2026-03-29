"""Build a distributable zip of OracleGG for Windows.

Creates oraclegg-dist.zip with everything needed to run on a fresh Windows machine.
Friends just need Python 3.11+ installed, then run OracleGG_Windows.bat.
"""

import os
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DIST_NAME = "oraclegg-dist.zip"

# Files/dirs to include
INCLUDE = [
    "pyproject.toml",
    ".env.example",
    ".gitignore",
    "src/",
    "scripts/seed_static_data.py",
    "scripts/run_pipeline.py",
    "scripts/import_history.py",
    "scripts/build_windows_exe.bat",
    "launcher/",
    "docs/setup-guide.md",
]

# Files/dirs to exclude
EXCLUDE = {
    "__pycache__",
    ".venv",
    "data",
    ".git",
    ".env",
    "node_modules",
    ".ruff_cache",
}


def should_include(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE:
            return False
    return True


def main():
    dist_path = PROJECT_ROOT / DIST_NAME
    count = 0

    with zipfile.ZipFile(dist_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pattern in INCLUDE:
            full = PROJECT_ROOT / pattern
            if full.is_file():
                if should_include(full.relative_to(PROJECT_ROOT)):
                    arcname = f"oraclegg/{full.relative_to(PROJECT_ROOT)}"
                    zf.write(full, arcname)
                    count += 1
            elif full.is_dir():
                for root, dirs, files in os.walk(full):
                    # Filter excluded dirs
                    dirs[:] = [d for d in dirs if d not in EXCLUDE]
                    for f in files:
                        fp = Path(root) / f
                        rel = fp.relative_to(PROJECT_ROOT)
                        if should_include(rel):
                            zf.write(fp, f"oraclegg/{rel}")
                            count += 1

        # Include .env.example as .env so it works out of the box
        env_example = PROJECT_ROOT / ".env.example"
        if env_example.exists():
            zf.write(env_example, "oraclegg/.env")
            count += 1

        # Add a README for the zip
        readme = """OracleGG - League of Legends Real-Time Coach
=============================================

QUICK START (Windows):
1. Install Python 3.11+ from https://python.org (check "Add to PATH")
2. Extract this zip anywhere
3. Edit oraclegg\\.env.example -> rename to .env -> set your RIOT_API_KEY
   Get a key at: https://developer.riotgames.com/
4. Double-click: oraclegg\\launcher\\OracleGG_Windows.bat
5. Open a League game. OracleGG detects it automatically.

OR run the installer:
   powershell -ExecutionPolicy Bypass -File oraclegg\\launcher\\install.ps1

FULL DOCS: oraclegg\\docs\\setup-guide.md
"""
        zf.writestr("README.txt", readme)
        count += 1

    size_mb = dist_path.stat().st_size / (1024 * 1024)
    print(f"Built {dist_path.name}: {count} files, {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
