import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.browser.browser_manager import BrowserManager


def print_result(label, result):
    status = "ok" if result.get("success") else "failed"
    print(f"{label}: {status} - {result.get('message')}")


def main():
    manager = BrowserManager()
    profiles_root = Path("profiles/accounts").resolve()
    account_one = {
        "id": "diagnostic-1",
        "name": "Diagnostic Account 1",
        "profile_path": str(profiles_root / "diagnostic-1"),
    }
    account_two = {
        "id": "diagnostic-2",
        "name": "Diagnostic Account 2",
        "profile_path": str(profiles_root / "diagnostic-2"),
    }

    try:
        print_result("start account 1", manager.start_account(account_one))
        print_result("navigate account 1", manager.goto("https://www.facebook.com/"))
        print_result("close account 1", manager.close())
        print_result("switch account 2", manager.switch_account(account_two))
        print_result("navigate account 2", manager.goto("https://www.facebook.com/"))
        print_result("switch account 1", manager.switch_account(account_one))
        print_result("queued navigation 1", manager.goto("https://www.facebook.com/"))
        print_result("queued navigation 2", manager.goto("https://www.facebook.com/groups/feed/"))
    finally:
        print_result("shutdown", manager.shutdown())


if __name__ == "__main__":
    main()
