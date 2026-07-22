import threading
import customtkinter as ctk
from tkinter import filedialog

from app.controllers.groups_controller import GroupsController
from app.ui.theme import colors, styles
from app.ui.widgets import (
    FieldLabel,
    GroupsManagerTable,
    PrimaryButton,
    SearchBox,
    SecondaryButton,
    SectionPanel,
    SectionTitle,
    SelectBox,
    StatusBadge,
    StatCard,
    TextInput,
)


class GroupsPage(ctk.CTkFrame):
    """Presentation-only Groups Management page."""

    route = "groups"
    title = "Groups"

    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)

        self.controller = controller or GroupsController()
        self.filters = self.controller.default_filters()

        self.search_var = ctk.StringVar(value=self.filters["search"])
        self.min_members_var = ctk.StringVar(value=self.filters["min_members"])
        self.max_members_var = ctk.StringVar(value=self.filters["max_members"])
        self.privacy_var = ctk.StringVar(value=self.filters["privacy"])
        self.category_var = ctk.StringVar(value=self.filters["category"])
        self.selected_var = ctk.StringVar(value=self.filters["selected"])

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_toolbar()
        self._build_filter_panel()
        self._build_table()
        self._build_summary_bar()

        self._load()

    def _build_toolbar(self):
        self.toolbar = SectionPanel(self)
        self.toolbar.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Padding.PAGE_Y, styles.Spacing.MD),
        )
        self.toolbar.grid_columnconfigure(0, weight=1)

        self.search_box = SearchBox(
            self.toolbar,
            textvariable=self.search_var,
            placeholder_text="Search groups",
        )
        self.search_box.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Padding.FRAME_Y,
        )
        self.search_box.bind("<KeyRelease>", self._on_search)

        self.status = StatusBadge(
            self.toolbar,
            text="Ready",
            variant="neutral",
        )
        self.status.grid(
            row=0,
            column=1,
            padx=(styles.Spacing.SM, styles.Spacing.SM),
            pady=styles.Padding.FRAME_Y,
        )

        actions = [
            ("Refresh", self._refresh),
            ("Scan", self._scan),
            ("Analyze", self._analyze),
            ("Export CSV", self._export_csv),
        ]

        for index, (label, command) in enumerate(actions, start=2):
            SecondaryButton(
                self.toolbar,
                text=label,
                command=command,
            ).grid(
                row=0,
                column=index,
                padx=(styles.Radius.NONE, styles.Spacing.SM),
                pady=styles.Padding.FRAME_Y,
            )

    def _build_filter_panel(self):
        self.filter_panel = SectionPanel(self)
        self.filter_panel.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Spacing.MD),
        )

        for column in range(8):
            self.filter_panel.grid_columnconfigure(column, weight=1)

        SectionTitle(
            self.filter_panel,
            text="Filters",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )

        self._field(
            column=0,
            label="Minimum Members",
            widget=TextInput(
                self.filter_panel,
                textvariable=self.min_members_var,
                placeholder_text="Minimum",
            ),
        )

        self._field(
            column=1,
            label="Maximum Members",
            widget=TextInput(
                self.filter_panel,
                textvariable=self.max_members_var,
                placeholder_text="Maximum",
            ),
        )

        self.privacy_select = SelectBox(
            self.filter_panel,
            values=["All", "Public", "Private"],
            variable=self.privacy_var,
        )
        self._field(column=2, label="Privacy", widget=self.privacy_select)

        self.category_select = SelectBox(
            self.filter_panel,
            values=["All Categories"],
            variable=self.category_var,
        )
        self._field(column=3, label="Category", widget=self.category_select)

        self.selected_select = SelectBox(
            self.filter_panel,
            values=["All", "Selected Only", "Unselected Only"],
            variable=self.selected_var,
        )
        self._field(column=4, label="Selected", widget=self.selected_select)

        PrimaryButton(
            self.filter_panel,
            text="Apply Filters",
            command=self._apply_filters,
        ).grid(
            row=2,
            column=5,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=(styles.Spacing.SM, styles.Padding.FRAME_Y),
        )

        SecondaryButton(
            self.filter_panel,
            text="Select All",
            command=self._select_all,
        ).grid(
            row=2,
            column=6,
            sticky="ew",
            padx=(styles.Spacing.SM, styles.Padding.FRAME_X),
            pady=(styles.Spacing.SM, styles.Padding.FRAME_Y),
        )

        SecondaryButton(
            self.filter_panel,
            text="Unselect All",
            command=self._unselect_all,
        ).grid(
            row=2,
            column=7,
            sticky="ew",
            padx=(styles.Radius.NONE, styles.Padding.FRAME_X),
            pady=(styles.Spacing.SM, styles.Padding.FRAME_Y),
        )

    def _build_table(self):
        self.table_panel = SectionPanel(self)
        self.table_panel.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Spacing.MD),
        )
        self.table_panel.grid_columnconfigure(0, weight=1)
        self.table_panel.grid_rowconfigure(1, weight=1)

        SectionTitle(
            self.table_panel,
            text="Groups Table",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )

        self.groups_table = GroupsManagerTable(
            self.table_panel,
            on_select=self._set_group_selected,
            on_sort=self._sort_by,
        )
        self.groups_table.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )

    def _build_summary_bar(self):
        self.summary_bar = SectionPanel(self)
        self.summary_bar.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.PAGE_Y),
        )

        for column in range(4):
            self.summary_bar.grid_columnconfigure(column, weight=1)

        self.total_card = StatCard(self.summary_bar, title="Total Groups")
        self.selected_card = StatCard(self.summary_bar, title="Selected Groups")
        self.public_card = StatCard(self.summary_bar, title="Public Groups")
        self.private_card = StatCard(self.summary_bar, title="Private Groups")

        cards = [
            self.total_card,
            self.selected_card,
            self.public_card,
            self.private_card,
        ]

        for index, card in enumerate(cards):
            card.grid(
                row=0,
                column=index,
                sticky="ew",
                padx=styles.Spacing.SM,
                pady=styles.Padding.FRAME_Y,
            )

    def _field(self, column, label, widget):
        FieldLabel(
            self.filter_panel,
            text=label,
        ).grid(
            row=1,
            column=column,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=(styles.Radius.NONE, styles.Spacing.XS),
        )

        widget.grid(
            row=2,
            column=column,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=(styles.Spacing.SM, styles.Padding.FRAME_Y),
        )

    def _load(self):
        groups = self.controller.load()
        self._sync_categories()
        self._render(groups)

    def _refresh(self):
        groups = self.controller.refresh()
        self._sync_categories()
        self._render(groups)

    def _scan(self):
        self.status.set_status("Scanning groups...", "info")
        self._run_async(self.controller.scan, "Scan finished")

    def _analyze(self):
        self.status.set_status("Analyzing groups...", "info")
        self._run_async(self.controller.analyze, "Analysis finished")

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )

        if path:
            self.controller.export_csv(path)

    def _apply_filters(self):
        self._render(self.controller.apply_filters(self._current_filters()))

    def _on_search(self, _event):
        self._render(self.controller.apply_filters(self._current_filters()))

    def _set_group_selected(self, group_id, selected):
        self._render(self.controller.set_group_selected(group_id, selected))

    def _select_all(self):
        self._render(self.controller.select_all())

    def _unselect_all(self):
        self._render(self.controller.unselect_all())

    def _sort_by(self, key):
        self._render(self.controller.sort_by(key))

    def _current_filters(self):
        return {
            "search": self.search_var.get(),
            "min_members": self.min_members_var.get(),
            "max_members": self.max_members_var.get(),
            "privacy": self.privacy_var.get(),
            "category": self.category_var.get(),
            "selected": self.selected_var.get(),
        }

    def _sync_categories(self):
        categories = self.controller.categories()
        self.category_select.configure(values=categories)

        if self.category_var.get() not in categories:
            self.category_var.set("All Categories")

    def _render(self, groups):
        self.groups_table.set_groups(groups)
        self._render_summary()

    def _render_summary(self):
        summary = self.controller.summary()

        self.total_card.set_value(str(summary["total"]))
        self.selected_card.set_value(str(summary["selected"]))
        self.public_card.set_value(str(summary["public"]))
        self.private_card.set_value(str(summary["private"]))

    def _run_async(self, task, success_message):
        def target():
            try:
                groups = task()
                self.after(0, lambda: self._finish_async(groups, success_message, "success"))
            except Exception as error:
                message = str(error)
                self.after(0, lambda: self.status.set_status(message, "danger"))

        threading.Thread(target=target, daemon=True).start()

    def _finish_async(self, groups, message, variant):
        self._sync_categories()
        self._render(groups)
        self.status.set_status(message, variant)
