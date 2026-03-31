"""PyInstaller entry point for OracleGG.

Bundled into the .exe. Starts server, opens browser/native window.
First-run setup (seeding, pipeline) is handled automatically by the server.
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


def ensure_env(app_dir):
    """Create .env from template if it doesn't exist."""
    env_path = os.path.join(app_dir, ".env")
    env_example = os.path.join(app_dir, ".env.example")

    if not os.path.exists(env_path) and os.path.exists(env_example):
        import shutil
        shutil.copy(env_example, env_path)
        print("  Created .env from template.")
        print("  Set your Riot API key in Settings after the app opens.")
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
                    print("  Enabled Live Client Data API in League config.")
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

    ensure_env(app_dir)
    enable_live_client_api()

    # Start server (auto-seeds DB and auto-runs pipeline on first run)
    print("  Starting server...")
    server = multiprocessing.Process(target=run_server, args=(port, app_dir), daemon=True)
    server.start()

    # Wait for server to be ready
    import httpx
    for _ in range(60):  # Up to 30s (first run seeds data)
        try:
            httpx.get(f"http://127.0.0.1:{port}/api/version", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    url = f"http://127.0.0.1:{port}"
    print(f"  Running at {url}")
    print()

    # Try native window, fall back to browser
    use_browser = False
    try:
        import webview
        print("  Opening native window...")
        webview.create_window(
            title="OracleGG",
            url=url,
            width=1100,
            height=800,
            min_size=(800, 600),
            on_top=False,
            text_select=False,
        )
        webview.start()  # Blocks until window closed
    except ImportError:
        use_browser = True
    except Exception as e:
        print(f"  Native window failed: {e}")
        print("  Tip: Install Edge WebView2 Runtime from https://developer.microsoft.com/en-us/microsoft-edge/webview2/")
        use_browser = True

    if use_browser:
        print("  Opening browser instead...")
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
