import customtkinter as ctk

from app.ui.theme import styles


class SearchBox(ctk.CTkEntry):
    def __init__(self, master, placeholder_text="Search", **kwargs):
        options = styles.SEARCH_BOX.copy()
        options.update(
            {
                "placeholder_text": placeholder_text,
            }
        )
        options.update(kwargs)
        super().__init__(master, **options)
