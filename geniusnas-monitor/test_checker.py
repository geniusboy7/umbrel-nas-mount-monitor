import tempfile
import threading
import time
import unittest
from pathlib import Path

from checker import BoundedProbe, check_mount


SOURCE = "//example.local/Media"


class MountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Media"
        self.root.mkdir()
        for name in ("Downloads", "Movies", "TV Shows"):
            (self.root / name).mkdir()
        escaped = str(self.root).replace(" ", "\\040")
        self.mountinfo = Path(self.temp.name) / "mountinfo"
        self.mountinfo.write_text(f"30 20 0:55 / {escaped} rw - cifs {SOURCE} rw\n")

    def test_healthy(self):
        self.assertTrue(check_mount(self.root, SOURCE, self.mountinfo))

    def test_missing_mount(self):
        self.mountinfo.write_text("")
        self.assertFalse(check_mount(self.root, SOURCE, self.mountinfo))

    def test_wrong_filesystem_or_source(self):
        original = self.mountinfo.read_text()
        self.mountinfo.write_text(original.replace("cifs", "ext4"))
        self.assertFalse(check_mount(self.root, SOURCE, self.mountinfo))
        self.mountinfo.write_text(original.replace(SOURCE, "//other.local/Media"))
        self.assertFalse(check_mount(self.root, SOURCE, self.mountinfo))

    def test_missing_path_and_read_error(self):
        (self.root / "Movies").rmdir()
        self.assertFalse(check_mount(self.root, SOURCE, self.mountinfo))
        self.mountinfo.unlink()
        self.assertFalse(check_mount(self.root, SOURCE, self.mountinfo))


class BoundedProbeTests(unittest.TestCase):
    def test_stalled_access_is_bounded_and_not_duplicated(self):
        release = threading.Event()
        calls = [0]

        def stalled():
            calls[0] += 1
            release.wait()
            return True

        probe = BoundedProbe(stalled, timeout=0.02)
        started = time.monotonic()
        self.assertFalse(probe.run())
        self.assertFalse(probe.run())
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(calls[0], 1)
        release.set()
        probe.worker.join(1)

    def test_probe_exception_is_unhealthy(self):
        probe = BoundedProbe(lambda: 1 / 0)
        self.assertFalse(probe.run())


if __name__ == "__main__":
    unittest.main()
