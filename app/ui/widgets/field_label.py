import customtkinter as ctk

from app.ui.theme import colors, fonts


class FieldLabel(ctk.CTkLabel):
    def __init__(self, master, **kwargs):
        options = {
            "font": fonts.SMALL_BOLD,
            "text_color": colors.TEXT_MUTED,
            "anchor": "w",
        }
        options.update(kwargs)
        super().__init__(master, **options)
