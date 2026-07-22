import customtkinter as ctk


class GroupsTable(ctk.CTkScrollableFrame):

    def __init__(self, master):
        super().__init__(master)

        self.rows = []

        headers = ctk.CTkFrame(self)
        headers.pack(fill="x", pady=(0, 5))

        columns = [
            ("✓", 40),
            ("Group", 320),
            ("Members", 110),
            ("Privacy", 100),
            ("Category", 120),
            ("Status", 100),
        ]

        for title, width in columns:

            ctk.CTkLabel(
                headers,
                text=title,
                width=width,
                anchor="w",
                font=("Arial", 14, "bold")
            ).pack(side="left", padx=2)

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

        row.pack(fill="x", pady=2)

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
            40,
            320,
            110,
            100,
            120,
            100,
        ]

        for value, width in zip(values, widths):

            ctk.CTkLabel(
                row,
                text=value,
                width=width,
                anchor="w"
            ).pack(side="left", padx=2)