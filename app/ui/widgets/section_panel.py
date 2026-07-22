import customtkinter as ctk

from app.ui.theme import styles


class SectionPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        options = styles.SECTION_PANEL.copy()
        options.update(kwargs)
        super().__init__(master, **options)
