import customtkinter as ctk

from app.ui.theme import colors, fonts, styles


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, value="0", caption="", **kwargs):
        super().__init__(
            master,
            height=112,
            corner_radius=styles.CARD_RADIUS,
            fg_color=colors.SURFACE,
            border_color=colors.BORDER,
            border_width=styles.BORDER_WIDTH,
            **kwargs
        )
        self.grid_propagate(False)

        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=fonts.SMALL_BOLD,
            text_color=colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=180,
        )
        self.title_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.XS),
        )

        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=fonts.TITLE,
            text_color=colors.TEXT,
            anchor="w",
        )
        self.value_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
        )

        self.caption_label = ctk.CTkLabel(
            self,
            text=caption,
            font=fonts.SMALL,
            text_color=colors.TEXT_MUTED,
            anchor="w",
        )
        self.caption_label.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.XS, styles.Padding.FRAME_Y),
        )

    def set_value(self, value, caption=None):
        self.value_label.configure(text=value)

        if caption is not None:
            self.caption_label.configure(text=caption)
