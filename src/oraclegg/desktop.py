"""Desktop app launcher using PyWebView.

Opens OracleGG in a native window instead of a browser tab.
Supports always-on-top mode for second monitor / overlay use.
"""

import multiprocessing
import sys
import time

import uvicorn

from oraclegg.config import settings


def run_server():
    """Run the FastAPI server in a subprocess."""
    uvicorn.run(
        "oraclegg.main:app",
        host=settings.host,
        port=settings.port,
        log_level="warning",
    )


def main():
    import webview

    base_url = f"http://{settings.host}:{settings.port}"

    server = multiprocessing.Process(target=run_server, daemon=True)
    server.start()

    import httpx
    for _ in range(30):
        try:
            httpx.get(f"{base_url}/api/stats", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    window = webview.create_window(
        title="OracleGG",
        url=f"{base_url}/in-game",
        width=900,
        height=700,
        min_size=(600, 400),
        on_top=True,  # Always on top for overlay use
        text_select=False,
    )

    # Start webview (blocks until window is closed)
    webview.start()

    # Cleanup
    server.terminate()
    server.join(timeout=3)


if __name__ == "__main__":
    main()
