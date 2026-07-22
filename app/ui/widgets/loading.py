import customtkinter as ctk

from app.ui.theme import colors, fonts, styles


class Loading(ctk.CTkFrame):
    def __init__(self, master, text="Loading...", **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(
            self,
            mode="indeterminate",
            progress_color=colors.PRIMARY,
        )
        self.progress.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.CONTROL_X,
            pady=(styles.Padding.CONTROL_Y, styles.Spacing.SM),
        )

        self.label = ctk.CTkLabel(
            self,
            text=text,
            font=fonts.SMALL,
            text_color=colors.TEXT_MUTED,
        )
        self.label.grid(
            row=1,
            column=0,
            padx=styles.Padding.CONTROL_X,
            pady=(styles.Radius.NONE, styles.Padding.CONTROL_Y),
        )

    def start(self):
        self.progress.start()

    def stop(self):
        self.progress.stop()

    def set_text(self, text):
        self.label.configure(text=text)
