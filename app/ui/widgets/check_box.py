import customtkinter as ctk

from app.ui.theme import styles


class CheckBox(ctk.CTkCheckBox):
    def __init__(self, master, **kwargs):
        options = styles.CHECKBOX.copy()
        options.update(kwargs)
        super().__init__(master, **options)
