import customtkinter as ctk

from app.ui.theme import colors, styles
from app.ui.widgets.check_box import CheckBox
from app.ui.widgets.secondary_button import SecondaryButton
from app.ui.widgets.status_badge import StatusBadge
from app.ui.widgets.table_text import TableText


class GroupsManagerTable(ctk.CTkFrame):
    def __init__(self, master, on_select=None, on_sort=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)

        self.on_select = on_select
        self.on_sort = on_sort
        self.rows = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkFrame(self, fg_color=colors.TRANSPARENT)
        self.header.grid(row=0, column=0, sticky="ew")
        for column in range(len(styles.GROUP_TABLE_COLUMNS)):
            self.header.grid_columnconfigure(column, weight=1)

        self.body = ctk.CTkScrollableFrame(
            self,
            fg_color=colors.TRANSPARENT,
            corner_radius=styles.Radius.NONE,
        )
        self.body.grid(row=1, column=0, sticky="nsew", pady=(styles.Spacing.SM, styles.Radius.NONE))
        self.body.grid_columnconfigure(0, weight=1)

        self._build_header()

    def set_groups(self, groups):
        self.clear()

        for index, group in enumerate(groups):
            self._add_row(index, group)

    def clear(self):
        for row in self.rows:
            row.destroy()

        self.rows.clear()

    def _build_header(self):
        columns = [
            ("", "selected"),
            ("Group Name", "name"),
            ("Members", "members_count"),
            ("Privacy", "privacy"),
            ("Category", "category"),
            ("Last Scan", "last_scan"),
            ("Status", "selected"),
        ]

        for index, (title, key) in enumerate(columns):
            width = styles.GROUP_TABLE_COLUMNS[index][1]
            button = SecondaryButton(
                self.header,
                text=title,
                width=width,
                anchor="w",
                command=lambda sort_key=key: self._sort(sort_key),
            )
            button.grid(row=0, column=index, padx=styles.Spacing.XS, sticky="ew")

    def _add_row(self, index, group):
        row = ctk.CTkFrame(
            self.body,
            height=styles.ROW_HEIGHT,
            corner_radius=styles.Radius.SM,
            fg_color=colors.SURFACE if index % 2 == 0 else colors.SURFACE_MUTED,
        )
        row.grid(row=index, column=0, sticky="ew", pady=styles.Spacing.XS)
        row.grid_propagate(False)

        selected_var = ctk.IntVar(value=int(bool(group.get("selected"))))
        checkbox = CheckBox(
            row,
            text="",
            width=styles.GROUP_TABLE_COLUMNS[0][1],
            variable=selected_var,
            command=lambda group_id=group["id"], var=selected_var: self._select(group_id, var),
        )
        checkbox.grid(row=0, column=0, padx=styles.Spacing.XS, sticky="w")

        values = [
            group.get("name") or "",
            group.get("members") or group.get("members_count") or "",
            group.get("privacy") or "",
            group.get("category") or "",
            group.get("last_scan") or "",
        ]

        for col_index, value in enumerate(values, start=1):
            TableText(
                row,
                text=str(value),
                width=styles.GROUP_TABLE_COLUMNS[col_index][1],
            ).grid(row=0, column=col_index, padx=styles.Spacing.XS, sticky="w")

        status_text = "Selected" if group.get("selected") else "Unselected"
        status_variant = "info" if group.get("selected") else "neutral"
        StatusBadge(
            row,
            text=status_text,
            variant=status_variant,
            width=styles.GROUP_TABLE_COLUMNS[6][1],
        ).grid(row=0, column=6, padx=styles.Spacing.XS, sticky="w")

        row.bind("<Enter>", lambda event, row_frame=row: self._highlight(row_frame))
        row.bind("<Leave>", lambda event, row_frame=row, row_index=index: self._unhighlight(row_frame, row_index))

        self.rows.append(row)

    def _sort(self, key):
        if self.on_sort:
            self.on_sort(key)

    def _select(self, group_id, var):
        if self.on_select:
            self.on_select(group_id, bool(var.get()))

    def _highlight(self, row):
        row.configure(**styles.TABLE_ROW_HIGHLIGHT)

    def _unhighlight(self, row, index):
        row.configure(fg_color=colors.SURFACE if index % 2 == 0 else colors.SURFACE_MUTED)
