from datetime import datetime
import tkinter as tk

import customtkinter as ctk

from app.controllers.history_controller import HistoryController
from app.ui.theme import colors, fonts, styles
from app.ui.widgets import (
    FieldLabel,
    SearchBox,
    SecondaryButton,
    SectionPanel,
    SectionTitle,
    SelectBox,
    StatusBadge,
    TableText,
)


class HistoryPage(ctk.CTkFrame):
    route = "history"
    title = "History"
    COLUMNS = [
        ("Campaign", 130),
        ("Platform", 100),
        ("Account", 170),
        ("Target", 190),
        ("Post", 160),
        ("Status", 140),
        ("Message", 320),
        ("Started", 145),
        ("Finished", 145),
        ("Published URL", 340),
    ]

    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)
        self.controller = controller or HistoryController()
        self.platform_var = ctk.StringVar(value="All")
        self.account_var = ctk.StringVar(value="All")
        self.status_var = ctk.StringVar(value="All")
        self.date_var = ctk.StringVar()
        self.campaign_var = ctk.StringVar(value="All")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_filters()
        self._build_table()
        self.refresh()

    def refresh(self):
        self._sync_accounts()
        self._sync_campaigns()
        self._render(self.controller.load())

    def _build_filters(self):
        panel = SectionPanel(self)
        panel.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Padding.PAGE_Y, styles.Spacing.MD),
        )

        for column in range(7):
            panel.grid_columnconfigure(column, weight=1)

        SectionTitle(panel, text="Publish History").grid(
            row=0,
            column=0,
            columnspan=7,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Padding.FRAME_Y,
        )

        self.platform_select = SelectBox(panel, values=self.controller.platforms(), variable=self.platform_var, command=lambda _value: self._apply())
        self._field(panel, 1, "Platform", self.platform_select)

        self.account_select = SelectBox(panel, values=["All"], variable=self.account_var, command=lambda _value: self._apply())
        self._field(panel, 2, "Account", self.account_select)

        self.status_select = SelectBox(panel, values=self.controller.statuses(), variable=self.status_var, command=lambda _value: self._apply())
        self._field(panel, 3, "Status", self.status_select)

        self.date_input = SearchBox(panel, textvariable=self.date_var, placeholder_text="YYYY-MM-DD")
        self.date_input.bind("<KeyRelease>", lambda _event: self._apply())
        self._field(panel, 4, "Date", self.date_input)

        self.campaign_select = SelectBox(panel, values=["All"], variable=self.campaign_var, command=lambda _value: self._apply())
        self._field(panel, 5, "Campaign", self.campaign_select)

        SecondaryButton(panel, text="Refresh", command=self.refresh).grid(
            row=2,
            column=6,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.SM, styles.Padding.FRAME_Y),
        )

    def _build_table(self):
        panel = SectionPanel(self)
        panel.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.PAGE_Y),
        )
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        table_shell = ctk.CTkFrame(panel, fg_color=colors.TRANSPARENT)
        table_shell.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )
        table_shell.grid_columnconfigure(0, weight=1)
        table_shell.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            table_shell,
            background="#171a1f",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical = ctk.CTkScrollbar(table_shell, orientation="vertical", command=self.canvas.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ctk.CTkScrollbar(table_shell, orientation="horizontal", command=self.canvas.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)

        self.rows = ctk.CTkFrame(self.canvas, fg_color=colors.SURFACE)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.rows, anchor="nw")
        self.rows.bind("<Configure>", self._sync_scroll_region)

        for index, (label, width) in enumerate(self.COLUMNS):
            self.rows.grid_columnconfigure(index, minsize=width)
            TableText(
                self.rows,
                text=label,
                width=width,
                font=fonts.SMALL_BOLD,
            ).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=styles.Spacing.XS,
                pady=styles.Spacing.SM,
            )

    def _field(self, panel, column, label, widget):
        FieldLabel(panel, text=label).grid(
            row=1,
            column=column,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.XS),
        )
        widget.grid(
            row=2,
            column=column,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )

    def _sync_accounts(self):
        values = ["All"] + [
            f"{account['id']} | {account['name']}"
            for account in self.controller.accounts()
        ]
        self.account_select.configure(values=values)

        if self.account_var.get() not in values:
            self.account_var.set("All")

    def _sync_campaigns(self):
        values = ["All"] + [
            f"{campaign['id']} | {campaign['name']}"
            for campaign in self.controller.campaigns()
        ]
        self.campaign_select.configure(values=values)

        if self.campaign_var.get() not in values:
            self.campaign_var.set("All")

    def _apply(self):
        rows = self.controller.set_filters(
            self.platform_var.get(),
            self.account_var.get(),
            self.status_var.get(),
            self.date_var.get(),
            self.campaign_var.get(),
        )
        self._render(rows)

    def _render(self, rows):
        for child in self.rows.winfo_children():
            if int(child.grid_info().get("row", 0)) > 0:
                child.destroy()

        if not rows:
            TableText(
                self.rows,
                text="No publish history found.",
                text_color=colors.TEXT_MUTED,
            ).grid(row=1, column=0, columnspan=len(self.COLUMNS), sticky="ew", pady=styles.Spacing.MD)
            self.rows.update_idletasks()
            self._sync_scroll_region()
            return

        for row_index, item in enumerate(rows, start=1):
            values = [
                item.get("campaign_name") or (str(item.get("campaign_id")) if item.get("campaign_id") else ""),
                item.get("platform") or "facebook",
                item.get("account_name") or str(item.get("account_id") or ""),
                item.get("group_name") or str(item.get("group_id") or ""),
                item.get("post_title") or str(item.get("post_id") or ""),
                item.get("status") or "",
                item.get("message") or "",
                self._compact_timestamp(item.get("started_at")),
                self._compact_timestamp(item.get("finished_at")),
                item.get("published_post_url") or "",
            ]

            for column_index, value in enumerate(values):
                if column_index == 5:
                    StatusBadge(
                        self.rows,
                        text=value,
                        variant=self._variant(value),
                        font=fonts.SMALL,
                    ).grid(row=row_index, column=column_index, sticky="ew", padx=styles.Spacing.XS, pady=styles.Spacing.XS)
                else:
                    full_value = str(value)
                    visible_value = self._truncate(full_value, 70 if column_index in {6, 9} else 34)
                    cell = TableText(
                        self.rows,
                        text=visible_value,
                        width=self.COLUMNS[column_index][1],
                        font=fonts.SMALL,
                        text_color=colors.TEXT if column_index < 6 else colors.TEXT_MUTED,
                        anchor="w",
                    )
                    cell.grid(row=row_index, column=column_index, sticky="ew", padx=styles.Spacing.XS, pady=styles.Spacing.XS)

                    if visible_value != full_value:
                        cell.configure(cursor="hand2")
                        cell.bind(
                            "<Button-1>",
                            lambda _event, title=self.COLUMNS[column_index][0], text=full_value: self._show_details(title, text),
                        )

        self.rows.update_idletasks()
        self._sync_scroll_region()

    def _sync_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _truncate(self, value, limit):
        if len(value) <= limit:
            return value
        return value[: max(1, limit - 3)] + "..."

    def _compact_timestamp(self, value):
        text = str(value or "")

        if not text:
            return ""

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return text[:16]

    def _show_details(self, title, value):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("620x260")
        dialog.transient(self.winfo_toplevel())
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)
        SectionTitle(dialog, text=title).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=styles.Padding.PAGE_Y,
        )
        text_box = ctk.CTkTextbox(dialog, wrap="word")
        text_box.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.PAGE_Y),
        )
        text_box.insert("1.0", value)
        text_box.configure(state="disabled")

    def _variant(self, status):
        if status == "Success":
            return "success"

        if status in ["Failed", "PermissionDenied", "Checkpoint", "Blocked", "RateLimited", "ValidationFailed"]:
            return "danger"

        if status in ["Stopped", "Skipped"]:
            return "warning"

        if status == "Validated":
            return "info"

        return "neutral"
