"""Serve the current folder for local viewing, with caching disabled so edits
to the pages and data files always show up on reload.

Usage: python3 tools/serve.py [port]   (default 8385; run from the kit, or from a
       repository that holds the kit as kit/)
"""
import http.server
import sys
from functools import partial
from pathlib import Path


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 64   # pages fetch a dozen files at once; the default 5 drops connections


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8385
    root = Path.cwd()
    handler = partial(NoCacheHandler, directory=str(root))
    print(f"Serving {root} at http://localhost:{port}/")
    Server(("", port), handler).serve_forever()
