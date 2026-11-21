"""Read the static assets the selected local game explicitly declares."""
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".bin": "application/octet-stream",
    ".txt": "text/plain; charset=utf-8", ".obj": "text/plain; charset=utf-8",
    ".task": "application/octet-stream", ".nspack": "application/octet-stream",
    ".wasm": "application/wasm", ".woff2": "font/woff2", ".wav": "audio/wav", ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg", ".mp4": "video/mp4", ".webm": "video/webm", ".ico": "image/x-icon",
}


class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.inline = False
        self.hashes = set()

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.inline = "src" not in dict(attrs)

    def handle_endtag(self, tag):
        if tag == "script":
            self.inline = False

    def handle_data(self, data):
        if self.inline:
            digest = hashlib.sha256(data.encode("utf-8")).digest()
            self.hashes.add("'sha256-" + base64.b64encode(digest).decode("ascii") + "'")


class GameMount:
    def __init__(self, directory):
        root = Path(directory).resolve(strict=True)
        manifest = root / "joint-game.json"
        if not root.is_dir() or manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 1_000_000:
            raise ValueError("The game directory needs a regular joint-game.json manifest.")
        spec = json.loads(manifest.read_text(encoding="utf-8"))
        files = spec.get("files") if isinstance(spec, dict) else None
        if not isinstance(spec, dict) or spec.get("version") != 1 or not isinstance(files, list) or not all(isinstance(k, str) for k in files):
            raise ValueError("Expected a version 1 game manifest listing its static files.")
        if "index.html" not in files or len(files) != len(set(files)):
            raise ValueError("List index.html and each game asset exactly once.")
        self.root = root
        self.files = {}
        total = 0
        if len(files) > 16_384:
            raise ValueError("A game can list at most 16,384 static assets.")
        for name in files:
            rel = PurePosixPath(name)
            if (not name or rel.is_absolute() or rel.as_posix() != name or chr(92) in name or
                    any(part.startswith(".") or ":" in part for part in rel.parts) or
                    any(ord(c) < 32 or c in "%?#" for c in name) or rel.suffix.lower() not in TYPES):
                raise ValueError(f"Unsupported game asset name: {name}")
            path = self.path_for(rel)
            size = path.stat().st_size
            total += size
            if size > 128 * 1024 ** 2 or total > 1024 ** 3:
                raise ValueError("Game assets must fit within 128 MiB per file and 1 GiB overall.")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while block := stream.read(1024 ** 2):
                    digest.update(block)
            self.files[name] = (size, digest.digest(), TYPES[rel.suffix.lower()])

    def path_for(self, rel):
        path = self.root.joinpath(*rel.parts)
        if (any(self.root.joinpath(*rel.parts[:i]).is_symlink() for i in range(1, len(rel.parts) + 1)) or
                not path.resolve(strict=True).is_relative_to(self.root) or not path.is_file()):
            raise ValueError(f"Each game asset must be a regular local file: {rel}")
        return path

    def get(self, url):
        path = unquote(urlsplit(url).path)
        name = "index.html" if path == "/game/" else path.removeprefix("/game/")
        if not path.startswith("/game/") or name not in self.files:
            return None
        size, digest, media = self.files[name]
        try:
            with self.path_for(PurePosixPath(name)).open("rb") as stream:
                data = stream.read(size + 1)
        except (OSError, ValueError):
            return None
        if len(data) != size or hashlib.sha256(data).digest() != digest:
            return None
        policy = None
        if media.startswith("text/html"):
            scripts = InlineScripts()
            scripts.feed(data.decode("utf-8").replace(chr(13)+chr(10), chr(10)).replace(chr(13), chr(10)))
            policy = ("default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; "
                      "connect-src 'self'; script-src 'self' 'wasm-unsafe-eval' " + " ".join(sorted(scripts.hashes)) +
                      "; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; worker-src 'self' blob:")
        elif name == "scene/src/camera/pose-worker.js":
            policy = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; "
                      "object-src 'none'; base-uri 'none'")
        return data, media, policy
