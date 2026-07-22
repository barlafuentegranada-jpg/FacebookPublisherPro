import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.controllers.posts_controller import PostsController
from app.ui.theme import colors, fonts, styles
from app.ui.widgets import (
    DangerButton,
    FieldLabel,
    PrimaryButton,
    SearchBox,
    SecondaryButton,
    SectionPanel,
    SectionTitle,
    SelectBox,
    StatusBadge,
    TableText,
    TextInput,
)


class PostsPage(ctk.CTkFrame):
    route = "posts"
    title = "Posts"

    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)

        self.controller = controller or PostsController()
        self.selected_card = None

        self.search_var = ctk.StringVar()
        self.filter_status_var = ctk.StringVar(value="All")
        self.title_var = ctk.StringVar()
        self.youtube_var = ctk.StringVar()
        self.image_var = ctk.StringVar()
        self.video_var = ctk.StringVar()
        self.tags_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Draft")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_body()
        self.refresh()

    def refresh(self):
        posts = self.controller.refresh()
        self._render_posts(posts)

        if self.controller.selected_post_id:
            post = self.controller.select_post(self.controller.selected_post_id)
            if post:
                self._load_editor(post)

    def _build_toolbar(self):
        toolbar = SectionPanel(self)
        toolbar.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Padding.PAGE_Y, styles.Spacing.MD),
        )
        toolbar.grid_columnconfigure(1, weight=1)

        PrimaryButton(toolbar, text="New Post", command=self._clear_editor).grid(
            row=0,
            column=0,
            padx=(styles.Padding.FRAME_X, styles.Spacing.SM),
            pady=styles.Padding.FRAME_Y,
        )

        self.search_box = SearchBox(
            toolbar,
            textvariable=self.search_var,
            placeholder_text="Search posts",
        )
        self.search_box.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=styles.Padding.FRAME_Y,
        )
        self.search_box.bind("<KeyRelease>", self._on_search)

        self.status_filter = SelectBox(
            toolbar,
            values=["All", "Draft", "Ready", "Archived"],
            variable=self.filter_status_var,
            command=self._on_status_filter,
        )
        self.status_filter.grid(
            row=0,
            column=2,
            padx=styles.Spacing.SM,
            pady=styles.Padding.FRAME_Y,
        )

        SecondaryButton(toolbar, text="Refresh", command=self.refresh).grid(
            row=0,
            column=3,
            padx=(styles.Spacing.SM, styles.Padding.FRAME_X),
            pady=styles.Padding.FRAME_Y,
        )

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color=colors.TRANSPARENT)
        body.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.PAGE_Y),
        )
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        list_panel = SectionPanel(body)
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, styles.Spacing.MD))
        list_panel.grid_columnconfigure(0, weight=1)
        list_panel.grid_rowconfigure(1, weight=1)

        SectionTitle(list_panel, text="Library").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )

        self.posts_list = ctk.CTkScrollableFrame(
            list_panel,
            fg_color=colors.TRANSPARENT,
            corner_radius=styles.Radius.NONE,
        )
        self.posts_list.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Padding.FRAME_Y),
        )
        self.posts_list.grid_columnconfigure(0, weight=1)

        editor = SectionPanel(body)
        editor.grid(row=0, column=1, sticky="nsew")
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(4, weight=1)

        SectionTitle(editor, text="Editor").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )

        self.message = StatusBadge(editor, text="Ready", variant="neutral")
        self.message.grid(
            row=0,
            column=1,
            sticky="e",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.SM),
        )

        self._editor_field(editor, 1, "Title", TextInput(editor, textvariable=self.title_var))

        FieldLabel(editor, text="Post Text").grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.SM, styles.Spacing.XS),
        )
        self.content_text = ctk.CTkTextbox(
            editor,
            fg_color=colors.SURFACE_MUTED,
            border_color=colors.BORDER,
            border_width=styles.BORDER_WIDTH,
            corner_radius=styles.Radius.SM,
            text_color=colors.TEXT,
            font=fonts.BODY,
        )
        self.content_text.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Radius.NONE, styles.Spacing.SM),
        )

        self._editor_field(editor, 5, "YouTube URL", TextInput(editor, textvariable=self.youtube_var))
        self._media_field(editor, 6, "Image", self.image_var, self._choose_image)
        self._media_field(editor, 7, "Video", self.video_var, self._choose_video)
        self._editor_field(editor, 8, "Tags", TextInput(editor, textvariable=self.tags_var))

        self.status_select = SelectBox(
            editor,
            values=["Draft", "Ready", "Archived"],
            variable=self.status_var,
        )
        self._editor_field(editor, 9, "Status", self.status_select)

        actions = ctk.CTkFrame(editor, fg_color=colors.TRANSPARENT)
        actions.grid(
            row=10,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Padding.FRAME_Y,
        )

        buttons = [
            (PrimaryButton, "Save", self._save),
            (SecondaryButton, "Save as New", self._save_as_new),
            (SecondaryButton, "Duplicate", self._duplicate),
            (SecondaryButton, "Archive", self._archive),
            (DangerButton, "Delete", self._delete),
            (SecondaryButton, "Clear", self._clear_editor),
        ]

        for index, (button_class, text, command) in enumerate(buttons):
            button_class(actions, text=text, command=command).grid(
                row=0,
                column=index,
                padx=(styles.Radius.NONE, styles.Spacing.SM),
            )

    def _editor_field(self, parent, row, label, widget):
        FieldLabel(parent, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.SM, styles.Spacing.XS),
        )
        widget.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.SM, styles.Spacing.XS),
        )

    def _media_field(self, parent, row, label, variable, command):
        FieldLabel(parent, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.SM, styles.Spacing.XS),
        )
        row_frame = ctk.CTkFrame(parent, fg_color=colors.TRANSPARENT)
        row_frame.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.SM, styles.Spacing.XS),
        )
        row_frame.grid_columnconfigure(0, weight=1)
        TextInput(row_frame, textvariable=variable).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(styles.Radius.NONE, styles.Spacing.SM),
        )
        SecondaryButton(row_frame, text="Choose", command=command).grid(row=0, column=1)

    def _render_posts(self, posts):
        for child in self.posts_list.winfo_children():
            child.destroy()

        self.selected_card = None

        if not posts:
            TableText(
                self.posts_list,
                text="No posts found.",
                text_color=colors.TEXT_MUTED,
            ).grid(row=0, column=0, sticky="ew", pady=styles.Spacing.MD)
            return

        for index, post in enumerate(posts):
            card = self._post_card(post)
            card.grid(row=index, column=0, sticky="ew", pady=styles.Spacing.SM)

            if post["id"] == self.controller.selected_post_id:
                card.configure(fg_color=colors.SURFACE_ACTIVE)
                self.selected_card = card

    def _post_card(self, post):
        card = ctk.CTkFrame(
            self.posts_list,
            corner_radius=styles.Radius.MD,
            fg_color=colors.SURFACE_MUTED,
            border_color=colors.BORDER,
            border_width=styles.BORDER_WIDTH,
        )
        card.grid_columnconfigure(0, weight=1)

        title = post.get("title") or "Untitled Post"
        preview = (post.get("content") or "").replace("\n", " ")[:120]
        media = self._media_indicators(post)
        tags = post.get("tags") or "No tags"
        updated = post.get("updated_at") or post.get("created_at") or ""

        TableText(card, text=title, font=fonts.BODY_BOLD).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.XS),
        )
        StatusBadge(card, text=post.get("status") or "Draft", variant=self._status_variant(post)).grid(
            row=0,
            column=1,
            padx=styles.Padding.FRAME_X,
            pady=(styles.Padding.FRAME_Y, styles.Spacing.XS),
        )
        TableText(card, text=preview or "Media-only post", text_color=colors.TEXT_MUTED).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Spacing.XS,
        )
        TableText(card, text=f"{media} | {tags} | Updated {updated}", font=fonts.SMALL, text_color=colors.TEXT_MUTED).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=(styles.Spacing.XS, styles.Padding.FRAME_Y),
        )

        for widget in (card,):
            widget.bind("<Button-1>", lambda _event, post_id=post["id"]: self._select(post_id))

        return card

    def _select(self, post_id):
        post = self.controller.select_post(post_id)

        if post:
            self._load_editor(post)
            self._render_posts(self.controller.posts)
            self._set_message("Post loaded", "info")

    def _load_editor(self, post):
        self.title_var.set(post.get("title") or "")
        self.youtube_var.set(post.get("youtube_url") or "")
        self.image_var.set(post.get("image_path") or "")
        self.video_var.set(post.get("video_path") or "")
        self.tags_var.set(post.get("tags") or "")
        self.status_var.set(post.get("status") or "Draft")
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", post.get("content") or "")

    def _payload(self):
        return {
            "title": self.title_var.get(),
            "content": self.content_text.get("1.0", "end").strip(),
            "image_path": self.image_var.get(),
            "video_path": self.video_var.get(),
            "youtube_url": self.youtube_var.get(),
            "tags": self.tags_var.get(),
            "status": self.status_var.get(),
        }

    def _save(self):
        self._run_action(lambda: self.controller.update_selected(self._payload()), "Post saved")

    def _save_as_new(self):
        self._run_action(lambda: self.controller.save_as_new(self._payload()), "Post saved as new")

    def _duplicate(self):
        self._run_action(self.controller.duplicate_selected, "Post duplicated")

    def _archive(self):
        self._run_action(self.controller.archive_selected, "Post archived")

    def _delete(self):
        if not messagebox.askyesno("Delete Post", "Delete the selected post?", parent=self):
            return

        try:
            self.controller.delete_selected()
            self._clear_editor()
            self._render_posts(self.controller.posts)
            self._set_message("Post deleted", "warning")
        except Exception as error:
            self._set_message(str(error), "danger")

    def _run_action(self, action, success_message):
        try:
            post = action()
            if isinstance(post, dict):
                self._load_editor(post)
            self._render_posts(self.controller.posts)
            self._set_message(success_message, "success")
        except Exception as error:
            self._set_message(str(error), "danger")

    def _clear_editor(self):
        self.controller.selected_post_id = None
        self.title_var.set("")
        self.youtube_var.set("")
        self.image_var.set("")
        self.video_var.set("")
        self.tags_var.set("")
        self.status_var.set("Draft")
        self.content_text.delete("1.0", "end")
        self._render_posts(self.controller.posts)
        self._set_message("Editor cleared", "neutral")

    def _choose_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")],
        )

        if path:
            self.image_var.set(path)

    def _choose_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("Videos", "*.mp4 *.mov *.avi *.mkv")],
        )

        if path:
            self.video_var.set(path)

    def _on_search(self, _event):
        posts = self.controller.set_search(self.search_var.get())
        self._render_posts(posts)

    def _on_status_filter(self, value):
        posts = self.controller.set_status(value)
        self._render_posts(posts)

    def _media_indicators(self, post):
        indicators = []

        if post.get("image_path"):
            indicators.append("Image")

        if post.get("video_path"):
            indicators.append("Video")

        if post.get("youtube_url"):
            indicators.append("YouTube")

        return ", ".join(indicators) if indicators else "Text"

    def _status_variant(self, post):
        status = post.get("status")

        if status == "Ready":
            return "success"

        if status == "Archived":
            return "neutral"

        return "warning"

    def _set_message(self, text, variant):
        self.message.set_status(text, variant)
