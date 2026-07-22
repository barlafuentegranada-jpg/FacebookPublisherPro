import customtkinter as ctk

from app.ui.theme import styles


class SecondaryButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        options = styles.SECONDARY_BUTTON.copy()
        options.update(kwargs)
        super().__init__(master, **options)
