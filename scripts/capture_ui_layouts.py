import json
import sys
import time
from pathlib import Path

from PIL import ImageGrab

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ui.layout.main_window import MainWindow


SIZES = [(1920, 1080), (1366, 768), (1280, 720), (1024, 768)]
OUTPUT_DIR = Path("logs/layout_checks")


def boxes_overlap(left, right):
    return not (
        left[2] <= right[0]
        or right[2] <= left[0]
        or left[3] <= right[1]
        or right[3] <= left[1]
    )


def capture(window, name):
    window.deiconify()
    window.lift()
    window.attributes("-topmost", True)
    window.focus_force()
    window.update_idletasks()
    window.update()
    time.sleep(0.1)
    x = window.winfo_rootx()
    y = window.winfo_rooty()
    width = window.winfo_width()
    height = window.winfo_height()
    path = OUTPUT_DIR / f"{name}.png"
    ImageGrab.grab(bbox=(x, y, x + width, y + height), all_screens=True).save(path)
    return str(path)


def dashboard_result(window, width, height):
    window.navigate("dashboard")
    window.update_idletasks()
    page = window.router.pages["dashboard"]
    page._reflow(page.winfo_width())
    window.update_idletasks()
    cards = list(page.cards.values())
    bounds = [
        (
            card.winfo_rootx(),
            card.winfo_rooty(),
            card.winfo_rootx() + card.winfo_width(),
            card.winfo_rooty() + card.winfo_height(),
        )
        for card in cards
    ]
    overlaps = sum(
        1
        for index, left in enumerate(bounds)
        for right in bounds[index + 1 :]
        if boxes_overlap(left, right)
    )
    return {
        "viewport": f"{width}x{height}",
        "columns": page._column_count,
        "card_overlaps": overlaps,
        "scrollable_content_height": page.body._parent_canvas.bbox("all")[3],
        "scrollable_view_height": page.body.winfo_height(),
        "sidebar_width": window.sidebar.winfo_width(),
        "screenshot": capture(window, f"dashboard_{width}x{height}"),
    }


def history_result(window, width, height):
    window.navigate("history")
    window.update_idletasks()
    page = window.router.pages["history"]
    page._sync_scroll_region()
    region = page.canvas.bbox("all") or (0, 0, 0, 0)
    return {
        "viewport": f"{width}x{height}",
        "table_content_width": region[2],
        "table_view_width": page.canvas.winfo_width(),
        "horizontal_scroll_required": region[2] > page.canvas.winfo_width(),
        "sidebar_width": window.sidebar.winfo_width(),
        "screenshot": capture(window, f"history_{width}x{height}"),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    window = MainWindow()
    window.update()
    results = {"dashboard": [], "history": []}

    try:
        for width, height in SIZES:
            window.geometry(f"{width}x{height}+0+0")
            window.update()
            results["dashboard"].append(dashboard_result(window, width, height))
            results["history"].append(history_result(window, width, height))
    finally:
        window.destroy()

    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
