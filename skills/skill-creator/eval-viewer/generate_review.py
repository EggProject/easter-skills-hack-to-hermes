"""eval-viewer/generate_review.py — write feedback.json next to viewer.html.

`--static` mode writes the viewer's data file (feedback.json) next to
viewer.html with a relative path that resolves under the same dir.

TDD test cases for this module:
  test_eval_viewer_static_open
"""

from __future__ import annotations

import argparse
import http.server
import json
import socketserver
from pathlib import Path

from scripts.utils import emit


def write_static(feedback: dict, *, out_dir: Path) -> tuple[Path, Path]:
    """Write feedback.json next to viewer.html. Returns (json_path, html_path)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "feedback.json"
    html_path = out_dir / "viewer.html"
    json_path.write_text(json.dumps(feedback, indent=2, sort_keys=True), encoding="utf-8")
    html_path.write_text(_render_html(feedback), encoding="utf-8")
    return json_path, html_path


def _render_html(feedback: dict) -> str:
    """Render a self-contained HTML page that fetches `feedback.json` (relative)."""
    return """<!doctype html>
<html><head><title>Eval Review</title></head>
<body>
<h1>Eval Review</h1>
<pre id="feedback">{}</pre>
<script>
fetch('feedback.json')
  .then(r => r.json())
  .then(j => { document.getElementById('feedback').textContent = JSON.stringify(j, null, 2); })
  .catch(e => { document.getElementById('feedback').textContent = 'Error: ' + e; });
</script>
</body></html>
"""


def serve(feedback: dict, *, port: int = 8765) -> None:
    """Serve the viewer + feedback.json over a stdlib HTTP server."""
    out_dir = Path("/tmp/eval-viewer")
    json_path, html_path = write_static(feedback, out_dir=out_dir)
    handler_cls = type(
        "_Handler",
        (http.server.SimpleHTTPRequestHandler,),
        {"__init__": lambda self, *a, **kw: super().__init__(*a, directory=str(out_dir), **kw)},
    )
    with socketserver.TCPServer(("", port), handler_cls) as httpd:
        emit(
            f"Serving viewer at http://localhost:{port}/{html_path.name}",
            f"Viewer kiszolgálás: http://localhost:{port}/{html_path.name}",
        )
        httpd.serve_forever()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="generate_review.py",
        description=(
            "Write feedback.json next to viewer.html, or serve both via HTTP.\n"
            "Use when: you want a side-by-side HTML review of a benchmark run."
        ),
    )
    p.add_argument("--feedback", required=True, help="Path to the feedback JSON.")
    p.add_argument("--out-dir", default="./eval-review", help="Output directory.")
    p.add_argument("--static", action="store_true", help="Write files; do not serve.")
    p.add_argument("--port", type=int, default=8765, help="HTTP port (serve mode).")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    feedback = json.loads(Path(args.feedback).read_text(encoding="utf-8"))
    if args.static:
        json_path, html_path = write_static(feedback, out_dir=Path(args.out_dir))
        emit(
            f"Wrote {json_path} + {html_path}",
            f"Írva: {json_path} + {html_path}",
        )
        return 0
    serve(feedback, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
