"""Assemble the standalone HTML. No network or third-party dependencies."""
from pathlib import Path
from base64 import b64encode

root = Path(__file__).resolve().parent
src = root / "src"
template = (src / "page.html").read_text()
js = "\n".join((src / name).read_text() for name in ("example.js", "predict.js", "chart.js", "view.js"))
data = (src / "bundle.json").read_text().replace("<", "\\u003c")
licence = b64encode((root / "DATA-LICENCE.txt").read_bytes()).decode("ascii")
for key, value in (("LICENCE", licence), ("CSS", (src/"style.css").read_text()), ("DATA",data), ("JS",js)):
    token = "%%"+key+"%%"
    if template.count(token) != 1:
        raise ValueError(f"Expected one {token} placeholder")
    template = template.replace(token,value)
(root / "index.html").write_text(template)
