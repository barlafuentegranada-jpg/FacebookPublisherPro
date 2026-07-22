import customtkinter as ctk

from app.ui.theme import colors, fonts, styles
from app.ui.widgets.status_badge import StatusBadge


class Header(ctk.CTkFrame):
    """Top application header for the v2 UI shell."""

    def __init__(
        self,
        master,
        title="Facebook Publisher",
        subtitle="UI v2",
        **kwargs
    ):
        super().__init__(
            master,
            corner_radius=styles.Radius.NONE,
            fg_color=colors.SURFACE,
            **kwargs
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=fonts.HEADER_TITLE,
            text_color=colors.TEXT,
            anchor="w",
        )
        self.title_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Spacing.LG, styles.Radius.NONE),
        )

        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=fonts.SMALL,
            text_color=colors.TEXT_MUTED,
            anchor="w",
        )
        self.subtitle_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Spacing.LG),
        )

        self.account_label = StatusBadge(
            self,
            text="No Active Account",
            variant="warning",
        )
        self.account_label.grid(
            row=0,
            column=1,
            padx=(styles.Spacing.SM, styles.Padding.PAGE_X),
            pady=(styles.Spacing.LG, styles.Spacing.XS),
            sticky="e",
        )

        self.login_label = StatusBadge(
            self,
            text="Unknown",
            variant="neutral",
        )
        self.login_label.grid(
            row=1,
            column=1,
            padx=(styles.Spacing.SM, styles.Padding.PAGE_X),
            pady=(styles.Radius.NONE, styles.Spacing.LG),
            sticky="e",
        )

    def set_title(self, title, subtitle=None):
        self.title_label.configure(text=title)

        if subtitle is not None:
            self.subtitle_label.configure(text=subtitle)

    def set_account(self, account):
        if account is None:
            self.account_label.set_status("No Active Account", "warning")
            self.login_label.set_status("Unknown", "neutral")
            return

        status = account.get("login_status") or "Unknown"
        variant = "success" if status == "Logged in" else "warning"

        self.account_label.set_status(account.get("name") or "Active Account", "info")
        self.login_label.set_status(status, variant)
