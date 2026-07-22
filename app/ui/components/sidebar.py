import customtkinter as ctk

from app.ui.theme import colors, fonts, styles
from app.ui.widgets.secondary_button import SecondaryButton


class Sidebar(ctk.CTkFrame):
    """Left navigation rail for the v2 UI shell."""

    def __init__(self, master, on_navigate=None, **kwargs):
        super().__init__(
            master,
            corner_radius=styles.Radius.NONE,
            fg_color=colors.SURFACE,
            **kwargs
        )

        self.on_navigate = on_navigate
        self.buttons = {}
        self.active_route = None

        self.grid_columnconfigure(0, weight=1)

        self.brand_label = ctk.CTkLabel(
            self,
            text="Publisher",
            font=fonts.HEADER_TITLE,
            text_color=colors.TEXT,
            anchor="w",
        )
        self.brand_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.LG, styles.Spacing.LG),
        )

        self.nav_frame = ctk.CTkFrame(self, fg_color=colors.TRANSPARENT)
        self.nav_frame.grid(
            row=1,
            column=0,
            sticky="new",
            padx=styles.Spacing.MD,
            pady=styles.Spacing.SM,
        )
        self.nav_frame.grid_columnconfigure(0, weight=1)

    def set_items(self, items):
        for button in self.buttons.values():
            button.destroy()

        self.buttons.clear()

        for index, item in enumerate(items):
            route = item["route"]
            title = item["title"]

            button = SecondaryButton(
                self.nav_frame,
                text=title,
                anchor="w",
                **styles.NAV_BUTTON,
                command=lambda selected_route=route: self._navigate(selected_route),
            )
            button.grid(row=index, column=0, sticky="ew", pady=styles.Spacing.XS)

            self.buttons[route] = button

    def set_active(self, route):
        self.active_route = route

        for item_route, button in self.buttons.items():
            if item_route == route:
                button.configure(**styles.NAV_BUTTON_ACTIVE)
            else:
                button.configure(**styles.NAV_BUTTON_INACTIVE)

    def _navigate(self, route):
        if self.on_navigate:
            self.on_navigate(route)
