import customtkinter as ctk

from app.ui.theme import colors, styles
from app.ui.widgets import SectionPanel, SectionTitle, TableText


class HistoryPage(ctk.CTkFrame):
    route = "history"
    title = "History"

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        panel = SectionPanel(self)
        panel.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=styles.Padding.PAGE_Y,
        )

        SectionTitle(panel, text="History").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )
        TableText(panel, text="Account and publishing history will be organized here.").grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )
