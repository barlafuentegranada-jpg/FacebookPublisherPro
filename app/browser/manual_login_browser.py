import os
import subprocess
from pathlib import Path


class ManualLoginBrowser:
    """Launches normal installed Chrome for manual Facebook authentication."""

    PROFILE_LOCK_MESSAGE = "Close the manual Chrome window before checking login."

    def __init__(self):
        self.processes = {}

    def open(self, profile_path):
        chrome_path = self._chrome_path()
        absolute_profile = Path(profile_path).resolve()
        absolute_profile.mkdir(parents=True, exist_ok=True)

        if self.is_profile_in_use(absolute_profile):
            raise RuntimeError(self.PROFILE_LOCK_MESSAGE)

        process = subprocess.Popen(
            [
                str(chrome_path),
                f"--user-data-dir={absolute_profile}",
                "--no-first-run",
                "--no-default-browser-check",
                "https://www.facebook.com/",
            ]
        )
        self.processes[str(absolute_profile)] = process
        return process

    def is_profile_in_use(self, profile_path):
        absolute_profile = str(Path(profile_path).resolve())
        process = self.processes.get(absolute_profile)

        if process and process.poll() is None:
            return True

        self.processes.pop(absolute_profile, None)

        return self.has_profile_lock(absolute_profile)

    def has_profile_lock(self, profile_path):
        profile = Path(profile_path)
        lock_names = [
            "SingletonLock",
            "SingletonCookie",
            "SingletonSocket",
            "LOCK",
        ]

        return any((profile / lock_name).exists() for lock_name in lock_names)

    def _chrome_path(self):
        candidates = [
            os.environ.get("PROGRAMFILES", ""),
            os.environ.get("PROGRAMFILES(X86)", ""),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        relative = Path("Google/Chrome/Application/chrome.exe")

        for base in candidates:
            if not base:
                continue

            path = Path(base) / relative

            if path.exists():
                return path

        raise RuntimeError(
            "Google Chrome is not installed. Install Chrome to use manual Facebook login."
        )


manual_login_browser = ManualLoginBrowser()
