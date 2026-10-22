"""Run the Python Iris model locally and open its browser interface."""

from __future__ import annotations

import argparse
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

from app import Handler, MODEL_PATH


ROOT = Path(__file__).resolve().parent
HTML = ROOT / "Iris_Classifier_Local.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="run the model service without opening the page")
    args = parser.parse_args()
    if not MODEL_PATH.is_file():
        parser.error("model.json is missing; run iris_classifier.py train first")
    if not HTML.is_file():
        parser.error("Iris_Classifier_Local.html is missing; run build_offline.py first")
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as error:
        if args.port != 8765:
            parser.error(f"The local model could not start on port {args.port}: {error}")
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_port
    print(f"Python model ready at http://127.0.0.1:{port}", flush=True)
    print(f"Browser page: {HTML}", flush=True)
    print("Keep this window open while you use the classifier. Press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Thread(target=webbrowser.open_new_tab, args=(f"{HTML.as_uri()}?port={port}",), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
