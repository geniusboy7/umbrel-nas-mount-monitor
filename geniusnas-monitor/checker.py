"""Read-only CIFS mount health endpoint for an Umbrel app."""

from __future__ import annotations

import os
import re
import stat
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


_ESCAPE = re.compile(r"\\([0-7]{3})")


def _unescape(value: str) -> str:
    return _ESCAPE.sub(lambda match: chr(int(match.group(1), 8)), value)


def mount_identity(mountinfo: str, target: str) -> tuple[str, str] | None:
    """Return (filesystem type, source) for an exact mount point."""
    identity = None
    for line in mountinfo.splitlines():
        if " - " not in line:
            continue
        left, right = line.split(" - ", 1)
        pre, post = left.split(), right.split()
        if len(pre) >= 5 and len(post) >= 2 and _unescape(pre[4]) == target:
            identity = post[0], _unescape(post[1])
    return identity


def check_mount(root: Path, expected_source: str, mountinfo_path: Path) -> bool:
    """Inspect metadata only; do not enumerate or open media files."""
    try:
        identity = mount_identity(mountinfo_path.read_text(), str(root))
        if identity != ("cifs", expected_source):
            return False
        base = root.stat()
        if not stat.S_ISDIR(base.st_mode):
            return False
        for name in ("Downloads", "Movies", "TV Shows"):
            entry = (root / name).stat()
            if not stat.S_ISDIR(entry.st_mode) or entry.st_dev != base.st_dev:
                return False
        return os.statvfs(root).f_blocks > 0
    except (OSError, ValueError, UnicodeError):
        return False


class BoundedProbe:
    """Bound each HTTP request and allow at most one blocked CIFS worker."""

    def __init__(self, probe, timeout: float = 5.0):
        self.probe = probe
        self.timeout = timeout
        self.lock = threading.Lock()
        self.worker: threading.Thread | None = None

    def run(self) -> bool:
        with self.lock:
            if self.worker is not None and self.worker.is_alive():
                return False
            finished = threading.Event()
            result = [False]

            def work():
                try:
                    result[0] = bool(self.probe())
                except Exception:
                    result[0] = False
                finally:
                    finished.set()

            self.worker = threading.Thread(target=work, daemon=True)
            self.worker.start()
        return finished.wait(self.timeout) and result[0]


def handler_for(probe: BoundedProbe):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/health":
                self.send_error(404)
                return
            healthy = probe.run()
            body = b"ok\n" if healthy else b"unhealthy\n"
            self.send_response(200 if healthy else 503)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    expected = os.environ["EXPECTED_SOURCE"]
    if not expected.startswith("//") or not expected.endswith("/Media"):
        raise ValueError("EXPECTED_SOURCE must identify the Media CIFS share")
    root = Path(os.environ.get("MEDIA_ROOT", "/nas/Media"))
    probe = BoundedProbe(lambda: check_mount(root, expected, Path("/proc/self/mountinfo")))
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), handler_for(probe))
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
