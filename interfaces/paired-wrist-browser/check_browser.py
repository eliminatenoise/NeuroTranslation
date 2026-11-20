"""Run source-bound parity and load tests in Chromium against a loopback-only origin."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

HERE = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    requests = []

    def do_GET(self):
        self.requests.append(self.path)
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b'<!doctype html><link rel="icon" href="data:,"><title>Wrist model QA</title>')
            return
        allowed = {"/check.mjs", "/fixtures.json", "/public/predictor.mjs", "/public/tensors.mjs",
                   *(f"/public/weights/{mode}.bin" for mode in ("motion", "emg", "full"))}
        if self.path not in allowed:
            self.send_error(404)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


SCRIPT = """
const done = arguments[arguments.length - 1];
(async () => {
  const {verify} = await import('./check.mjs');
  const cases = await (await fetch('./fixtures.json')).json();
  const start = performance.now();
  const {loadPairedPredictor} = await import('./public/predictor.mjs');
  const import_ms = performance.now() - start;
  const afterImport = performance.getEntriesByType('resource').map(e=>e.name);
  if(afterImport.some(s=>s.endsWith('.bin'))) throw Error('Weights fetched before model selection');
  const result = await verify(loadPairedPredictor, cases);
  const resources = performance.getEntriesByType('resource').map(e=>new URL(e.name));
  if(resources.some(url=>url.origin!==location.origin)) throw Error('Non-loopback resource');
  done({result, module_import_ms:import_ms, resources:resources.map(url=>url.pathname)});
})().catch(e=>done({error:String(e), stack:e.stack}));
"""


def request(base, path, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(base + path, data=data, headers={"Content-Type": "application/json"}, method=method)
    with urlopen(req, timeout=30) as response:
        return json.load(response)["value"]


def run():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(HERE)))
    host = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    try:
        with tempfile.TemporaryDirectory() as profile, subprocess.Popen(
            ["chromedriver", f"--port={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) as driver:
            session = None
            try:
                for attempt in range(100):
                    try:
                        request(base, "/status")
                        break
                    except URLError:
                        if driver.poll() is not None or attempt == 99:
                            raise
                        time.sleep(.05)
                opts = {"browserName": "chrome", "goog:chromeOptions": {"args": [
                    "--headless=new", "--disable-background-networking", "--disable-component-update",
                    "--no-first-run", f"--user-data-dir={profile}",
                    "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1"]}}
                info = request(base, "/session", {"capabilities": {"alwaysMatch": opts}})
                session = "/session/" + info["sessionId"]
                request(base, session + "/url", {"url": host})
                result = request(base, session + "/execute/async", {"script": SCRIPT, "args": []})
                if "error" in result:
                    raise RuntimeError(result)
                if any(Handler.requests.count(f"/public/weights/{m}.bin") != 1 for m in ("motion", "emg", "full")):
                    raise RuntimeError(f"Expected exactly one asset request per selected fit: {Handler.requests}")
                result.update(chromium=info["capabilities"]["browserVersion"],
                              server_requests=Handler.requests, origin="127.0.0.1",
                              hostname_resolution="external hostnames disabled")
                return result
            finally:
                try:
                    if session:
                        request(base, session, method="DELETE")
                finally:
                    driver.terminate()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
