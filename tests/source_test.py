import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class SourceTests(unittest.TestCase):
    def test_release_rejects_staged_unstaged_and_untracked_changes(self):
        for change in ("staged", "unstaged", "untracked"):
            with self.subTest(change=change), tempfile.TemporaryDirectory(prefix="ydotool-provenance-test-") as directory:
                root = Path(directory)
                (root / "packaging").mkdir()
                shutil.copyfile(ROOT / "packaging/build.sh", root / "packaging/build.sh")
                (root / "VERSION").write_text("1.0.4\n")
                (root / ".gitignore").write_text(".build/\ndist/\n")
                def git(*args):
                    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
                git("init", "-q")
                git("add", ".")
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Fixture")
                if change == "untracked":
                    (root / "secret.txt").write_text("must not enter source package")
                else:
                    (root / "VERSION").write_text("1.0.5\n")
                    if change == "staged":
                        git("add", "VERSION")
                result = subprocess.run(["bash", "packaging/build.sh", "package"], cwd=root, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("release requires a clean Git checkout", result.stderr)
                self.assertFalse((root / "dist").exists())


if __name__ == "__main__":
    unittest.main()
