import customtkinter as ctk

from app.ui.theme import fonts, styles


class StatusBadge(ctk.CTkLabel):
    def __init__(self, master, text, variant="neutral", **kwargs):
        self.variant = variant
        options = {
            "text": text,
            "font": fonts.BADGE,
            "corner_radius": styles.Radius.SM,
            "height": styles.INPUT_HEIGHT,
        }
        options.update(styles.STATUS_BADGES.get(variant, styles.STATUS_BADGES["neutral"]))
        options.update(kwargs)
        super().__init__(master, **options)

    def set_status(self, text, variant=None):
        self.configure(text=text)

        if variant is not None:
            self.variant = variant
            self.configure(**styles.STATUS_BADGES.get(variant, styles.STATUS_BADGES["neutral"]))
