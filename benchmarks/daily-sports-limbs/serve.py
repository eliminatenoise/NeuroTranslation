"""Open a local browser interface to the trained five-placement NeuroTranslate checkpoint."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Lock
import webbrowser

from broader_learner import configure_cpu_runtime
from model import HERE, PARTS, digest, load_checkpoint
from predict import forecast

ASSETS = {"/": ("viewer.html", "text/html; charset=utf-8"),
          "/viewer.js": ("viewer.js", "text/javascript; charset=utf-8"),
          "/viewer.css": ("viewer.css", "text/css; charset=utf-8")}
MAX_REQUEST_BYTES = 32768


def local_server(port):
    path = HERE / "model.pt"
    if digest(path) != json.loads((HERE / "results.json").read_text())["checkpoint_sha256"]:
        raise ValueError("Different model checkpoint")
    model, state = load_checkpoint(path)
    examples = json.loads((HERE / "recorded-examples.json").read_text())
    if examples["checkpoint_sha256"] != digest(path):
        raise ValueError("Recorded examples belong to a different checkpoint")
    lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, content_type, body):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def reply(self, obj, status=200):
            self.send(status, "application/json", json.dumps(obj, allow_nan=False).encode())

        def valid_host(self):
            expected = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") == expected:
                return True
            self.reply({"error": "Invalid local server address"}, 421)
            return False

        def do_GET(self):
            if not self.valid_host():
                return
            if self.path == "/examples.json":
                self.reply(examples)
            elif self.path in ASSETS:
                name, mime = ASSETS[self.path]
                self.send(200, mime, (HERE / name).read_bytes())
            else:
                self.reply({"error": "Unknown path"}, 404)

        def do_POST(self):
            if not self.valid_host():
                return
            if self.path != "/forecast":
                self.reply({"error": "Unknown path"}, 404)
                return
            expected = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Origin") != expected:
                self.reply({"error": "Open the forecast page on this local server"}, 403)
                return
            if self.headers.get_content_type() != "application/json":
                self.reply({"error": "Expected a JSON request"}, 415)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_REQUEST_BYTES:
                    self.reply({"error": "Expected one 16-sample sensor window"}, 413)
                    return
                request = json.loads(self.rfile.read(length))
                if type(request) is not dict or set(request) != {"selected", "record"}:
                    raise ValueError("Select a body part and supply a sensor recording")
                part, record = request["selected"], request["record"]
                if type(part) is not str or part not in PARTS:
                    raise ValueError("Unknown sensor placement")
                with lock:
                    result = forecast(model, state, record, part)
                known = examples["examples"][part]
                measured = known["measured_target"] if record == known["input"] else None
                self.reply({"forecast": result, "measured_target": measured})
            except (KeyError, TypeError, ValueError, OverflowError, RuntimeError, FloatingPointError) as err:
                self.reply({"error": str(err)}, 422)

        def log_message(self, format, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0, help="Local port (default: automatic)")
    parser.add_argument("--no-browser", action="store_true", help="Print the address without opening it")
    args = parser.parse_args()
    configure_cpu_runtime(1, 1, True)
    with local_server(args.port) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Open {url}\nPress Ctrl+C to close.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
