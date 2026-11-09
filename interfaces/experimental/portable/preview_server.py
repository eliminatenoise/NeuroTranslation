"""NeuroTranslator portable interface SOURCE ONLY, not runtime admission.

This file has never been run as part of its authoring. Only an explicitly invoked
run_runtime loads the fixed future bundle. It does not launch the broader app.
Normal actor/lease/rights/current-holds/loaded-source/SourceFive-as-applicable and
model/runtime qualification remain separate. A command-line flag is no receipt.
"""
from __future__ import annotations

import argparse
import hashlib
from decimal import Decimal, DecimalException
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import struct
import sys
import time

MAX_BODY_BYTES = 1_500_000  # 1500 kB, decimal bytes, not 1500 KiB
READ_SECONDS = 10.0
WRITE_SECONDS = 5.0
MAX_REQUESTS = 1024
# Largest exact finite float32 integer; bound before decimal-to-integer conversion.
MAX_FLOAT32_INTEGER = ((1 << 24) - 1) << 104
SOURCE_SHA256 = "6cdaa3c9f6845bd3f0c31c45136f09ecc259049d1ea51fc327599c7e194a133c"
DISPLAY_GLOSSARY = {"revision": 28, "sha256": "c253cdfa96c3ca68877ae2f5af05322d9876952bef8bed5eb646928d3ec90041"}
SERIALIZED_GLOSSARY = {"revision": 5, "sha256": "17fadf58b0e550b1fc95732234dceb168dc0f399f08afcdd204e5e466898d235"}
# Lexical declarations only. No target/parent lookup occurs at module import.
MODELS = {
    "first60seconds": {
        "label": "First 60 seconds — direct model",
        "method": "direct_scratch_specialist",
        "run": "first60seconds:combined:direct_scratch_specialist",
        "weights": "artifacts/loco_multiregion/portable/first60seconds/model.weights.npz",
        "metadata": "artifacts/loco_multiregion/portable/first60seconds/model.architecture.json",
        "metadata_sha256": "355a1a1d40daea75417fce71ecf9b74116a266e7e8a733a424aa8b2a65425651",
        "weights_sha256": "291ad8bc31e7314b67439f0586379089886723c9d41bb9f88764691cbc12b022",
        "checkpoint_sha256": "179b732918c082efdc1761158e66cfdc98a5c482f10ffc4597fa1ea7ed2dbb0c",
        "virtual_input_basis_features": None,
        "supports_region_mask": False,
    },
    "full_training_partition": {
        "label": "Full training partition — adapted model",
        "method": "unfrozen_source_trunk",
        "run": "full_training_partition:combined:unfrozen_source_trunk",
        "weights": "artifacts/loco_multiregion/portable/full_training_partition/model.weights.npz",
        "metadata": "artifacts/loco_multiregion/portable/full_training_partition/model.architecture.json",
        "metadata_sha256": "6332dd535b4ee2550699ea0bd49917064b91f0117d84e6d8b4adcd59a64092ef",
        "weights_sha256": "6fe0ce0daa86a3b99223cc590a1b6ad5f17e25a64cbf16ab5570e6f2e3bfd017",
        "checkpoint_sha256": "1b7eb3abe283121c41f46024288d3808fbb66042a13db9d02f2aab28d3c3a5ad",
        "virtual_input_basis_features": 171,
        "supports_region_mask": True,
    },
}
CODE_PINS = {
    "neural/portable_loco.py": "53d7a5ad099c4be38f07585d872ffcceef9c0d7666677f4508de0a1342b61024",
    "neural/portable_numpy.py": "f184ec676c9ff970af309a076a18be333e2d784ea1e8ec8f5e0775381373203f",
    "neural/__init__.py": "c6bc41898427ef187c6c6692ba601e5ae62fd31980219f0a36bc43e153dc7a32",
    "requirements.numpy.txt": "887629097ef646c5fe67c4d2145e827946ddb8d56a455d95f69fd1e7b76492aa",
}
ORIGINS = ("entered", "simulated", "caller_declared_measured")
REQUIRED_FIELDS = {"request_id", "model", "counts", "source_sha256", "unit_ids",
                   "input_origin", "count_unit", "velocity_unit", "bin_seconds"}
# Decode-only errors from the pinned implementation; no path or exception leak.
DECODER_ERRORS = {
    "Expected numeric20-bin counts in the exact recording-specific feature layout":
        "Counts must be a numeric 20 × 344 array in the required feature order.",
    "Explicit boolean mask required for every recorded region in this view":
        "An explicit mask must contain Boolean M1 and S1 values.",
    "All-missing recorded-region input is unsupported": "At least one recorded region must be present.",
    "Direct/ridge missing-region mode is unsupported": "The direct model needs both M1 and S1.",
    "Observed recorded counts must be finite nonnegative integers before float32 conversion":
        "Present-region counts must be finite nonnegative integers.",
    "Recorded counts overflow float32": "A present-region count exceeds the finite float32 range.",
    "Recorded integer counts lose precision in float32": "A present-region count is not exact in float32.",
    "Exact raw-source SHA-256 and source-local stable feature ID order are required":
        "Supply this model's exact source SHA-256 and ordered source-local IDs.",
}


class InputError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def reject_constant(value):
    raise InputError(400, "JSON must not contain NaN or Infinity.")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(400, "Duplicate JSON keys are not allowed.")
        result[key] = value
    return result


class DeadlineReader:
    """Bound the entire request read, including slow headers, using one socket.

    No helper threads, process, timer service, retry or background job is used.
    HTTP pipelining is disabled; any over-read bytes die with this connection.
    """
    def __init__(self, connection):
        self.connection = connection
        self.deadline = time.monotonic() + READ_SECONDS
        self.buffer = bytearray()
        self.header_bytes = 0
        self.closed = False

    def _fill(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise InputError(408, "The request read deadline expired; nothing is retried.")
        self.connection.settimeout(remaining)
        try:
            block = self.connection.recv(8192)
        except (TimeoutError, socket.timeout):
            raise InputError(408, "The request read deadline expired; nothing is retried.") from None
        self.buffer.extend(block)
        return bool(block)

    def readline(self, size=-1):
        limit = 65537 if size < 0 else min(size, 65537)
        while True:
            end = self.buffer.find(b"\n", 0, limit)
            take = end + 1 if end >= 0 else min(len(self.buffer), limit)
            if end >= 0 or len(self.buffer) >= limit:
                break
            if not self._fill():
                take = len(self.buffer)
                break
        self.header_bytes += take
        if self.header_bytes > 65536:
            raise InputError(431, "Request headers exceed 64 KiB.")
        value = bytes(self.buffer[:take])
        del self.buffer[:take]
        return value

    def read(self, size):
        if not 0 <= size <= MAX_BODY_BYTES:
            raise InputError(413, "The JSON body exceeds 1500 kB.")
        out = bytearray()
        while len(out) < size:
            if not self.buffer and not self._fill():
                raise InputError(400, "The JSON body ended before Content-Length bytes arrived.")
            count = min(size - len(out), len(self.buffer))
            out.extend(self.buffer[:count])
            del self.buffer[:count]
        if time.monotonic() > self.deadline:
            raise InputError(408, "The request read deadline expired; nothing is retried.")
        return bytes(out)

    def close(self):
        self.buffer.clear()
        self.closed = True


def validate_payload(payload, decoders):
    if type(payload) is not dict:
        raise InputError(400, "The request must be a JSON object.")
    if set(payload) not in (REQUIRED_FIELDS, REQUIRED_FIELDS | {"region_mask"}):
        raise InputError(400, "Required fields are missing or unexpected request fields are present.")
    model = payload["model"]
    if type(model) is not str or model not in MODELS:
        raise InputError(400, "Choose first60seconds or full_training_partition.")
    decoder = decoders[model]
    if type(payload["request_id"]) is not str or not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", payload["request_id"]):
        raise InputError(400, "A fresh UUIDv4 request_id is required.")
    if (payload["count_unit"] != "counts/bin" or payload["velocity_unit"] != "m/s"
            or type(payload["bin_seconds"]) not in (int, Decimal)
            or payload["bin_seconds"] != Decimal("0.02")):
        raise InputError(400, "Use counts/bin, 0.02-second completed bins and m/s output units.")
    if type(payload["input_origin"]) is not str or payload["input_origin"] not in ORIGINS:
        raise InputError(400, "Declare entered, simulated or caller_declared_measured input.")
    source = payload["source_sha256"]
    if type(source) is not str or source != decoder.source_sha256:
        raise InputError(422, "The caller source SHA-256 must match this exact recording.")
    ids = payload["unit_ids"]
    if type(ids) is not list or any(type(x) is not str for x in ids) or tuple(ids) != decoder.unit_ids:
        raise InputError(422, "The caller must supply all 344 exact source-local IDs in model order.")
    mask = payload.get("region_mask")
    if "region_mask" in payload:
        if type(mask) is not dict or set(mask) != {"M1", "S1"} or any(type(v) is not bool for v in mask.values()):
            raise InputError(422, "An explicit region_mask must contain Boolean M1 and S1 values; omit it for both.")
        if not any(mask.values()):
            raise InputError(422, "All-missing input is unsupported.")
        if model == "first60seconds" and not all(mask.values()):
            raise InputError(422, "The direct first-60-second model requires both recorded regions.")
    counts = payload["counts"]
    if type(counts) is not list or len(counts) != 20 or any(type(row) is not list or len(row) != 344 for row in counts):
        raise InputError(422, "Supply the complete 20 × 344 count array, even when a region is masked.")
    normalized = []
    for row in counts:
        numeric_row = []
        for column, value in enumerate(row):
            if type(value) not in (int, Decimal) or (type(value) is Decimal and not value.is_finite()):
                raise InputError(422, "Every count position must contain a finite JSON number, never a Boolean.")
            present = mask is None or mask["M1" if column < 163 else "S1"]
            if not present:
                # Ignored values must not influence whole-array dtype selection.
                numeric_row.append(0.0)
                continue
            if value < 0 or (type(value) is Decimal and value != value.to_integral_value()):
                raise InputError(422, "Present-region counts must be nonnegative integers.")
            if value > MAX_FLOAT32_INTEGER:
                raise InputError(422, "A present-region count exceeds finite float32 range.")
            integer = int(value)  # Bounded above before decimal-to-integer conversion.
            try:
                exact = struct.unpack("!f", struct.pack("!f", integer))[0]
            except (OverflowError, struct.error):
                raise InputError(422, "A present-region count exceeds finite float32 range.") from None
            if not math.isfinite(exact) or int(exact) != integer:
                raise InputError(422, "A present-region integer count is not exactly representable in float32.")
            # A float32-exact integer is also exact in binary64. Uniform floats
            # avoid object/integer-array coercion without changing checked values.
            numeric_row.append(float(integer))
        normalized.append(numeric_row)
    return model, decoder, normalized


class PreviewServer(HTTPServer):
    allow_reuse_address = False
    request_queue_size = 1

    def handle_error(self, request, client_address):
        # No default traceback, private paths or input values in logs.
        print("A local request failed; no automatic retry was made.", file=sys.stderr)


class PreviewHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "NeuroTranslatorPreview"
    sys_version = ""

    def setup(self):
        super().setup()
        self.rfile.close()
        self.rfile = DeadlineReader(self.connection)

    def log_message(self, format, *args):
        pass  # Do not log source-local IDs, counts, URLs or filesystem paths.

    def handle_one_request(self):
        self.request_version = "HTTP/1.0"
        self.requestline = ""
        self.command = None
        try:
            super().handle_one_request()
        except InputError as error:
            self.reply(error.status, {"error": error.message})
        except (OSError, ConnectionError):
            pass
        finally:
            self.close_connection = True

    def send_error(self, code, message=None, explain=None):
        self.reply(code, {"error": self.responses.get(code, ("Request refused",))[0]})

    def handle_expect_100(self):
        self.reply(417, {"error": "Expect/100-continue is unsupported."})
        return False

    def one_header(self, name, required=False):
        values = self.headers.get_all(name, [])
        if len(values) > 1 or (required and len(values) != 1):
            raise InputError(400, "A single " + name + " header is required.")
        return values[0] if values else None

    def check_local_request(self, mutation=False):
        if self.client_address[0] != "127.0.0.1":
            raise InputError(403, "Only the local loopback client is supported.")
        if self.one_header("Host", True) != self.server.authority:
            raise InputError(403, "Use the exact loopback address printed at startup.")
        origin = self.one_header("Origin", mutation)
        if origin is not None and origin != self.server.origin:
            raise InputError(403, "This request must come from the same local page.")
        site = self.one_header("Sec-Fetch-Site")
        if site is not None and site not in ("same-origin", "none"):
            raise InputError(403, "Cross-origin requests are unsupported.")
        for name in ("Transfer-Encoding", "Content-Encoding", "Expect"):
            if self.one_header(name) is not None:
                raise InputError(400, name + " is unsupported.")
        if mutation:
            token = self.one_header("X-Preview-Token", True)
            if not token.isascii() or not secrets.compare_digest(token, self.server.token):
                raise InputError(403, "Reopen the local page to obtain its current request token.")

    def reply(self, status, value, content_type="application/json; charset=utf-8"):
        self.close_connection = True
        body = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False, ensure_ascii=True).encode("utf-8")
        try:
            self.connection.settimeout(WRITE_SECONDS)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            self.send_header("Content-Security-Policy", self.server.csp)
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        except (OSError, ConnectionError):
            pass  # Outcome may be unknown to the client; never retry.

    def do_GET(self):
        try:
            self.check_local_request()
            if self.one_header("Content-Length") not in (None, "0"):
                raise InputError(400, "GET requests do not accept a body.")
            if self.path == "/":
                self.reply(200, self.server.page, "text/html; charset=utf-8")
            elif self.path == "/api/models":
                self.reply(200, {"models": self.server.catalog, "request_token": self.server.token,
                                 "display_glossary": DISPLAY_GLOSSARY,
                                 "serialized_glossary": SERIALIZED_GLOSSARY})
            else:
                self.reply(404, {"error": "This local address has no endpoint."})
        except InputError as error:
            self.reply(error.status, {"error": error.message})

    def do_POST(self):
        try:
            self.check_local_request(mutation=True)
            if self.path != "/api/decode":
                raise InputError(404, "This local address has no endpoint.")
            content_type = self.one_header("Content-Type", True).lower().replace(" ", "")
            if content_type not in ("application/json", "application/json;charset=utf-8"):
                raise InputError(415, "Use application/json with UTF-8 text.")
            length = self.one_header("Content-Length", True)
            if not re.fullmatch(r"0|[1-9][0-9]{0,6}", length):
                raise InputError(400, "Content-Length must be one unambiguous decimal byte count.")
            length = int(length)
            if length > MAX_BODY_BYTES:
                raise InputError(413, "The JSON body exceeds 1500 kB (1,500,000 bytes).")
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"),
                                     object_pairs_hook=unique_object, parse_float=Decimal,
                                     parse_constant=reject_constant)
            except (UnicodeError, ValueError, RecursionError, DecimalException):
                raise InputError(400, "The body must be one well-formed UTF-8 JSON object.") from None
            model, decoder, counts_for_decoder = validate_payload(payload, self.server.decoders)
            request_id = payload["request_id"]
            if request_id in self.server.seen:
                raise InputError(409, "This request ID has already been attempted; it will not be retried.")
            if len(self.server.seen) >= MAX_REQUESTS:
                raise InputError(503, "This session reached its bounded request limit; no request was started.")
            self.server.seen.add(request_id)  # Consume before inference, including failed/unknown outcomes.
            try:
                physical = decoder.decode(counts_for_decoder, payload["unit_ids"],
                                          source_sha256=payload["source_sha256"],
                                          region_mask=payload.get("region_mask"))
            except ValueError as error:
                raise InputError(422, DECODER_ERRORS.get(str(error), "The decoder rejected this count window.")) from None
            values = [float(x) for x in physical]
            if len(values) != 2 or not all(math.isfinite(x) for x in values):
                raise InputError(500, "The model did not return two finite velocity components.")
            self.reply(200, {"request_id": request_id, "model": model,
                             "validation_selected_run": MODELS[model]["run"],
                             "velocity_xy": values, "velocity_unit": "m/s",
                             "output_kind": "model_estimate", "observed": False,
                             "input_origin": payload["input_origin"], "origin_authenticated": False,
                             "source_sha256": payload["source_sha256"],
                             "region_mask": payload.get("region_mask"),
                             "context_bins": 20, "bin_seconds": 0.02, "history_seconds": 0.4})
        except InputError as error:
            self.reply(error.status, {"error": error.message})
        except Exception:
            self.reply(500, {"error": "The model request failed. No output is available and no retry was made."})


def run_runtime(port):
    """Explicit future runtime only. This source step grants no authority to call it.

    Requires separate actual actor/lease/use/rights/current funds/holds/loaded-source,
    SourceFive-as-applicable and model/runtime admission. No proof token is invented.
    """
    # Defaults affect only this process, before any neural/numerical import.
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ.setdefault(name, "1")
    root = Path(__file__).resolve().parent
    for relative, expected in CODE_PINS.items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError("A fixed decoder/dependency source does not match the selected bundle.")
    if any(name == "neural" or name.startswith("neural.") for name in sys.modules):
        raise RuntimeError("Use a fresh process for the fixed decoder bundle.")
    sys.path.insert(0, str(root))
    # Never move this import or model construction to module scope.
    from neural.portable_loco import PortableLocoDecoder

    decoders, catalog = {}, []
    for budget, choice in MODELS.items():
        decoder = PortableLocoDecoder(root / choice["weights"], root / choice["metadata"],
                                      expected_metadata_sha256=choice["metadata_sha256"])
        meta = decoder.metadata
        required = {"budget": budget, "method": choice["method"], "view": "combined",
                    "session": "loco_20170215_02", "source_sha256": SOURCE_SHA256,
                    "validation_selected_run": choice["run"], "weights_sha256": choice["weights_sha256"],
                    "source_checkpoint_sha256": choice["checkpoint_sha256"],
                    "region_sizes": {"M1": 163, "S1": 181}}
        if any(meta.get(key) != value for key, value in required.items()) or decoder.feature_count != 344:
            raise RuntimeError("A loaded model differs from the fixed selected export.")
        if choice["supports_region_mask"] and meta["trunk_config"]["n_units"] != 171:
            raise RuntimeError("The adapted model input basis differs from the selected export.")
        decoders[budget] = decoder
        catalog.append({"id": budget, "label": choice["label"], "method": decoder.method,
                        "validation_selected_run": choice["run"], "session": meta["session"],
                        "source_sha256": decoder.source_sha256, "unit_ids": list(decoder.unit_ids),
                        "regions": list(decoder.regions), "region_sizes": meta["region_sizes"],
                        "recorded_features": 344, "input_shape": [20, 344],
                        "virtual_input_basis_features": choice["virtual_input_basis_features"],
                        "supports_region_mask": choice["supports_region_mask"],
                        "semantics": meta["semantics"], "count_unit": "counts/bin", "velocity_unit": "m/s",
                        "metadata_sha256": choice["metadata_sha256"], "weights_sha256": choice["weights_sha256"],
                        "selection_partition": meta["selection_partition"],
                        "limits": "Recent recorded-task velocity; transfer benefit unconfirmed for both budgets. Caller origin is unauthenticated. No uncertainty interval is calibrated here."})
    nonce = secrets.token_urlsafe(24)
    page = (root / "preview.html").read_bytes().replace(b"__CSP_NONCE__", nonce.encode("ascii"))
    server = PreviewServer(("127.0.0.1", port), PreviewHandler)
    try:
        server.decoders = decoders
        server.catalog = catalog
        server.page = page
        server.token = secrets.token_urlsafe(32)
        server.seen = set()
        server.authority = "127.0.0.1:" + str(server.server_port)
        server.origin = "http://" + server.authority
        server.csp = ("default-src 'none'; script-src 'nonce-" + nonce + "'; style-src 'nonce-" + nonce
                      + "'; connect-src 'self'; img-src 'none'; font-src 'none'; base-uri 'none'; "
                      "form-action 'none'; frame-ancestors 'none'; object-src 'none'")
        print("Open " + server.origin + "/ in this computer's browser. Ctrl+C closes the server.")
        # One foreground process, one request at a time. No automatic retry.
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        decoders.clear()


def main():
    parser = argparse.ArgumentParser(description="Unexecuted source candidate; runtime needs separate qualification.")
    parser.add_argument("action", choices=["run"], help="Explicitly start the qualified future bundle only.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a loopback port from 1024 to 65535.")
    try:
        run_runtime(args.port)
    except KeyboardInterrupt:
        print("Local server closed. No request was retried.")
    except Exception:
        print("Startup failed. Check the qualified bundle and environment; no automatic retry was made.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
