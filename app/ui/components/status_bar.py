import customtkinter as ctk

from app.ui.theme import colors, fonts, styles


class StatusBar(ctk.CTkFrame):
    """Bottom status strip for short app state messages."""

    def __init__(self, master, initial_status="Ready", **kwargs):
        super().__init__(
            master,
            corner_radius=styles.Radius.NONE,
            height=styles.STATUS_BAR_HEIGHT,
            fg_color=colors.SURFACE,
            **kwargs
        )

        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self,
            text=initial_status,
            font=fonts.SMALL,
            text_color=colors.TEXT_MUTED,
            anchor="w",
        )
        self.status_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
        )

    def set_status(self, text):
        self.status_label.configure(text=text)

    def set_context(self, account=None, browser_status="Closed"):
        account_name = account["name"] if account else "No active account"
        self.set_status(f"Current account: {account_name} | Browser: {browser_status}")
