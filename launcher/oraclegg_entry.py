"""PyInstaller entry point for OracleGG.

Bundled into the .exe. Handles first-run setup, starts server, opens browser.
"""

import multiprocessing
import os
import sys
import time
import webbrowser


def get_app_dir():
    """Get the directory where the .exe lives (or the project root in dev)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def first_run_setup(app_dir):
    """Check if first run — seed static data and create .env."""
    db_path = os.path.join(app_dir, "data", "oraclegg.db")
    env_path = os.path.join(app_dir, ".env")
    env_example = os.path.join(app_dir, ".env.example")

    # Check .env
    if not os.path.exists(env_path):
        if os.path.exists(env_example):
            import shutil
            shutil.copy(env_example, env_path)
            print("  [!] Created .env from template.")
            print("  [!] Edit .env and set your RIOT_API_KEY before using.")
            print("      Get one at: https://developer.riotgames.com/")
            print()

    # Check if DB needs seeding
    if not os.path.exists(db_path):
        print("  [..] First run — downloading champion and item data...")
        try:
            import asyncio
            from oraclegg.db.engine import init_db
            from oraclegg.static_data.manager import seed_all
            asyncio.run(init_db())
            asyncio.run(seed_all())
            print("  [OK] Data ready.")
        except Exception as e:
            print(f"  [!] Data seed failed: {e}")
            print("      You can run this manually later.")
        print()


def enable_live_client_api():
    """Enable the Live Client Data API in League's config if not already."""
    cfg_paths = [
        r"C:\Riot Games\League of Legends\Config\game.cfg",
        r"D:\Riot Games\League of Legends\Config\game.cfg",
    ]
    for cfg in cfg_paths:
        if os.path.exists(cfg):
            try:
                with open(cfg, "r") as f:
                    content = f.read()
                if "EnableReplayApi" not in content:
                    content = content.replace("[General]", "[General]\nEnableReplayApi=1", 1)
                    with open(cfg, "w") as f:
                        f.write(content)
                    print("  [OK] Enabled Live Client Data API in League config.")
            except Exception:
                pass


def run_server(port, app_dir):
    os.environ.setdefault("DB_PATH", os.path.join(app_dir, "data", "oraclegg.db"))
    os.chdir(app_dir)
    from oraclegg.main import app
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main():
    port = 8000
    app_dir = get_app_dir()

    print()
    print("  ====================================")
    print("  OracleGG - League of Legends Coach")
    print("  ====================================")
    print()

    # Set working directory
    os.chdir(app_dir)
    os.environ.setdefault("DB_PATH", os.path.join(app_dir, "data", "oraclegg.db"))

    # First run setup
    first_run_setup(app_dir)
    enable_live_client_api()

    # Start server
    print("  Starting server...")
    server = multiprocessing.Process(target=run_server, args=(port, app_dir), daemon=True)
    server.start()

    # Wait for server
    import httpx
    for _ in range(40):
        try:
            httpx.get(f"http://127.0.0.1:{port}/api/stats", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    url = f"http://127.0.0.1:{port}"
    print(f"  Running at {url}")
    print()

    # Try native window, fall back to browser
    try:
        import webview
        print("  Opening native window...")
        webview.create_window(
            title="OracleGG",
            url=f"{url}/in-game",
            width=960,
            height=750,
            min_size=(700, 500),
            on_top=True,
            text_select=False,
        )
        webview.start()  # Blocks until window closed
    except ImportError:
        print("  Opening browser...")
        webbrowser.open(url)
        print("  OracleGG is running. Close this window to stop.")
        print()
        try:
            server.join()
        except KeyboardInterrupt:
            pass

    # Cleanup
    print("\n  Shutting down...")
    server.terminate()
    server.join(timeout=3)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
