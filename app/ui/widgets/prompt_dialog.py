import customtkinter as ctk

from app.ui.theme import colors, styles
from app.ui.widgets.field_label import FieldLabel
from app.ui.widgets.primary_button import PrimaryButton
from app.ui.widgets.secondary_button import SecondaryButton
from app.ui.widgets.text_input import TextInput


class PromptDialog(ctk.CTkToplevel):
    def __init__(self, master, title, label, initial_value="", on_submit=None):
        super().__init__(master)

        self.on_submit = on_submit
        self.title(title)
        self.geometry("420x180")
        self.resizable(False, False)
        self.configure(fg_color=colors.BACKGROUND)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        FieldLabel(
            self,
            text=label,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Padding.PAGE_Y, styles.Spacing.SM),
        )

        self.input = TextInput(self)
        self.input.insert(0, initial_value)
        self.input.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )
        self.input.focus_set()

        actions = ctk.CTkFrame(self, fg_color=colors.TRANSPARENT)
        actions.grid(
            row=2,
            column=0,
            sticky="e",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Spacing.SM, styles.Padding.PAGE_Y),
        )

        SecondaryButton(
            actions,
            text="Cancel",
            command=self.destroy,
        ).grid(row=0, column=0, padx=(styles.Radius.NONE, styles.Spacing.SM))

        PrimaryButton(
            actions,
            text="Save",
            command=self._submit,
        ).grid(row=0, column=1)

        self.bind("<Return>", lambda _event: self._submit())

    def _submit(self):
        value = self.input.get().strip()

        if self.on_submit:
            self.on_submit(value)

        self.destroy()
