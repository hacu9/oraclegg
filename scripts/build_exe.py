"""Build OracleGG as a standalone .exe for Windows.

Run ON WINDOWS (not WSL):
    uv run python scripts/build_exe.py

This creates dist/OracleGG.exe that bundles Python + all dependencies.
Friends can download and run it without installing anything.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def main():
    print("Building OracleGG .exe...")
    print()

    # Ensure PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "OracleGG",
        "--onefile",
        "--console",  # Keep console for server logs
        "--add-data", f"{PROJECT_ROOT / 'src' / 'oraclegg' / 'ui'};oraclegg/ui",
        "--add-data", f"{PROJECT_ROOT / '.env.example'};.",
        "--hidden-import", "oraclegg",
        "--hidden-import", "oraclegg.main",
        "--hidden-import", "oraclegg.api.routes",
        "--hidden-import", "oraclegg.game_loop.monitor",
        "--hidden-import", "oraclegg.recommender.tips",
        "--hidden-import", "oraclegg.recommender.builds",
        "--hidden-import", "oraclegg.recommender.rules.item_triggers",
        "--hidden-import", "oraclegg.recommender.rules.objective_rules",
        "--hidden-import", "oraclegg.recommender.rules.gold_lead_rules",
        "--hidden-import", "oraclegg.recommender.rules.power_spike_rules",
        "--hidden-import", "oraclegg.scouting.scout",
        "--hidden-import", "oraclegg.scouting.comp",
        "--hidden-import", "oraclegg.scouting.analyzer",
        "--hidden-import", "oraclegg.tracker.personal",
        "--hidden-import", "oraclegg.tracker.post_game",
        "--hidden-import", "oraclegg.riot.client",
        "--hidden-import", "oraclegg.riot.live_client",
        "--hidden-import", "oraclegg.static_data.manager",
        "--hidden-import", "oraclegg.db.engine",
        "--hidden-import", "oraclegg.db.models",
        "--hidden-import", "aiosqlite",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--paths", str(PROJECT_ROOT / "src"),
        str(PROJECT_ROOT / "launcher" / "oraclegg_entry.py"),
    ]

    print("Running PyInstaller...")
    print(f"  Command: {' '.join(cmd[:6])}...")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode == 0:
        exe_path = PROJECT_ROOT / "dist" / "OracleGG.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print()
            print(f"  Built: {exe_path}")
            print(f"  Size: {size_mb:.1f} MB")
            print()
            print("  Share this .exe with friends. They just need to:")
            print("  1. Put their Riot API key in a .env file next to the .exe")
            print("  2. Double-click OracleGG.exe")
        else:
            print("  Build succeeded but .exe not found at expected path")
    else:
        print(f"  Build failed with code {result.returncode}")


if __name__ == "__main__":
    main()
