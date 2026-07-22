import customtkinter as ctk

from app.ui.theme import fonts, styles


class GroupsTable(ctk.CTkScrollableFrame):

    def __init__(self, master):
        super().__init__(master)

        self.rows = []

        headers = ctk.CTkFrame(self)
        headers.pack(fill="x", pady=(0, 5))

        columns = [
            ("✓", styles.GROUP_TABLE_COLUMNS[0][1]),
            ("Group", styles.GROUP_TABLE_COLUMNS[1][1]),
            ("Members", styles.GROUP_TABLE_COLUMNS[2][1]),
            ("Privacy", styles.GROUP_TABLE_COLUMNS[3][1]),
            ("Category", styles.GROUP_TABLE_COLUMNS[4][1]),
            ("Status", styles.GROUP_TABLE_COLUMNS[5][1]),
        ]

        for title, width in columns:

            ctk.CTkLabel(
                headers,
                text=title,
                width=width,
                anchor="w",
                font=fonts.BODY_BOLD,
            ).pack(side="left", padx=styles.Spacing.XS)

    def clear(self):

        for row in self.rows:
            row.destroy()

        self.rows.clear()

    def add_row(
        self,
        selected,
        name,
        members,
        privacy,
        category,
        status
    ):

        row = ctk.CTkFrame(self)

        row.pack(fill="x", pady=styles.Spacing.XS)

        self.rows.append(row)

        values = [
            "☑" if selected else "☐",
            name,
            members,
            privacy,
            category,
            status,
        ]

        widths = [
            styles.GROUP_TABLE_COLUMNS[0][1],
            styles.GROUP_TABLE_COLUMNS[1][1],
            styles.GROUP_TABLE_COLUMNS[2][1],
            styles.GROUP_TABLE_COLUMNS[3][1],
            styles.GROUP_TABLE_COLUMNS[4][1],
            styles.GROUP_TABLE_COLUMNS[5][1],
        ]

        for value, width in zip(values, widths):

            ctk.CTkLabel(
                row,
                text=value,
                width=width,
                anchor="w"
            ).pack(side="left", padx=styles.Spacing.XS)
