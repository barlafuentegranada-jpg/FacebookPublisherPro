import customtkinter as ctk

from app.ui.theme import colors, fonts, styles
from app.ui.widgets.danger_button import DangerButton
from app.ui.widgets.primary_button import PrimaryButton
from app.ui.widgets.secondary_button import SecondaryButton
from app.ui.widgets.status_badge import StatusBadge
from app.ui.widgets.table_text import TableText


class AccountCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        account,
        on_rename=None,
        on_login=None,
        on_set_active=None,
        on_open_browser=None,
        on_refresh_status=None,
        on_reset_profile=None,
        on_remove=None,
        **kwargs
    ):
        super().__init__(
            master,
            corner_radius=styles.Radius.MD,
            fg_color=colors.SURFACE,
            border_color=colors.BORDER,
            border_width=styles.BORDER_WIDTH,
            **kwargs
        )

        self.account = account
        self.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(self, fg_color=colors.TRANSPARENT)
        title_row.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )
        title_row.grid_columnconfigure(0, weight=1)

        TableText(
            title_row,
            text=account["name"],
            font=fonts.SECTION_TITLE,
        ).grid(row=0, column=0, sticky="ew")

        active_text = "Active" if account.get("active") else "Inactive"
        active_variant = "success" if account.get("active") else "neutral"
        StatusBadge(
            title_row,
            text=active_text,
            variant=active_variant,
        ).grid(row=0, column=1, padx=(styles.Spacing.SM, styles.Radius.NONE))

        login_variant = "success" if account.get("login_status") == "Logged in" else "warning"
        StatusBadge(
            title_row,
            text=account.get("login_status") or "Unknown",
            variant=login_variant,
        ).grid(row=0, column=2, padx=(styles.Spacing.SM, styles.Radius.NONE))

        details = [
            ("Profile", account.get("profile_path") or ""),
            ("Last Login", account.get("last_login") or "Never"),
            ("Groups", str(account.get("groups_count") or 0)),
        ]

        for index, (label, value) in enumerate(details, start=1):
            TableText(
                self,
                text=f"{label}: {value}",
                font=fonts.SMALL,
                text_color=colors.TEXT_MUTED,
            ).grid(
                row=index,
                column=0,
                sticky="ew",
                padx=styles.Padding.FRAME_X,
                pady=styles.Spacing.XS,
            )

        actions = ctk.CTkFrame(self, fg_color=colors.TRANSPARENT)
        actions.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.SM, styles.Padding.FRAME_Y),
        )

        action_buttons = [
            (SecondaryButton, "Rename", on_rename),
            (PrimaryButton, "Open Manual Login", on_login),
            (SecondaryButton, "Set Active", on_set_active),
            (SecondaryButton, "Open Browser", on_open_browser),
            (SecondaryButton, "Check Login", on_refresh_status),
            (SecondaryButton, "Reset Login Profile", on_reset_profile),
            (DangerButton, "Remove", on_remove),
        ]

        for index, (button_class, text, command) in enumerate(action_buttons):
            button_class(
                actions,
                text=text,
                command=lambda callback=command: callback(account["id"]) if callback else None,
            ).grid(row=0, column=index, padx=(styles.Radius.NONE, styles.Spacing.SM))
