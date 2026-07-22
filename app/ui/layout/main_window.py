import customtkinter as ctk

from app.controllers.accounts_controller import AccountsController
from app.ui.components import Header, Sidebar, StatusBar
from app.ui.layout.router import Router
from app.ui.pages import (
    AccountsPage,
    CampaignsPage,
    DashboardPage,
    GroupsPage,
    HistoryPage,
    PostsPage,
    SettingsPage,
)
from app.ui.theme import colors, styles


class MainWindow(ctk.CTk):
    """Standalone v2 UI shell.

    This class is intentionally not wired into `app/main.py` yet, so the
    current application continues to launch the existing UI.
    """

    def __init__(self):
        super().__init__()

        self.title("Facebook Publisher Pro - UI v2")
        self.geometry(f"{styles.WINDOW_WIDTH}x{styles.WINDOW_HEIGHT}")
        self.minsize(styles.MIN_WINDOW_WIDTH, styles.MIN_WINDOW_HEIGHT)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=colors.BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.accounts_controller = AccountsController()

        self.grid_columnconfigure(0, minsize=styles.SIDEBAR_WIDTH)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.sidebar = Sidebar(self, on_navigate=self.navigate)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")

        self.header = Header(
            self,
            title="Dashboard",
            subtitle="Facebook Publisher Pro",
        )
        self.header.grid(row=0, column=1, sticky="ew")

        self.page_container = ctk.CTkFrame(
            self,
            corner_radius=styles.Radius.NONE,
            fg_color=colors.BACKGROUND,
        )
        self.page_container.grid(row=1, column=1, sticky="nsew")
        self.page_container.grid_columnconfigure(0, weight=1)
        self.page_container.grid_rowconfigure(0, weight=1)

        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=1, sticky="ew")

        self.router = Router(
            self.page_container,
            on_route_changed=self._on_route_changed,
        )

        self._register_pages()
        self.navigate("dashboard")
        self._refresh_account_context()

    def _register_pages(self):
        page_specs = [
            ("dashboard", lambda: DashboardPage(self.page_container, controller=self.accounts_controller)),
            (
                "accounts",
                lambda: AccountsPage(
                    self.page_container,
                    controller=self.accounts_controller,
                    on_accounts_changed=self._refresh_account_context,
                ),
            ),
            ("groups", lambda: GroupsPage(self.page_container)),
            ("posts", lambda: PostsPage(self.page_container)),
            ("campaigns", lambda: CampaignsPage(self.page_container)),
            ("history", lambda: HistoryPage(self.page_container)),
            ("settings", lambda: SettingsPage(self.page_container)),
        ]

        nav_items = []

        for _route, factory in page_specs:
            page = factory()
            self.router.register(page.route, page)
            nav_items.append(
                {
                    "route": page.route,
                    "title": page.title,
                }
            )

        self.sidebar.set_items(nav_items)

    def navigate(self, route):
        self.router.navigate(route)

    def _on_route_changed(self, route, page):
        self.sidebar.set_active(route)
        self.header.set_title(page.title, "Facebook Publisher Pro")
        if hasattr(page, "refresh"):
            page.refresh()
        self._refresh_account_context()

    def _refresh_account_context(self):
        context = self.accounts_controller.active_context()
        account = context["account"]
        browser_status = context["browser_status"]

        self.header.set_account(account)
        self.status_bar.set_context(account, browser_status)

    def _on_close(self):
        try:
            self.accounts_controller.shutdown_browser()
        finally:
            self.destroy()
