import customtkinter as ctk
from tkinter import filedialog

from app.database.db import db

from app.services.facebook_service import facebook
from app.services.post_service import post_service
from app.services.publisher import publisher

from app.ui.groups_table import GroupsTable


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Facebook Publisher Pro")
        self.geometry("1500x900")

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.group_vars = []

        # ==================================================
        # Toolbar
        # ==================================================

        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            toolbar,
            text="Login",
            width=120,
            command=facebook.login
        ).pack(side="left", padx=5, pady=10)

        ctk.CTkButton(
            toolbar,
            text="Scan Groups",
            width=150,
            command=self.scan_groups
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="Analyze Groups",
            width=170,
            command=self.analyze_groups
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="Select All",
            width=120,
            command=self.select_all
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="Unselect All",
            width=120,
            command=self.unselect_all
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="Publish",
            width=140,
            fg_color="green",
            command=self.publish_post
        ).pack(side="left", padx=15)

        self.status = ctk.CTkLabel(
            toolbar,
            text="Ready"
        )

        self.status.pack(side="right", padx=20)

        # ==================================================
        # Main Layout
        # ==================================================

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # ==================================================
        # LEFT PANEL
        # ==================================================

        left = ctk.CTkFrame(body)

        left.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 5)
        )

        ctk.CTkLabel(
            left,
            text="Facebook Groups",
            font=("Arial", 20, "bold")
        ).pack(pady=10)

        self.groups_table = GroupsTable(left)

        self.groups_table.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # ==================================================
        # RIGHT PANEL
        # ==================================================

        right = ctk.CTkFrame(body)

        right.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        ctk.CTkLabel(
            right,
            text="Post Editor",
            font=("Arial", 22, "bold")
        ).pack(pady=15)

        # ---------------- Title ----------------

        ctk.CTkLabel(
            right,
            text="Title"
        ).pack(anchor="w", padx=20)

        self.title_entry = ctk.CTkEntry(
            right,
            width=650
        )

        self.title_entry.pack(
            padx=20,
            pady=5
        )

        # ---------------- Content ----------------

        ctk.CTkLabel(
            right,
            text="Post Text"
        ).pack(
            anchor="w",
            padx=20,
            pady=(10, 0)
        )

        self.content_box = ctk.CTkTextbox(
            right,
            width=700,
            height=260
        )

        self.content_box.pack(
            padx=20,
            pady=5
        )
        # ===================================================
        # RIGHT PANEL
        # ===================================================

        right = ctk.CTkFrame(body)
        right.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        ctk.CTkLabel(
            right,
            text="Post Editor",
            font=("Arial", 22, "bold")
        ).pack(pady=15)

        # ---------------- Title ----------------

        ctk.CTkLabel(
            right,
            text="Title"
        ).pack(anchor="w", padx=20)

        self.title_entry = ctk.CTkEntry(
            right,
            width=650
        )

        self.title_entry.pack(
            padx=20,
            pady=5
        )

        # ---------------- Content ----------------

        ctk.CTkLabel(
            right,
            text="Post Text"
        ).pack(anchor="w", padx=20)

        self.content_box = ctk.CTkTextbox(
            right,
            width=700,
            height=260
        )

        self.content_box.pack(
            padx=20,
            pady=5
        )

        # ---------------- Youtube ----------------

        ctk.CTkLabel(
            right,
            text="YouTube URL"
        ).pack(anchor="w", padx=20)

        self.youtube_entry = ctk.CTkEntry(
            right,
            width=700
        )

        self.youtube_entry.pack(
            padx=20,
            pady=5
        )

        # ---------------- Image ----------------

        self.image_label = ctk.CTkLabel(
            right,
            text="No image selected",
            anchor="w"
        )

        self.image_label.pack(
            anchor="w",
            padx=20,
            pady=(10, 0)
        )

        ctk.CTkButton(
            right,
            text="Choose Image",
            command=self.choose_image
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )

        # ---------------- Video ----------------

        self.video_label = ctk.CTkLabel(
            right,
            text="No video selected",
            anchor="w"
        )

        self.video_label.pack(
            anchor="w",
            padx=20,
            pady=(10, 0)
        )

        ctk.CTkButton(
            right,
            text="Choose Video",
            command=self.choose_video
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )

        # ---------------- Delay ----------------

        ctk.CTkLabel(
            right,
            text="Delay Between Groups (seconds)"
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 0)
        )

        self.delay_entry = ctk.CTkEntry(
            right,
            width=120
        )

        self.delay_entry.insert(0, "30")

        self.delay_entry.pack(
            anchor="w",
            padx=20,
            pady=5
        )

        self.load_groups()

    # ===================================================
    # FILE PICKERS
    # ===================================================

    def choose_image(self):

        path = filedialog.askopenfilename(
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.webp")
            ]
        )

        if path:

            post_service.set_image(path)

            self.image_label.configure(
                text=path
            )

    # ===================================================

    def choose_video(self):

        path = filedialog.askopenfilename(
            filetypes=[
                ("Videos", "*.mp4 *.mov *.avi *.mkv")
            ]
        )

        if path:

            post_service.set_video(path)

            self.video_label.configure(
                text=path
            )
    # ===================================================
    # ACTIONS
    # ===================================================

    def publish_post(self):

        post_service.set_title(
            self.title_entry.get()
        )

        post_service.set_content(
            self.content_box.get("1.0", "end")
        )

        post_service.set_youtube(
            self.youtube_entry.get()
        )

        post_service.set_delay(
            self.delay_entry.get()
        )

        publisher.publish()

    # ===================================================

    def scan_groups(self):

        self.status.configure(
            text="Scanning..."
        )

        self.update()

        facebook.scan_groups()

        self.load_groups()

        self.status.configure(
            text="Scan Finished"
        )

    # ===================================================

    def analyze_groups(self):

        self.status.configure(
            text="Analyzing..."
        )

        self.update()

        facebook.analyze_groups()

        self.load_groups()

        self.status.configure(
            text="Analysis Finished"
        )

    # ===================================================
    # GROUP TABLE
    # ===================================================

    def load_groups(self):

        self.groups_table.clear()

        self.group_vars.clear()

        groups = db.get_groups()

        self.status.configure(
            text=f"{len(groups)} Groups"
        )

        for group in groups:

            selected = bool(group["selected"])

            self.group_vars.append(
                (
                    group["id"],
                    selected
                )
            )

            self.groups_table.add_row(
                selected=selected,
                name=group["name"],
                members=group["members"] or "",
                privacy=group["privacy"] or "",
                category=group["category"] or "",
                status="Ready"
            )

    # ===================================================

    def refresh_groups(self):

        self.load_groups()

    # ===================================================
    # SELECT BUTTONS
    # ===================================================

    def select_all(self):

        groups = db.get_groups()

        for group in groups:

            db.set_group_selected(
                group["id"],
                True
            )

        self.load_groups()

    # ===================================================

    def unselect_all(self):

        groups = db.get_groups()

        for group in groups:

            db.set_group_selected(
                group["id"],
                False
            )

        self.load_groups()
    # ===================================================
    # OPTIONAL HELPERS
    # ===================================================

    def get_selected_group_ids(self):

        groups = db.get_selected_groups()

        return [
            group["id"]
            for group in groups
        ]

    # ===================================================

    def get_selected_groups(self):

        return db.get_selected_groups()

    # ===================================================

    def clear_post(self):

        self.title_entry.delete(
            0,
            "end"
        )

        self.content_box.delete(
            "1.0",
            "end"
        )

        self.youtube_entry.delete(
            0,
            "end"
        )

        self.image_label.configure(
            text="No image selected"
        )

        self.video_label.configure(
            text="No video selected"
        )

        self.delay_entry.delete(
            0,
            "end"
        )

        self.delay_entry.insert(
            0,
            "30"
        )

        post_service.clear()

    # ===================================================

    def update_status(
        self,
        text
    ):

        self.status.configure(
            text=text
        )

        self.update_idletasks()

    # ===================================================

    def on_closing(self):

        self.destroy()
                                    