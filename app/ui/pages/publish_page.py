import customtkinter as ctk
from tkinter import messagebox

from app.controllers.publish_controller import PublishController
from app.ui.theme import colors, fonts, styles
from app.ui.widgets import (
    CheckBox,
    FieldLabel,
    PrimaryButton,
    SecondaryButton,
    SectionPanel,
    SectionTitle,
    SelectBox,
    StatCard,
    StatusBadge,
    TableText,
    TextInput,
)


class PublishPage(ctk.CTkFrame):
    route = "publish"
    title = "Publish"

    def __init__(self, master, controller=None, on_open_groups=None, on_open_targets=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)

        self.controller = controller or PublishController()
        self.on_open_groups = on_open_groups
        self.on_open_targets = on_open_targets or on_open_groups
        self.posts = []
        self.groups = []
        self.telegram_accounts = []
        self.telegram_targets = []
        self.post_options = []
        self.active_account = None

        self.platform_var = ctk.StringVar(value="Facebook")
        self.telegram_account_var = ctk.StringVar(value="No Telegram bots")
        self.telegram_parse_mode_var = ctk.StringVar(value="None")
        self.post_var = ctk.StringVar()
        self.delay_min_var = ctk.StringVar(value="30")
        self.delay_max_var = ctk.StringVar(value="90")
        self.stop_checkpoint_var = ctk.IntVar(value=1)
        self.stop_block_var = ctk.IntVar(value=1)
        self.dry_run_var = ctk.IntVar(value=0)
        self.debug_one_group_var = ctk.IntVar(value=1)
        self.composer_debug_only_var = ctk.IntVar(value=0)
        self.stop_after_failures_var = ctk.StringVar(value="5")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self._build_account()
        self._build_post()
        self._build_groups()
        self._build_settings()
        self._build_controls()
        self._build_results()
        self.refresh()

    def refresh(self):
        if self.platform_var.get() == "Telegram":
            context = self.controller.telegram_context()
            self.telegram_accounts = context["accounts"]
            self.telegram_targets = context["targets"]
            self.posts = context["posts"]
            self.groups = self.telegram_targets
            self._sync_telegram_accounts()
            account = self._selected_telegram_account()
        else:
            context = self.controller.active_context()
            account = context["account"]
            self.active_account = account
            self.posts = context["posts"]
            self.groups = context["groups"]

        account_name = account["name"] if account else "No active account"
        login_status = account.get("login_status") or account.get("status") if account else "Login required"
        self.account_label.configure(text=f"{account_name} | {login_status}")
        self.groups_count.set_value(str(len(self.groups)))
        self._render_group_preview()
        self._sync_posts()
        self._sync_platform_controls()

    def _build_account(self):
        panel = SectionPanel(self)
        panel.grid(row=0, column=0, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Padding.PAGE_Y, styles.Spacing.MD))
        panel.grid_columnconfigure(0, weight=1)
        SectionTitle(panel, text="Account").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.platform_select = SelectBox(
            panel,
            values=["Facebook", "Telegram"],
            variable=self.platform_var,
            command=lambda _value: self.refresh(),
        )
        self.platform_select.grid(row=0, column=1, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.telegram_account_select = SelectBox(
            panel,
            values=["No Telegram bots"],
            variable=self.telegram_account_var,
            command=lambda _value: self.refresh(),
        )
        self.telegram_account_select.grid(row=0, column=2, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.account_label = TableText(panel, text="", text_color=colors.TEXT_MUTED)
        self.account_label.grid(row=0, column=3, sticky="e", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

    def _build_post(self):
        panel = SectionPanel(self)
        panel.grid(row=1, column=0, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Radius.NONE, styles.Spacing.MD))
        panel.grid_columnconfigure(1, weight=1)
        SectionTitle(panel, text="Post").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.post_select = SelectBox(panel, values=["No Ready posts"], variable=self.post_var, command=self._on_post_changed)
        self.post_select.grid(row=0, column=1, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.post_preview = TableText(panel, text="Select a Ready post.", text_color=colors.TEXT_MUTED)
        self.post_preview.grid(row=1, column=0, columnspan=2, sticky="ew", padx=styles.Padding.FRAME_X, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))

    def _build_groups(self):
        panel = SectionPanel(self)
        panel.grid(row=2, column=0, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Radius.NONE, styles.Spacing.MD))
        panel.grid_columnconfigure(1, weight=1)
        SectionTitle(panel, text="Targets").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.groups_count = StatCard(panel, title="Selected Targets")
        self.groups_count.grid(row=0, column=1, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.manage_groups_button = SecondaryButton(panel, text="Manage Groups", command=self._open_groups)
        self.manage_groups_button.grid(row=0, column=2, padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.groups_preview = TableText(panel, text="", text_color=colors.TEXT_MUTED)
        self.groups_preview.grid(row=1, column=0, columnspan=3, sticky="ew", padx=styles.Padding.FRAME_X, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))

    def _build_settings(self):
        panel = SectionPanel(self)
        panel.grid(row=3, column=0, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Radius.NONE, styles.Spacing.MD))
        for column in range(8):
            panel.grid_columnconfigure(column, weight=1)
        SectionTitle(panel, text="Settings").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self._field(panel, 1, "Min Delay", TextInput(panel, textvariable=self.delay_min_var))
        self._field(panel, 2, "Max Delay", TextInput(panel, textvariable=self.delay_max_var))
        self.stop_checkpoint_check = CheckBox(panel, text="Stop on checkpoint", variable=self.stop_checkpoint_var)
        self.stop_checkpoint_check.grid(row=1, column=3, sticky="w", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.stop_block_check = CheckBox(panel, text="Stop on block", variable=self.stop_block_var)
        self.stop_block_check.grid(row=1, column=4, sticky="w", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        CheckBox(panel, text="Dry run", variable=self.dry_run_var).grid(row=1, column=5, sticky="w", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.debug_one_group_check = CheckBox(panel, text="One-target debug", variable=self.debug_one_group_var)
        self.debug_one_group_check.grid(row=1, column=6, sticky="w", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.composer_debug_only_check = CheckBox(panel, text="Composer Debug Only", variable=self.composer_debug_only_var)
        self.composer_debug_only_check.grid(row=1, column=7, sticky="w", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.telegram_parse_mode_select = SelectBox(
            panel,
            values=["None", "HTML", "MarkdownV2"],
            variable=self.telegram_parse_mode_var,
        )
        self.telegram_parse_mode_select.grid(row=2, column=5, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        FieldLabel(panel, text="Stop after failures").grid(
            row=2,
            column=6,
            sticky="e",
            padx=styles.Spacing.SM,
            pady=styles.Padding.FRAME_Y,
        )
        TextInput(panel, textvariable=self.stop_after_failures_var).grid(
            row=2,
            column=7,
            sticky="ew",
            padx=styles.Spacing.SM,
            pady=styles.Padding.FRAME_Y,
        )

    def _build_controls(self):
        panel = SectionPanel(self)
        panel.grid(row=4, column=0, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Radius.NONE, styles.Spacing.MD))
        panel.grid_columnconfigure(2, weight=1)
        self.start_button = PrimaryButton(panel, text="Start Publishing", command=self._start)
        self.start_button.grid(row=0, column=0, padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        SecondaryButton(panel, text="Stop after current group", command=self._stop).grid(row=0, column=1, padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.progress = ctk.CTkProgressBar(panel)
        self.progress.grid(row=0, column=2, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.progress.set(0)
        self.current = StatusBadge(panel, text="Idle", variant="neutral")
        self.current.grid(row=0, column=3, padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.success_card = StatCard(panel, title="Success")
        self.failed_card = StatCard(panel, title="Failed")
        self.skipped_card = StatCard(panel, title="Skipped")
        self.success_card.grid(row=1, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))
        self.failed_card.grid(row=1, column=1, sticky="ew", padx=styles.Spacing.SM, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))
        self.skipped_card.grid(row=1, column=2, sticky="ew", padx=styles.Spacing.SM, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))
        self.group_number = TableText(panel, text="Current group: 0 / 0", text_color=colors.TEXT_MUTED)
        self.failure_count = TableText(panel, text="Current consecutive failures: 0", text_color=colors.TEXT_MUTED)
        self.cooldown = TableText(panel, text="Cooldown: inactive", text_color=colors.TEXT_MUTED)
        self.group_number.grid(row=2, column=0, sticky="w", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.failure_count.grid(row=2, column=1, sticky="w", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.cooldown.grid(row=2, column=2, sticky="w", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)

    def _build_results(self):
        panel = SectionPanel(self)
        panel.grid(row=5, column=0, sticky="nsew", padx=styles.Padding.PAGE_X, pady=(styles.Radius.NONE, styles.Padding.PAGE_Y))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        SectionTitle(panel, text="Live Results").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.results_list = ctk.CTkScrollableFrame(panel, fg_color=colors.TRANSPARENT, corner_radius=styles.Radius.NONE)
        self.results_list.grid(row=1, column=0, sticky="nsew", padx=styles.Padding.FRAME_X, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))
        self.results_list.grid_columnconfigure(0, weight=1)

    def _field(self, parent, column, label, widget):
        FieldLabel(parent, text=label).grid(row=0, column=column, sticky="ew", padx=styles.Spacing.SM, pady=(styles.Padding.FRAME_Y, styles.Spacing.XS))
        widget.grid(row=1, column=column, sticky="ew", padx=styles.Spacing.SM, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))

    def _sync_posts(self):
        self.post_options = [f"{post['id']} | {post.get('title') or 'Untitled Post'}" for post in self.posts]
        values = self.post_options or ["No Ready posts"]
        self.post_select.configure(values=values)
        if self.post_var.get() not in values:
            self.post_var.set(values[0])
        self._on_post_changed(self.post_var.get())

    def _on_post_changed(self, _value):
        post = self._selected_post()
        if not post:
            self.post_preview.configure(text="Select a Ready post.")
            return
        media = []
        if post.get("image_path"):
            media.append("Image")
        if post.get("video_path"):
            media.append("Video")
        if post.get("youtube_url"):
            media.append("YouTube")
        preview = (post.get("content") or "Media-only post").replace("\n", " ")[:180]
        self.post_preview.configure(text=f"{preview} | Media: {', '.join(media) if media else 'Text'} | Tags: {post.get('tags') or 'None'}")

    def _render_group_preview(self):
        names = [group["name"] for group in self.groups[:5]]
        suffix = "" if len(self.groups) <= 5 else f" +{len(self.groups) - 5} more"
        empty = "No selected Facebook groups for the active account." if self.platform_var.get() == "Facebook" else "No selected targets for the active account."
        self.groups_preview.configure(text=", ".join(names) + suffix if names else empty)

    def _selected_post(self):
        value = self.post_var.get()
        if "|" not in value:
            return None
        post_id = int(value.split("|", 1)[0].strip())
        for post in self.posts:
            if post["id"] == post_id:
                return post
        return None

    def _start(self):
        post = self._selected_post()
        if not post:
            self.current.set_status("Select a Ready post", "danger")
            return
        try:
            request = self.controller.build_request(
                platform=self.platform_var.get().lower(),
                account_id=self._selected_telegram_account_id(),
                target_ids=[target["id"] for target in self.telegram_targets if target.get("selected")],
                telegram_parse_mode=self.telegram_parse_mode_var.get(),
                post_id=post["id"],
                delay_min_seconds=self.delay_min_var.get(),
                delay_max_seconds=self.delay_max_var.get(),
                stop_on_checkpoint=bool(self.stop_checkpoint_var.get()),
                stop_on_block=bool(self.stop_block_var.get()),
                dry_run=bool(self.dry_run_var.get()),
                debug_one_group=bool(self.debug_one_group_var.get()),
                composer_debug_only=bool(self.composer_debug_only_var.get()),
                stop_after_consecutive_failures=self.stop_after_failures_var.get(),
            )
            self._reset_results()
            self.current.set_status("Starting", "info")
            self.controller.start_async(
                request,
                self._progress_from_thread,
                self._success_from_thread,
                self._error_from_thread,
            )
        except Exception as error:
            self.current.set_status(str(error), "danger")

    def _stop(self):
        self.controller.stop()
        self.current.set_status("Stop requested", "warning")

    def _progress_from_thread(self, event):
        self.after(0, lambda: self._handle_progress(event))

    def _success_from_thread(self, result):
        self.after(0, lambda: self._finish(result))

    def _error_from_thread(self, error):
        message = str(error)
        self.after(0, lambda: self.current.set_status(message, "danger"))

    def _handle_progress(self, event):
        name = event.get("event")
        data = event.get("data") or {}
        if name == "current":
            self.current.set_status(f"{data.get('group')} | {data.get('operation')}", "info")
        elif name == "delay":
            self.current.set_status(f"Delay: {data.get('remaining_seconds')}s", "neutral")
            self.cooldown.configure(text="Cooldown: inactive")
        elif name == "cooldown":
            remaining = data.get("remaining_seconds", 0)
            self.cooldown.configure(text=f"Cooldown: {remaining}s")
            self.current.set_status(f"Cooldown: {remaining}s", "warning")
        elif name == "group_progress":
            self.group_number.configure(
                text=f"Current group: {data.get('current', 0)} / {data.get('total', 0)}"
            )
            self.failure_count.configure(
                text=f"Current consecutive failures: {data.get('consecutive_failures', 0)}"
            )
        elif name == "rate_limited":
            self._show_rate_limit_warning(data)
        elif name == "result":
            self._append_result(data)
            self.current.set_status(data.get("message") or data.get("status") or "Result received", self._variant(data.get("status")))
            self._update_progress()
        elif name == "stopped":
            self.current.set_status(data.get("message") or "Stopped", "warning")

    def _append_result(self, item):
        row = ctk.CTkFrame(self.results_list, fg_color=colors.SURFACE_MUTED, corner_radius=styles.Radius.SM)
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=3)
        index = len(self.results_list.winfo_children())
        row.grid(row=index, column=0, sticky="ew", pady=styles.Spacing.XS)
        duration = self._duration(item)
        TableText(row, text=item.get("group_name") or item.get("target_id") or "", font=fonts.SMALL_BOLD).grid(row=0, column=0, sticky="ew", padx=styles.Spacing.SM, pady=styles.Spacing.SM)
        StatusBadge(row, text=item.get("status") or "", variant=self._variant(item.get("status"))).grid(row=0, column=1, padx=styles.Spacing.SM, pady=styles.Spacing.SM)
        TableText(row, text=f"{item.get('message') or ''} | {duration}", font=fonts.SMALL, text_color=colors.TEXT_MUTED).grid(row=0, column=2, sticky="ew", padx=styles.Spacing.SM, pady=styles.Spacing.SM)

    def _finish(self, result):
        data = result.get("data") or {}
        self.success_card.set_value(str(data.get("success_count", 0)))
        self.failed_card.set_value(str(data.get("failure_count", 0)))
        self.skipped_card.set_value(str(data.get("skipped_count", 0)))
        self.current.set_status(result.get("message") or "Finished", "success" if result.get("success") else "danger")
        self._update_progress(done=True)

    def _reset_results(self):
        for child in self.results_list.winfo_children():
            child.destroy()
        self.progress.set(0)
        self.success_card.set_value("0")
        self.failed_card.set_value("0")
        self.skipped_card.set_value("0")
        self.group_number.configure(text=f"Current group: 0 / {len(self.groups)}")
        self.failure_count.configure(text="Current consecutive failures: 0")
        self.cooldown.configure(text="Cooldown: inactive")

    def _update_progress(self, done=False):
        total = max(len(self.groups), 1)
        completed = len(self.results_list.winfo_children())
        self.progress.set(1 if done else min(completed / total, 1))

    def _duration(self, item):
        return f"{item.get('started_at', '')} -> {item.get('finished_at', '')}"

    def _variant(self, status):
        if status == "Success":
            return "success"
        if status == "Validated":
            return "info"
        if status in ["Failed", "Blocked", "Checkpoint", "PermissionDenied", "RateLimited"]:
            return "danger"
        if status in ["Skipped", "Stopped", "ValidationFailed"]:
            return "warning"
        return "neutral"

    def _open_groups(self):
        if self.platform_var.get() == "Telegram" and self.on_open_targets:
            self.on_open_targets()
        elif self.on_open_groups:
            self.on_open_groups()

    def _sync_telegram_accounts(self):
        values = [f"{account['id']} | {account['name']}" for account in self.telegram_accounts] or ["No Telegram bots"]
        self.telegram_account_select.configure(values=values)

        if self.telegram_account_var.get() not in values:
            self.telegram_account_var.set(values[0])

    def _selected_telegram_account_id(self):
        if self.platform_var.get() != "Telegram":
            return None

        value = self.telegram_account_var.get()

        if "|" not in value:
            raise ValueError("Select a Telegram bot account.")

        return int(value.split("|", 1)[0].strip())

    def _selected_telegram_account(self):
        value = self.telegram_account_var.get()

        if "|" not in value:
            return None

        account_id = int(value.split("|", 1)[0].strip())

        for account in self.telegram_accounts:
            if account["id"] == account_id:
                return account

        return None

    def _sync_platform_controls(self):
        telegram = self.platform_var.get() == "Telegram"
        state = "normal" if telegram else "disabled"
        facebook_state = "disabled" if telegram else "normal"
        self.telegram_account_select.configure(state=state)
        self.telegram_parse_mode_select.configure(state=state)
        self.stop_checkpoint_check.configure(state=facebook_state)
        self.stop_block_check.configure(state=facebook_state)
        self.composer_debug_only_check.configure(state=facebook_state)
        self.groups_count.title_label.configure(text="Selected Targets" if telegram else "Selected Groups")
        self.manage_groups_button.configure(text="Open Targets" if telegram else "Manage Groups")
        self.start_button.configure(
            state=(
                "normal"
                if telegram or self._facebook_publishing_available(self.active_account)
                else "disabled"
            )
        )

    def _show_rate_limit_warning(self, data):
        account_name = (self.active_account or {}).get("name") or str(data.get("account_id") or "")
        details = (
            f"{data.get('message') or ''}\n\n"
            f"Affected account: {account_name}\n"
            f"Detection time: {data.get('detection_time') or ''}\n"
            f"Current group: {data.get('current_group') or ''}\n"
            f"Completed: {data.get('completed_count', 0)}\n"
            f"Remaining: {data.get('remaining_count', 0)}"
        )
        self.current.set_status("Facebook posting is rate-limited", "danger")
        self.start_button.configure(state="disabled")
        messagebox.showwarning("Facebook Posting Limited", details, parent=self)

    @staticmethod
    def _facebook_publishing_available(account):
        return bool(
            account
            and (account.get("publishing_state") or "Available") == "Available"
        )
