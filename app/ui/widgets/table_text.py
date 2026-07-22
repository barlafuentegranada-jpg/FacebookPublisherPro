import customtkinter as ctk

from app.ui.theme import colors, fonts


class TableText(ctk.CTkLabel):
    def __init__(self, master, **kwargs):
        options = {
            "font": fonts.BODY,
            "text_color": colors.TEXT,
            "anchor": "w",
        }
        options.update(kwargs)
        super().__init__(master, **options)
