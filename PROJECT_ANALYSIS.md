# Project Architecture Analysis

Generated on 2026-07-22.

## Executive Summary

This is a Python desktop application for managing Facebook group publishing. The app uses:

- `customtkinter` for the desktop UI.
- Playwright sync API for browser automation.
- SQLite for local persistence.
- A persistent Chromium profile under `profiles/facebook`.

The codebase is small, but the repository contains large generated/runtime directories (`profiles/`, `venv/`, `.git/`) and multiple SQLite database files with different schemas. The main architectural risks are UI/service coupling, synchronous long-running Playwright calls on the UI thread, duplicate UI construction, stale database artifacts, and checked-in browser profile data.

## 1. Folder Structure

Top-level structure:

```text
.
├── .git/                         # Git metadata; very large in this checkout
├── .vscode/                      # IDE settings
├── app/                          # Application source
│   ├── browser/                  # Playwright browser lifecycle
│   ├── controllers/              # Present but effectively unused
│   ├── database/                 # SQLite wrapper and stale DB artifact
│   ├── models/                   # Dataclass model definitions
│   ├── services/                 # Facebook scan/analyze/publish services
│   ├── ui/                       # CustomTkinter UI
│   ├── utils/                    # Present but empty
│   └── workers/                  # Generic background worker
├── assets/                       # Empty
├── config/                       # Empty `config.json`
├── data/                         # Active SQLite DB location
├── logs/                         # Empty
├── profiles/                     # Persistent Chromium profile/runtime data
├── venv/                         # Local virtual environment
├── README.md                     # Empty
├── requirements.txt              # Empty
├── requirements_backup.txt       # Actual dependency list
├── database.db                   # Legacy/stale SQLite DB
└── PROJECT_ANALYSIS.md           # This report
```

Observed folder sizes/counts:

| Folder | Files | Approx. bytes | Notes |
| --- | ---: | ---: | --- |
| `app/` | 41 | 131 KB | Includes source, `__pycache__`, and `app/database/facebook_publisher.db`. |
| `profiles/` | 2,793 | 415 MB | Chromium user profile/cache/session data. Tracked by Git. |
| `venv/` | 7,664 | 281 MB | Local virtual environment. Should remain untracked. |
| `data/` | 1 | 49 KB | Active app database: `data/facebook.db`. |
| `config/` | 1 | 0 B | Empty `config.json`. |
| `assets/` | 0 | 0 B | Empty. |
| `logs/` | 0 | 0 B | Empty. |

Important repository hygiene note: `.gitignore` excludes `venv/`, `*.db`, `data/*.db`, `.vscode/`, and `__pycache__/`, but those files/directories are already present in the repository index or workspace. `profiles/facebook` is not ignored and 2,793 profile files are tracked.

## 2. All Python Files

| File | Lines | Purpose |
| --- | ---: | --- |
| `app/__init__.py` | 0 | Empty package marker. |
| `app/main.py` | 11 | App entrypoint; configures CustomTkinter and opens `MainWindow`. |
| `app/browser/__init__.py` | 0 | Empty package marker. |
| `app/browser/browser_manager.py` | 114 | Owns Playwright lifecycle and persistent Chromium context. |
| `app/controllers/__init__.py` | 0 | Empty package marker. |
| `app/controllers/facebook_controller.py` | 0 | Empty controller stub. |
| `app/database/__init__.py` | 0 | Empty package marker. |
| `app/database/db.py` | 373 | SQLite connection, schema creation, group/history/settings operations. |
| `app/models/__init__.py` | 0 | Empty package marker. |
| `app/models/group.py` | 15 | `Group` dataclass, not integrated with DB/UI flow. |
| `app/services/__init__.py` | 0 | Empty package marker. |
| `app/services/facebook_service.py` | 35 | Facade for login, scan groups, analyze groups. |
| `app/services/group_analyzer.py` | 90 | Visits saved group URLs and extracts title/member/privacy metadata. |
| `app/services/group_scanner.py` | 205 | Opens Facebook groups feed, scrolls, extracts group links, saves groups. |
| `app/services/post_service.py` | 127 | In-memory post draft state. |
| `app/services/publisher.py` | 68 | Iterates selected groups; currently only opens each group. |
| `app/ui/__init__.py` | 0 | Empty package marker. |
| `app/ui/groups_table.py` | 81 | Scrollable CustomTkinter table-like widget. |
| `app/ui/main_window.py` | 567 | Main desktop UI and event handlers. |
| `app/utils/__init__.py` | 0 | Empty package marker. |
| `app/utils/logger.py` | 0 | Empty logger stub. |
| `app/workers/__init__.py` | 0 | Empty package marker. |
| `app/workers/worker.py` | 51 | Generic thread wrapper, currently unused. |

## 3. Dependency Graph

### External Dependencies

Actual dependencies are listed in `requirements_backup.txt`; `requirements.txt` is empty.

Declared backup dependencies:

- `customtkinter`
- `darkdetect`
- `greenlet`
- `numpy`
- `openpyxl`
- `packaging`
- `pandas`
- `pillow`
- `playwright`
- `pyee`
- `python-dateutil`
- `six`
- `typing_extensions`
- `tzdata`

Used directly by source:

- `customtkinter`: `app/main.py`, `app/ui/main_window.py`, `app/ui/groups_table.py`
- `tkinter.filedialog`: `app/ui/main_window.py`
- `playwright.sync_api`: `app/browser/browser_manager.py`, `app/services/group_scanner.py`, `app/services/group_analyzer.py`
- `sqlite3`: `app/database/db.py`
- Standard library: `os`, `pathlib`, `dataclasses`, `threading`

Likely unused dependencies in the current code:

- `numpy`
- `openpyxl`
- `pandas`
- `pillow`
- `python-dateutil`
- `six`
- `tzdata`
- `packaging`
- `darkdetect` is an indirect CustomTkinter dependency, not app code.
- `greenlet` and `pyee` are Playwright transitive dependencies.

### Local Import Graph

```text
app.main
└── app.ui.main_window
    ├── app.database.db
    ├── app.services.facebook_service
    │   ├── app.browser.browser_manager
    │   ├── app.services.group_analyzer
    │   │   ├── app.browser.browser_manager
    │   │   └── app.database.db
    │   └── app.services.group_scanner
    │       ├── app.browser.browser_manager
    │       └── app.database.db
    ├── app.services.post_service
    ├── app.services.publisher
    │   ├── app.browser.browser_manager
    │   ├── app.database.db
    │   └── app.services.post_service
    └── app.ui.groups_table
```

Independent/unused modules:

```text
app.models.group
app.workers.worker
app.controllers.facebook_controller
app.utils.logger
```

### Runtime Singleton Graph

Several modules instantiate global singletons at import time:

- `app.browser.browser_manager.browser = BrowserManager()`
- `app.database.db.db = Database()`
- `app.services.facebook_service.facebook = FacebookService()`
- `app.services.group_analyzer.analyzer = GroupAnalyzer()`
- `app.services.group_scanner.scanner = GroupScanner()`
- `app.services.post_service.post_service = PostService()`
- `app.services.publisher.publisher = Publisher()`

This simplifies wiring, but it also makes testing, alternate profiles, multiple accounts, and clean shutdown harder.

## 4. Dead Code / Unused Code

Likely unused modules:

- `app/controllers/facebook_controller.py`: empty.
- `app/utils/logger.py`: empty.
- `app/models/group.py`: defines `Group`, but database rows are used directly everywhere.
- `app/workers/worker.py`: generic worker exists, but long-running UI actions do not use it.

Likely unused methods/functions:

- `BrowserManager.refresh()`
- `BrowserManager.stop()`
- `Database.add_history()`
- `Database.get_history()`
- `Database.set_setting()`
- `Database.get_setting()`
- `Database.close()`
- `MainWindow.refresh_groups()`
- `MainWindow.get_selected_group_ids()`
- `MainWindow.get_selected_groups()`
- `MainWindow.clear_post()`
- `MainWindow.update_status()`
- `MainWindow.on_closing()` is defined but not wired to `WM_DELETE_WINDOW`.

Dead/stale artifacts:

- `database.db`: legacy schema with only a `groups` table using text IDs.
- `app/database/facebook_publisher.db`: richer older/alternate schema, not opened by current code.
- `requirements.txt`: empty while `requirements_backup.txt` contains the installable dependency list.
- `config/config.json`: empty.
- `README.md`: empty.
- `assets/` and `logs/`: empty directories.

## 5. Duplicate Code

### Duplicate Right Panel in `app/ui/main_window.py`

`MainWindow.__init__` creates the right panel twice:

- First block starts around `app/ui/main_window.py:89`.
- Second block starts around `app/ui/main_window.py:128`.

The duplicated section includes:

- `right = ctk.CTkFrame(body)`
- `right.grid(...)`
- `Post Editor` label
- `Title` label and `self.title_entry`
- `Post Text` label and `self.content_box`

Effect:

- The first right panel widgets are overwritten by the second `right` frame on the same grid cell.
- `self.title_entry` and `self.content_box` are assigned twice.
- The UI appears to work from the second panel, but the first panel remains unnecessary construction noise and may create layout/resource confusion.

### Repeated Patterns

There is also smaller structural duplication:

- Repeated file picker patterns in `choose_image()` and `choose_video()`.
- Repeated database update loops in `select_all()` and `unselect_all()`.
- Repeated Playwright `try/except: pass` patterns in browser/analyzer code.

These are not urgent, but they are good candidates for small helper methods after functional cleanup.

## 6. Large Files (>300 Lines)

| File | Lines | Notes |
| --- | ---: | --- |
| `app/ui/main_window.py` | 567 | Too much responsibility: layout, UI events, post state sync, group selection, service calls. Contains duplicate right panel. |
| `app/database/db.py` | 373 | Schema creation and all DB operations in one global singleton module. |

Near-large files:

- `app/services/group_scanner.py`: 205 lines; still manageable, but mixes navigation, scrolling, filtering, parsing, and persistence.

## 7. Circular Imports

No circular imports were detected in the local `app.*` import graph.

Current direction is mostly:

```text
UI -> services -> browser/database
```

That direction is healthy, but global singleton initialization increases implicit coupling. Future circular import risk is highest if lower-level services start importing UI helpers or if `database` starts importing model/service modules.

## 8. Database Schema

The active runtime database is `data/facebook.db`, because `app/database/db.py` connects to:

```python
sqlite3.connect("data/facebook.db", check_same_thread=False)
```

### Active Schema: `data/facebook.db`

#### `accounts`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Primary key. |
| `name` | `TEXT` | Account name. |
| `profile_path` | `TEXT` | Browser profile path. |
| `created_at` | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | Created timestamp. |

#### `groups`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Primary key. |
| `account_id` | `INTEGER` | No declared foreign key in active schema. |
| `name` | `TEXT` | Group display name. |
| `url` | `TEXT UNIQUE` | Used for deduplication. |
| `group_uid` | `TEXT` | Present but not populated. |
| `members` | `TEXT` | Human-readable member string. |
| `members_count` | `INTEGER DEFAULT 0` | Present but not populated. |
| `privacy` | `TEXT` | Intended privacy value. |
| `category` | `TEXT` | Currently receives privacy in `update_group_info()`. |
| `selected` | `INTEGER DEFAULT 1` | Selection state. |
| `active` | `INTEGER DEFAULT 1` | Present but not used. |
| `can_post` | `INTEGER DEFAULT 1` | Present but not used. |
| `last_scan` | `TIMESTAMP` | Set when groups are saved. |
| `last_publish` | `TIMESTAMP` | Present but not used. |
| `created_at` | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | Created timestamp. |

Important issue: `Database.update_group_info(group_id, name, members, privacy)` updates `category=?` with the `privacy` argument and does not update the `privacy` column. The UI reads both `privacy` and `category`, so analyzed privacy likely appears under Category instead of Privacy.

#### `publish_history`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Primary key. |
| `group_id` | `INTEGER` | No declared foreign key in active schema. |
| `post_id` | `INTEGER` | No declared foreign key in active schema. |
| `status` | `TEXT` | Publish status. |
| `message` | `TEXT` | Message/error text. |
| `published_at` | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | Timestamp. |

`add_history()` does not accept `post_id`, so `post_id` remains unused/null in current app flow.

#### `posts`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Primary key. |
| `title` | `TEXT` | Post title. |
| `content` | `TEXT` | Post content. |
| `image_path` | `TEXT` | Optional image path. |
| `video_path` | `TEXT` | Optional video path. |
| `youtube_url` | `TEXT` | Optional YouTube URL. |
| `created_at` | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | Created timestamp. |

No current code writes to `posts`.

#### `schedules`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Primary key. |
| `post_id` | `INTEGER` | No declared foreign key in active schema. |
| `start_time` | `TEXT` | Schedule start. |
| `delay_seconds` | `INTEGER` | Delay between groups. |
| `repeat_every` | `INTEGER` | Repeat interval. |
| `enabled` | `INTEGER DEFAULT 1` | Schedule enabled flag. |

No current code reads or writes `schedules`.

#### `settings`

| Column | Type | Notes |
| --- | --- | --- |
| `key` | `TEXT PRIMARY KEY` | Setting key. |
| `value` | `TEXT` | Setting value. |

Settings methods exist but are not currently used.

### Other Database Files

`database.db`:

- Legacy schema with only `groups(id TEXT PRIMARY KEY, name, url, members, selected, last_post)`.
- Not used by current code.

`app/database/facebook_publisher.db`:

- Older/alternate schema with foreign keys and indexes.
- Not used by current code.
- Contains useful design ideas missing from active schema, such as `idx_groups_url`, `idx_publish_history`, and foreign key declarations.

## 9. Playwright Flow

### Browser Lifecycle

`app/browser/browser_manager.py` owns Playwright:

1. `browser.get_page()` checks `is_running()`.
2. If needed, `browser.start()` calls `sync_playwright().start()`.
3. Chromium launches with `launch_persistent_context()`.
4. User data is stored at `profiles/facebook`.
5. Browser is visible: `headless=False`.
6. Viewport is fixed to `1400x900`.
7. First page is reused or a new page is created.

### Login Flow

`facebook.login()`:

1. Ensures browser is running.
2. Navigates to `https://www.facebook.com/groups/feed/`.
3. Relies on the persistent profile for login/session state.

### Scan Groups Flow

`facebook.scan_groups()` -> `scanner.scan()`:

1. Ensures browser is running.
2. Opens Facebook groups feed if not already on a groups URL.
3. Attempts to click a link with role `link` and name `See all`.
4. Scrolls to the bottom until `document.body.scrollHeight` stops changing.
5. Extracts all anchors matching `a[href*='/groups/']`.
6. Filters navigation/discovery/create/feed URLs.
7. Cleans link text into a group name.
8. Clears all existing groups with `db.clear_groups()`.
9. Saves each unique group URL with `db.save_group(account_id=1, ...)`.

Risks:

- Selectors are language-dependent and may fail outside English UI.
- `clear_groups()` deletes all groups before scan results are validated.
- Blocking Playwright operations run on the UI thread.
- `account_id=1` is hardcoded; account support is only partially modeled.

### Analyze Groups Flow

`facebook.analyze_groups()` -> `analyzer.analyze()`:

1. Loads all DB groups.
2. Navigates to each group URL.
3. Reads first `h1` as title when available.
4. Searches `body.inner_text()` for member-related lines in English/Arabic.
5. Checks page HTML for `Private group` or `Public group`.
6. Calls `db.update_group_info()`.

Important bug:

- Analyzer passes `privacy`, but DB writes it into `category`, not `privacy`.

### Publish Flow

`MainWindow.publish_post()` -> `publisher.publish()`:

1. Copies UI title/content/media/delay fields into `post_service`.
2. Verifies post has content or media.
3. Loads selected groups from DB.
4. Opens each group URL.
5. Waits 2 seconds.

Current limitation:

- It does not create Facebook posts yet.
- It does not upload media.
- It does not use the configured delay.
- It does not write `posts`, `schedules`, or `publish_history`.

## 10. UI Architecture

The UI is a single CustomTkinter desktop window:

```text
MainWindow (ctk.CTk)
├── Toolbar
│   ├── Login
│   ├── Scan Groups
│   ├── Analyze Groups
│   ├── Select All
│   ├── Unselect All
│   ├── Publish
│   └── Status label
└── Body
    ├── Left panel
    │   └── GroupsTable
    └── Right panel
        ├── Post title entry
        ├── Post text box
        ├── YouTube URL entry
        ├── Choose Image
        ├── Choose Video
        └── Delay entry
```

### `MainWindow`

Responsibilities:

- Builds the complete UI.
- Calls Facebook service actions directly.
- Reads and writes `post_service`.
- Reads and writes DB selection state.
- Refreshes `GroupsTable`.
- Handles file dialogs.
- Updates status text.

Architectural issue:

- `MainWindow` is doing layout, controller, and state synchronization work in one file. This is the main reason it has grown to 567 lines.

### `GroupsTable`

`GroupsTable` is a simple scrollable frame that renders rows as labels.

Limitations:

- Selection is displayed as text (`☑`/`☐`) rather than interactive checkboxes.
- Row state is not bound to group IDs.
- Per-row selection cannot be toggled from the table.
- Fixed column widths may clip long group names.

### Threading/UI Responsiveness

`Worker` exists but is not used. Scan, analyze, and publish all run synchronously from button callbacks. Because Playwright operations can take seconds or minutes, the UI can freeze during automation.

## 11. Refactoring Recommendations

Priority order:

1. Clean repository/runtime artifacts.
   - Stop tracking `profiles/facebook`, `venv`, `__pycache__`, and SQLite runtime files.
   - Add `profiles/` to `.gitignore`.
   - Keep a sample profile path/config, not the real browser profile.

2. Consolidate dependencies.
   - Move `requirements_backup.txt` contents into `requirements.txt`.
   - Remove unused direct dependencies or document why they are planned.

3. Fix the database schema mismatch.
   - Change `update_group_info()` to update `privacy=?` instead of `category=?`, or pass a true category separately.
   - Decide which DB schema is canonical: `data/facebook.db` vs `app/database/facebook_publisher.db`.
   - Add migrations or a reset strategy.
   - Add indexes and foreign keys if publish history/posts will be used.

4. Remove duplicate UI construction.
   - Delete the first duplicate right-panel block in `MainWindow.__init__`.
   - Extract UI construction into methods such as `_build_toolbar()`, `_build_groups_panel()`, and `_build_post_editor()`.

5. Move long-running work off the UI thread.
   - Use `Worker` or a safer queue/`after()` pattern.
   - Ensure UI updates happen on the Tk main thread.
   - Disable buttons while scan/analyze/publish is running.

6. Replace global singletons with explicit dependencies.
   - Introduce an application context or pass `db`, `browser`, and services into `MainWindow`.
   - This will make testing and shutdown cleaner.

7. Separate Playwright automation from persistence.
   - Let scanner return parsed group objects.
   - Let a service/repository layer decide when to clear/save groups.
   - Avoid deleting all saved groups until a scan has succeeded.

8. Make publishing explicit and observable.
   - Persist post drafts into `posts`.
   - Use configured delay.
   - Record per-group publish attempts in `publish_history`.
   - Update `last_publish`.
   - Add failure messages and retries.

9. Improve UI group selection.
   - Render real checkboxes bound to group IDs.
   - Save changes per row or with an Apply button.
   - Add filtering/search for large group lists.

10. Add tests around pure logic.
   - Unit-test URL filtering and group-name cleaning.
   - Unit-test DB operations using temporary SQLite files.
   - Keep Playwright tests separate because Facebook UI is dynamic and login-dependent.

11. Add basic documentation.
   - Fill `README.md` with setup, Playwright browser install, login/profile behavior, and known limitations.
   - Document that the app currently opens groups but does not complete the Facebook post creation flow.

## Key Findings Checklist

- Folder structure: analyzed.
- All Python files: listed.
- Dependency graph: documented.
- Dead code: identified.
- Duplicate code: identified in `app/ui/main_window.py`.
- Large files: `app/ui/main_window.py`, `app/database/db.py`.
- Circular imports: none detected.
- Database schema: documented for all SQLite files.
- Playwright flow: documented.
- UI architecture: documented.
- Refactoring recommendations: listed in priority order.
