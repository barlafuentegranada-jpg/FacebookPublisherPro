import customtkinter as ctk

from app.ui.theme import colors, fonts, styles


class LoadingOverlay(ctk.CTkFrame):
    def __init__(self, master, text="Loading...", **kwargs):
        super().__init__(
            master,
            corner_radius=styles.Radius.NONE,
            fg_color=colors.SURFACE,
            **kwargs
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.content = ctk.CTkFrame(
            self,
            corner_radius=styles.Radius.MD,
            fg_color=colors.SURFACE_MUTED,
        )
        self.content.grid(row=0, column=0, padx=styles.Padding.PAGE_X, pady=styles.Padding.PAGE_Y)

        self.progress = ctk.CTkProgressBar(
            self.content,
            mode="indeterminate",
            progress_color=colors.PRIMARY,
        )
        self.progress.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )

        self.label = ctk.CTkLabel(
            self.content,
            text=text,
            font=fonts.BODY,
            text_color=colors.TEXT_MUTED,
        )
        self.label.grid(
            row=1,
            column=0,
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )

    def show(self):
        self.grid()
        self.progress.start()

    def hide(self):
        self.progress.stop()
        self.grid_remove()

    def set_text(self, text):
        self.label.configure(text=text)
