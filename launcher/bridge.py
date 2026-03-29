"""WSL Bridge: proxies League Live Client Data API as plain HTTP.

This runs on Windows. It connects to the Live Client API on localhost:2999
(which only accepts local connections) and re-serves it as HTTP on port 29990
so OracleGG running in WSL can reach it.

If OracleGG runs natively on Windows, this bridge is not needed.
"""

import http.server
import json
import ssl
import urllib.request

LISTEN_PORT = 29990
RIOT_URL = "https://127.0.0.1:2999"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            req = urllib.request.Request(f"{RIOT_URL}{self.path}")
            with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
                data = r.read()
                self.send_response(r.status)
                self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    s = http.server.HTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    print(f"OracleGG Bridge: http://0.0.0.0:{LISTEN_PORT} -> {RIOT_URL}")
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        s.server_close()
