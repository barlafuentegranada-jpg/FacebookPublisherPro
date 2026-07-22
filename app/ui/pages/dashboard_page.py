import customtkinter as ctk

from app.controllers.accounts_controller import AccountsController
from app.ui.theme import colors, fonts, styles
from app.ui.widgets import SectionPanel, SectionTitle, StatCard, TableText


class DashboardPage(ctk.CTkFrame):
    route = "dashboard"
    title = "Dashboard"

    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)

        self.controller = controller or AccountsController()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        SectionTitle(
            self,
            text="Dashboard",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Padding.PAGE_Y, styles.Spacing.MD),
        )

        cards_panel = SectionPanel(self)
        cards_panel.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Spacing.MD),
        )

        for column in range(8):
            cards_panel.grid_columnconfigure(column, weight=1)

        self.total_accounts = StatCard(cards_panel, title="Total Accounts")
        self.logged_in = StatCard(cards_panel, title="Logged-in Accounts")
        self.total_groups = StatCard(cards_panel, title="Total Groups")
        self.selected_groups = StatCard(cards_panel, title="Selected Groups")
        self.publish_attempts = StatCard(cards_panel, title="Publish Attempts")
        self.total_posts = StatCard(cards_panel, title="Total Posts")
        self.draft_posts = StatCard(cards_panel, title="Draft Posts")
        self.ready_posts = StatCard(cards_panel, title="Ready Posts")

        cards = [
            self.total_accounts,
            self.logged_in,
            self.total_groups,
            self.selected_groups,
            self.publish_attempts,
            self.total_posts,
            self.draft_posts,
            self.ready_posts,
        ]

        for index, card in enumerate(cards):
            card.grid(
                row=0,
                column=index,
                sticky="ew",
                padx=styles.Spacing.SM,
                pady=styles.Padding.FRAME_Y,
            )

        self.accounts_panel = SectionPanel(self)
        self.accounts_panel.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Spacing.MD),
        )
        self.accounts_panel.grid_columnconfigure(0, weight=1)

        SectionTitle(
            self.accounts_panel,
            text="Account Groups",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )

        self.accounts_list = ctk.CTkFrame(self.accounts_panel, fg_color=colors.TRANSPARENT)
        self.accounts_list.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )
        self.accounts_list.grid_columnconfigure(0, weight=1)

        activity_panel = SectionPanel(self)
        activity_panel.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.PAGE_Y),
        )
        activity_panel.grid_columnconfigure(0, weight=1)

        SectionTitle(
            activity_panel,
            text="Recent Activity",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )

        TableText(
            activity_panel,
            text="Recent account, group, and publishing activity will appear here.",
            font=fonts.BODY,
            text_color=colors.TEXT_MUTED,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )

        self.refresh()

    def refresh(self):
        stats = self.controller.dashboard_stats()

        self.total_accounts.set_value(str(stats["total_accounts"]))
        self.logged_in.set_value(str(stats["logged_in_accounts"]))
        self.total_groups.set_value(str(stats["total_groups"]))
        self.selected_groups.set_value(str(stats["selected_groups"]))
        self.publish_attempts.set_value(str(stats["publish_attempts"]))
        self.total_posts.set_value(str(stats["total_posts"]))
        self.draft_posts.set_value(str(stats["draft_posts"]))
        self.ready_posts.set_value(str(stats["ready_posts"]))
        self._render_account_counts(stats["account_group_counts"])

    def _render_account_counts(self, account_counts):
        for child in self.accounts_list.winfo_children():
            child.destroy()

        if not account_counts:
            TableText(
                self.accounts_list,
                text="No accounts yet.",
                font=fonts.BODY,
                text_color=colors.TEXT_MUTED,
            ).grid(row=0, column=0, sticky="ew")
            return

        for row_index, item in enumerate(account_counts):
            account_name = item.get("account_name") or f"Account {item.get('account_id')}"
            group_count = item.get("group_count") or 0
            TableText(
                self.accounts_list,
                text=f"{account_name} | {group_count} groups",
                font=fonts.BODY,
                text_color=colors.TEXT,
            ).grid(
                row=row_index,
                column=0,
                sticky="ew",
                pady=styles.Spacing.XS,
            )
