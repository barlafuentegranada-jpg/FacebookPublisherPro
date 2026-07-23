from datetime import datetime

import customtkinter as ctk

from app.controllers.accounts_controller import AccountsController
from app.ui.theme import colors, fonts, styles
from app.ui.widgets import SectionPanel, SectionTitle, StatCard, StatusBadge, TableText


class DashboardPage(ctk.CTkFrame):
    route = "dashboard"
    title = "Dashboard"

    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)
        self.controller = controller or AccountsController()
        self._column_count = 0
        self._resize_job = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        SectionTitle(self, text="Dashboard").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Padding.PAGE_Y, styles.Spacing.MD),
        )

        self.body = ctk.CTkScrollableFrame(
            self,
            fg_color=colors.TRANSPARENT,
            corner_radius=styles.Radius.NONE,
        )
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

        self.cards = {}
        self.sections = []
        self._build_card_section(
            "Platform Overview",
            [
                ("total_accounts", "Total Accounts"),
                ("facebook_accounts", "Facebook Accounts"),
                ("instagram_accounts", "Instagram Accounts"),
                ("telegram_accounts", "Telegram Accounts"),
                ("total_targets", "Total Targets"),
                ("accounts_requiring_review", "Accounts Requiring Review"),
            ],
        )
        self._build_card_section(
            "Publishing Overview",
            [
                ("successful_posts", "Successful Publications"),
                ("publish_attempts", "Publish Attempts"),
                ("success_rate", "Success Rate"),
                ("total_posts", "Total Posts"),
                ("ready_posts", "Ready Posts"),
                ("failed_posts", "Failed Publications"),
                ("rate_limited_attempts", "Rate-Limited Attempts"),
            ],
        )
        self._build_card_section(
            "Campaign Overview",
            [
                ("total_campaigns", "Total Campaigns"),
                ("ready_campaigns", "Ready Campaigns"),
                ("running_campaigns", "Running Campaigns"),
                ("completed_campaigns", "Completed Campaigns"),
                ("campaign_success_rate", "Campaign Success Rate"),
            ],
        )

        self._build_account_targets()
        self._build_recent_activity()
        self.bind("<Configure>", self._schedule_reflow)
        self.refresh()

    def _build_card_section(self, title, definitions):
        row = len(self.sections)
        section = ctk.CTkFrame(self.body, fg_color=colors.TRANSPARENT)
        section.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Spacing.MD),
        )
        SectionTitle(section, text=title).grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(styles.Spacing.SM, styles.Spacing.MD),
        )
        grid = ctk.CTkFrame(section, fg_color=colors.TRANSPARENT)
        grid.grid(row=1, column=0, sticky="ew")
        section.grid_columnconfigure(0, weight=1)
        cards = []

        for key, label in definitions:
            card = StatCard(grid, title=label)
            self.cards[key] = card
            cards.append(card)

        self.sections.append((grid, cards))

    def _build_account_targets(self):
        row = len(self.sections)
        self.accounts_panel = SectionPanel(self.body)
        self.accounts_panel.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Spacing.MD),
        )
        self.accounts_panel.grid_columnconfigure(0, weight=1)
        SectionTitle(self.accounts_panel, text="Account Targets").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Padding.FRAME_Y,
        )
        self.accounts_list = ctk.CTkFrame(self.accounts_panel, fg_color=colors.TRANSPARENT)
        self.accounts_list.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )

    def _build_recent_activity(self):
        row = len(self.sections) + 1
        self.activity_panel = SectionPanel(self.body)
        self.activity_panel.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.PAGE_Y),
        )
        self.activity_panel.grid_columnconfigure(0, weight=1)
        SectionTitle(self.activity_panel, text="Recent Activity").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Padding.FRAME_Y,
        )
        self.activity_list = ctk.CTkFrame(self.activity_panel, fg_color=colors.TRANSPARENT)
        self.activity_list.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )

    def refresh(self):
        stats = self.controller.dashboard_stats()

        for key, card in self.cards.items():
            value = stats.get(key, 0)

            if key in {"success_rate", "campaign_success_rate"}:
                value = f"{value}%"

            card.set_value(str(value))

        self._render_account_targets(stats.get("account_target_counts") or [])
        self._render_recent_activity(stats.get("recent_activity") or [])
        self.after_idle(lambda: self._reflow(self.winfo_width()))

    def _schedule_reflow(self, event):
        if self._resize_job:
            self.after_cancel(self._resize_job)

        self._resize_job = self.after(80, lambda: self._reflow(event.width))

    def _reflow(self, width):
        try:
            window_width = int(self.winfo_toplevel().geometry().split("x", 1)[0])
        except (TypeError, ValueError):
            window_width = width

        columns = 4 if window_width >= 1366 else 3 if window_width >= 1200 else 2

        if columns == self._column_count:
            return

        self._column_count = columns

        for grid, cards in self.sections:
            for column in range(4):
                grid.grid_columnconfigure(column, weight=1 if column < columns else 0, uniform="dashboard_cards")

            for index, card in enumerate(cards):
                card.grid(
                    row=index // columns,
                    column=index % columns,
                    sticky="nsew",
                    padx=styles.Spacing.SM,
                    pady=styles.Spacing.SM,
                )

    def _render_account_targets(self, rows):
        self._clear(self.accounts_list)
        headers = ["Account", "Platform", "Targets", "Selected"]

        for column, header in enumerate(headers):
            self.accounts_list.grid_columnconfigure(column, weight=3 if column == 0 else 1)
            TableText(self.accounts_list, text=header, font=fonts.SMALL_BOLD).grid(
                row=0,
                column=column,
                sticky="ew",
                padx=styles.Spacing.SM,
                pady=styles.Spacing.XS,
            )

        if not rows:
            TableText(self.accounts_list, text="No account targets yet.", text_color=colors.TEXT_MUTED).grid(
                row=1,
                column=0,
                columnspan=4,
                sticky="ew",
                pady=styles.Spacing.MD,
            )
            return

        for row_index, item in enumerate(rows, start=1):
            values = [
                item.get("account") or "",
                item.get("platform") or "",
                item.get("target_count") or 0,
                item.get("selected_count") or 0,
            ]

            for column, value in enumerate(values):
                TableText(self.accounts_list, text=str(value), font=fonts.SMALL).grid(
                    row=row_index,
                    column=column,
                    sticky="ew",
                    padx=styles.Spacing.SM,
                    pady=styles.Spacing.XS,
                )

    def _render_recent_activity(self, rows):
        self._clear(self.activity_list)
        headers = ["Time", "Platform", "Account", "Target", "Status"]

        for column, header in enumerate(headers):
            self.activity_list.grid_columnconfigure(column, weight=2 if column in {2, 3} else 1)
            TableText(self.activity_list, text=header, font=fonts.SMALL_BOLD).grid(
                row=0,
                column=column,
                sticky="ew",
                padx=styles.Spacing.SM,
                pady=styles.Spacing.XS,
            )

        if not rows:
            TableText(self.activity_list, text="No publishing activity yet.", text_color=colors.TEXT_MUTED).grid(
                row=1,
                column=0,
                columnspan=5,
                sticky="ew",
                pady=styles.Spacing.MD,
            )
            return

        for row_index, item in enumerate(rows[:10], start=1):
            values = [
                self._compact_time(
                    item.get("finished_at") or item.get("started_at") or item.get("created_at")
                ),
                (item.get("platform") or "facebook").title(),
                item.get("account_name") or str(item.get("account_id") or ""),
                item.get("group_name") or str(item.get("group_id") or ""),
            ]

            for column, value in enumerate(values):
                TableText(self.activity_list, text=str(value)[:48], font=fonts.SMALL).grid(
                    row=row_index,
                    column=column,
                    sticky="ew",
                    padx=styles.Spacing.SM,
                    pady=styles.Spacing.XS,
                )

            status = item.get("status") or ""
            StatusBadge(
                self.activity_list,
                text=status,
                variant=self._status_variant(status),
                font=fonts.SMALL,
            ).grid(
                row=row_index,
                column=4,
                sticky="w",
                padx=styles.Spacing.SM,
                pady=styles.Spacing.XS,
            )

    def _compact_time(self, value):
        text = str(value or "")

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%m-%d %H:%M")
        except ValueError:
            return text[:16]

    def _status_variant(self, status):
        if status == "Success":
            return "success"
        if status in {"Failed", "PermissionDenied", "Checkpoint", "Blocked", "RateLimited", "ValidationFailed"}:
            return "danger"
        if status in {"Stopped", "Skipped"}:
            return "warning"
        return "neutral"

    def _clear(self, parent):
        for child in parent.winfo_children():
            child.destroy()
