import customtkinter as ctk

from app.controllers.targets_controller import TargetsController
from app.ui.theme import colors, fonts, styles
from app.ui.widgets import FieldLabel, SecondaryButton, SectionPanel, SectionTitle, SelectBox, StatusBadge, TableText


class TargetsPage(ctk.CTkFrame):
    route = "targets"
    title = "Publishing Targets"

    def __init__(self, master, controller=None, on_manage_facebook_groups=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)
        self.controller = controller or TargetsController()
        self.on_manage_facebook_groups = on_manage_facebook_groups
        self.platform_var = ctk.StringVar(value="All Platforms")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_filters()
        self._build_targets()
        self.refresh()

    def refresh(self):
        self._render(self.controller.load())

    def _build_filters(self):
        panel = SectionPanel(self)
        panel.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Padding.PAGE_Y, styles.Spacing.MD),
        )
        panel.grid_columnconfigure(0, weight=1)

        SectionTitle(panel, text="Targets").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Padding.FRAME_Y,
        )

        self.platform_select = SelectBox(
            panel,
            values=self.controller.platforms(),
            variable=self.platform_var,
            command=self._on_platform_changed,
        )
        FieldLabel(panel, text="Platform").grid(
            row=0,
            column=1,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.XS),
        )
        self.platform_select.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )

        self.status = StatusBadge(panel, text="Ready", variant="neutral")
        self.status.grid(row=1, column=2, padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

        SecondaryButton(
            panel,
            text="Manage Facebook Groups",
            command=self._manage_facebook_groups,
        ).grid(row=1, column=3, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)

    def _build_targets(self):
        panel = SectionPanel(self)
        panel.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.PAGE_Y),
        )
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(panel, fg_color=colors.TRANSPARENT)
        header.grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

        columns = ["Platform", "Type", "Name", "Privacy", "Members", "Selected", "Last Scan"]
        for index, label in enumerate(columns):
            header.grid_columnconfigure(index, weight=1)
            TableText(header, text=label, font=fonts.SMALL_BOLD).grid(row=0, column=index, sticky="ew", padx=styles.Spacing.XS)

        self.rows = ctk.CTkScrollableFrame(panel, fg_color=colors.TRANSPARENT, corner_radius=styles.Radius.NONE)
        self.rows.grid(row=1, column=0, sticky="nsew", padx=styles.Padding.FRAME_X, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))

        for index in range(len(columns)):
            self.rows.grid_columnconfigure(index, weight=1)

    def _on_platform_changed(self, value):
        self._render(self.controller.set_platform(value))

    def _render(self, targets):
        for child in self.rows.winfo_children():
            child.destroy()

        placeholder = self.controller.placeholder_message()
        if placeholder:
            StatusBadge(self.rows, text=placeholder, variant="info").grid(row=0, column=0, sticky="w", pady=styles.Spacing.MD)
            self.status.set_status(placeholder, "info")
            return

        if not targets:
            TableText(self.rows, text="No targets found.", text_color=colors.TEXT_MUTED).grid(row=0, column=0, sticky="ew", pady=styles.Spacing.MD)
            self.status.set_status("No targets", "neutral")
            return

        for row_index, target in enumerate(targets):
            values = [
                str(target.get("platform") or "facebook").title(),
                target.get("target_type") or "",
                target.get("name") or "",
                target.get("privacy") or "",
                str(target.get("members_count") or 0),
                "Yes" if target.get("selected") else "No",
                target.get("last_scan") or "",
            ]

            for column_index, value in enumerate(values):
                TableText(
                    self.rows,
                    text=str(value)[:120],
                    font=fonts.SMALL,
                    text_color=colors.TEXT if column_index < 4 else colors.TEXT_MUTED,
                ).grid(row=row_index, column=column_index, sticky="ew", padx=styles.Spacing.XS, pady=styles.Spacing.XS)

        self.status.set_status(f"{len(targets)} targets", "success")

    def _manage_facebook_groups(self):
        if self.on_manage_facebook_groups:
            self.on_manage_facebook_groups()
