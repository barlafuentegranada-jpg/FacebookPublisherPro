import customtkinter as ctk

from app.ui.theme import styles


class SelectBox(ctk.CTkOptionMenu):
    def __init__(self, master, values, **kwargs):
        options = styles.SELECT_BOX.copy()
        options.update(
            {
                "values": values,
            }
        )
        options.update(kwargs)
        super().__init__(master, **options)
