import customtkinter as ctk

from app.ui.theme import styles


class TextInput(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        options = styles.TEXT_INPUT.copy()
        options.update(kwargs)
        super().__init__(master, **options)
