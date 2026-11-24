"""Open the NeuroTranslate joint alpha demo on this computer."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import webbrowser

from joint_alpha.game_mount import GameMount
from joint_alpha.product import HERE, TOUCH_TASK, TOUCH_WEIGHTS, WEIGHTS, Product, examples

ASSETS = {
    "/": ("demo.html", "text/html; charset=utf-8"),
    "/outcome.js": ("outcome.js", "text/javascript; charset=utf-8"),
    "/demo.js": ("demo.js", "text/javascript; charset=utf-8"),
    "/demo.css": ("demo.css", "text/css; charset=utf-8"),
}


class Demo(BaseHTTPRequestHandler):
    def __init__(self, *args, product, catalog, game, **kwargs):
        self.product = product
        self.catalog = catalog
        self.game = game
        super().__init__(*args, **kwargs)

    def reply(self, status, body, media="application/json; charset=utf-8", policy=None):
        data = body if isinstance(body, bytes) else json.dumps(body, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", policy or "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

    def local_request(self):
        address = "127.0.0.1:" + str(self.server.server_port)
        if self.headers.get("Host") == address and self.headers.get("Origin", "http://" + address) == "http://" + address:
            return True
        self.reply(403, {"error": "Use the local address printed by the launcher."})
        return False

    def do_GET(self):
        if not self.local_request():
            return
        if self.game and self.path.startswith("/game/"):
            asset = self.game.get(self.path)
            if asset is None:
                self.reply(404, {"error": "This file is outside the game inventory."})
            else:
                data, media, policy = asset
                self.reply(200, data, media, policy)
            return
        if self.path in ASSETS:
            file, media = ASSETS[self.path]
            self.reply(200, (HERE / file).read_bytes(), media)
        elif self.path == "/api/tasks":
            self.reply(200, self.catalog)
        else:
            self.reply(404, {"error": "Unknown address."})

    def do_POST(self):
        if not self.local_request():
            return
        if self.path != "/api/forecast":
            self.reply(404, {"error": "Unknown address."})
            return
        if self.headers.get_content_type() != "application/json":
            self.reply(415, {"error": "Send JSON input."})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 2_000_000:
                self.reply(413, {"error": "Choose one input under 2 MB."})
                return
            record = json.loads(self.rfile.read(size))
            if not isinstance(record, dict) or not isinstance(record.get("X"), list) or len(record["X"]) != 1:
                raise ValueError("The browser takes one history at a time. Use predict.py for a batch.")
            self.reply(200, self.product.predict(record))
        except (KeyError, ValueError, TypeError, OverflowError, IndexError, RecursionError) as exc:
            self.reply(400, {"error": str(exc)})

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true", help="print the address without opening a browser")
    parser.add_argument("--game", metavar="DIR", help="open a locally supplied game directory with a joint-game.json inventory")
    parser.add_argument("--touch", action="store_true", help="run all eight tasks with the experimental touch checkpoint")
    args = parser.parse_args()
    try:
        game = GameMount(args.game) if args.game else None
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    product = Product(TOUCH_WEIGHTS if args.touch else WEIGHTS)
    cases = examples(with_touch=product.with_touch)
    descriptions = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))
    if product.with_touch:
        descriptions[TOUCH_TASK] = json.loads((HERE / "touch" / "display.json").read_text(encoding="utf-8"))
    if set(descriptions) != set(cases) or set(cases) != set(product.model.tasks):
        raise ValueError("The model, examples and display labels must describe the same tasks.")
    catalog = {"game_mounted": bool(game), "initial_task": TOUCH_TASK if product.with_touch else None, "model": product.title, "checkpoint_sha256": product.digest,
               "tasks": {k: {"schema": v, "description": descriptions[k], "example": cases[k]}
                         for k, v in product.catalog().items()}}
    handler = partial(Demo, product=product, catalog=catalog, game=game)
    with HTTPServer(("127.0.0.1", 0), handler) as server:
        url = "http://127.0.0.1:" + str(server.server_port)
        if game:
            url += "/game/"
        print(f"{product.title}\n{url}\nKeep this window open. Press Ctrl+C to stop.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
