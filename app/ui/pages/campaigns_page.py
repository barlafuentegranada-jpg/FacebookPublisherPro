from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from app.controllers.campaigns_controller import CampaignsController
from app.ui.theme import colors, fonts, styles
from app.ui.widgets import (
    CheckBox,
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


class CampaignsPage(ctk.CTkFrame):
    route = "campaigns"
    title = "Campaigns"

    def __init__(self, master, controller=None, on_open_history=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)
        self.controller = controller or CampaignsController()
        self.on_open_history = on_open_history
        self.selected_campaign_id = None
        self.account_vars = {}
        self.target_vars = {}
        self.target_search_var = ctk.StringVar()

        self.name_var = ctk.StringVar()
        self.description_var = ctk.StringVar()
        self.post_var = ctk.StringVar(value="No Ready posts")
        self.delay_min_var = ctk.StringVar(value="0")
        self.delay_max_var = ctk.StringVar(value="0")
        self.stop_on_error_var = ctk.BooleanVar(value=False)
        self.stop_on_checkpoint_var = ctk.BooleanVar(value=True)
        self.continue_after_facebook_rate_limit_var = ctk.BooleanVar(value=False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_campaign_list()
        self._build_editor()
        self._build_execution_panel()
        self.refresh()

    def refresh(self):
        self.campaigns = self.controller.load()
        self.posts = self.controller.ready_posts()
        self.accounts = self.controller.available_accounts()
        self._render_campaigns()
        self._sync_post_selector()

        if self.selected_campaign_id:
            self._load_campaign(self.selected_campaign_id)

    def _build_toolbar(self):
        panel = SectionPanel(self)
        panel.grid(row=0, column=0, columnspan=2, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Padding.PAGE_Y, styles.Spacing.MD))

        for column in range(5):
            panel.grid_columnconfigure(column, weight=1)

        PrimaryButton(panel, text="New Campaign", command=self._new_campaign).grid(row=0, column=0, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        SecondaryButton(panel, text="Duplicate", command=self._duplicate_campaign).grid(row=0, column=1, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        DangerButton(panel, text="Delete", command=self._delete_campaign).grid(row=0, column=2, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        SecondaryButton(panel, text="Archive", command=self._archive_campaign).grid(row=0, column=3, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        SecondaryButton(panel, text="Refresh", command=self.refresh).grid(row=0, column=4, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)

    def _build_campaign_list(self):
        panel = SectionPanel(self)
        panel.grid(row=1, column=0, sticky="nsew", padx=(styles.Padding.PAGE_X, styles.Spacing.MD), pady=(styles.Radius.NONE, styles.Padding.PAGE_Y))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        SectionTitle(panel, text="Campaign List").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.campaign_rows = ctk.CTkScrollableFrame(panel, fg_color=colors.TRANSPARENT, corner_radius=styles.Radius.NONE)
        self.campaign_rows.grid(row=1, column=0, sticky="nsew", padx=styles.Padding.FRAME_X, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))
        self.campaign_rows.grid_columnconfigure(0, weight=1)

    def _build_editor(self):
        self.editor = SectionPanel(self)
        self.editor.grid(row=1, column=1, sticky="nsew", padx=(styles.Radius.NONE, styles.Padding.PAGE_X), pady=(styles.Radius.NONE, styles.Padding.PAGE_Y))
        self.editor.grid_columnconfigure(0, weight=1)
        self.editor.grid_columnconfigure(1, weight=1)
        self.editor.grid_rowconfigure(6, weight=1)

        SectionTitle(self.editor, text="Campaign Editor").grid(row=0, column=0, columnspan=2, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self._field(self.editor, 1, 0, "Name", TextInput(self.editor, textvariable=self.name_var))
        self._field(self.editor, 1, 1, "Description", TextInput(self.editor, textvariable=self.description_var))
        self.post_select = SelectBox(self.editor, values=["No Ready posts"], variable=self.post_var)
        self._field(self.editor, 2, 0, "Saved Ready Post", self.post_select)
        self._field(self.editor, 2, 1, "Delay Minimum", TextInput(self.editor, textvariable=self.delay_min_var))
        self._field(self.editor, 3, 0, "Delay Maximum", TextInput(self.editor, textvariable=self.delay_max_var))
        CheckBox(self.editor, text="Stop on error", variable=self.stop_on_error_var).grid(row=3, column=1, sticky="w", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        CheckBox(self.editor, text="Stop on checkpoint", variable=self.stop_on_checkpoint_var).grid(row=4, column=0, sticky="w", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        CheckBox(
            self.editor,
            text="Continue other platforms after Facebook rate limit",
            variable=self.continue_after_facebook_rate_limit_var,
        ).grid(row=4, column=1, sticky="w", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

        self.accounts_panel = ctk.CTkScrollableFrame(self.editor, fg_color=colors.TRANSPARENT, corner_radius=styles.Radius.NONE, height=140)
        self.accounts_panel.grid(row=5, column=0, sticky="nsew", padx=styles.Padding.FRAME_X, pady=styles.Spacing.SM)
        self.accounts_panel.grid_columnconfigure(0, weight=1)
        self.targets_panel = ctk.CTkScrollableFrame(self.editor, fg_color=colors.TRANSPARENT, corner_radius=styles.Radius.NONE, height=240)
        self.targets_panel.grid(row=5, column=1, rowspan=2, sticky="nsew", padx=styles.Padding.FRAME_X, pady=styles.Spacing.SM)
        self.targets_panel.grid_columnconfigure(0, weight=1)

        target_tools = ctk.CTkFrame(self.editor, fg_color=colors.TRANSPARENT)
        target_tools.grid(row=6, column=0, sticky="new", padx=styles.Padding.FRAME_X, pady=styles.Spacing.SM)
        target_tools.grid_columnconfigure(0, weight=1)
        SearchBox(target_tools, textvariable=self.target_search_var, placeholder_text="Search targets").grid(row=0, column=0, sticky="ew", pady=styles.Spacing.XS)
        self.target_search_var.trace_add("write", lambda *_args: self._render_targets())
        SecondaryButton(target_tools, text="Select All", command=lambda: self._set_targets(True)).grid(row=1, column=0, sticky="ew", pady=styles.Spacing.XS)
        SecondaryButton(target_tools, text="Unselect All", command=lambda: self._set_targets(False)).grid(row=2, column=0, sticky="ew", pady=styles.Spacing.XS)

        self.validation_text = TableText(self.editor, text="", text_color=colors.TEXT_MUTED)
        self.validation_text.grid(row=7, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        PrimaryButton(self.editor, text="Save Campaign", command=self._save_campaign).grid(row=7, column=1, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

    def _build_execution_panel(self):
        panel = SectionPanel(self)
        panel.grid(row=2, column=0, columnspan=2, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Radius.NONE, styles.Padding.PAGE_Y))
        for column in range(8):
            panel.grid_columnconfigure(column, weight=1)

        self.execution_text = TableText(panel, text="No campaign running.", text_color=colors.TEXT_MUTED)
        self.execution_text.grid(row=0, column=0, columnspan=5, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.start_button = PrimaryButton(panel, text="Start", command=self._start_campaign, state="disabled")
        self.start_button.grid(row=0, column=5, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        DangerButton(panel, text="Stop", command=self.controller.stop).grid(row=0, column=6, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        SecondaryButton(panel, text="Open History", command=self._open_history).grid(row=0, column=7, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)

    def _field(self, master, row, column, label, widget):
        FieldLabel(master, text=label).grid(row=row * 2 - 1, column=column, sticky="ew", padx=styles.Padding.FRAME_X, pady=(styles.Spacing.SM, styles.Spacing.XS))
        widget.grid(row=row * 2, column=column, sticky="ew", padx=styles.Padding.FRAME_X, pady=(styles.Radius.NONE, styles.Spacing.SM))

    def _render_campaigns(self):
        for child in self.campaign_rows.winfo_children():
            child.destroy()

        if not self.campaigns:
            TableText(self.campaign_rows, text="No campaigns yet.", text_color=colors.TEXT_MUTED).grid(row=0, column=0, sticky="ew")
            return

        for index, campaign in enumerate(self.campaigns):
            row = ctk.CTkFrame(self.campaign_rows, fg_color=colors.SURFACE_ALT, corner_radius=styles.Radius.SM)
            row.grid(row=index, column=0, sticky="ew", pady=styles.Spacing.XS)
            row.grid_columnconfigure(0, weight=2)
            row.grid_columnconfigure(1, weight=1)
            row.grid_columnconfigure(2, weight=1)

            title = f"{campaign['name']} | {campaign.get('platforms_summary') or '-'} | {campaign.get('accounts_count', 0)} accounts | {campaign.get('targets_count', 0)} targets"
            SecondaryButton(row, text=title, anchor="w", command=lambda campaign_id=campaign["id"]: self._load_campaign(campaign_id)).grid(row=0, column=0, sticky="ew", padx=styles.Spacing.SM, pady=styles.Spacing.SM)
            StatusBadge(row, text=campaign.get("status") or "Draft").grid(row=0, column=1, sticky="ew", padx=styles.Spacing.SM, pady=styles.Spacing.SM)
            TableText(row, text=f"{campaign.get('success_rate', 0)}%", font=fonts.SMALL, text_color=colors.TEXT_MUTED).grid(row=0, column=2, sticky="ew", padx=styles.Spacing.SM, pady=styles.Spacing.SM)

    def _load_campaign(self, campaign_id):
        campaign = self.controller.get(campaign_id)

        if not campaign:
            return

        self.selected_campaign_id = campaign_id
        self.name_var.set(campaign.get("name") or "")
        self.description_var.set(campaign.get("description") or "")
        self.delay_min_var.set(str(campaign.get("delay_min_seconds") or 0))
        self.delay_max_var.set(str(campaign.get("delay_max_seconds") or 0))
        self.stop_on_error_var.set(bool(campaign.get("stop_on_error")))
        self.stop_on_checkpoint_var.set(bool(campaign.get("stop_on_checkpoint")))
        self.continue_after_facebook_rate_limit_var.set(
            bool(campaign.get("continue_other_platforms_after_facebook_rate_limit"))
        )
        self._set_post_value(campaign.get("post_id"))
        self._render_accounts(campaign.get("accounts") or [])
        self._render_targets(campaign.get("targets") or [])
        self._render_validation(campaign.get("validation") or {"valid": False, "errors": []})

    def _render_accounts(self, selected_accounts=None):
        selected = {
            (account["platform"], int(account["account_id"]))
            for account in selected_accounts or []
            if account.get("enabled", 1)
        }
        self.account_vars = {}

        for child in self.accounts_panel.winfo_children():
            child.destroy()

        SectionTitle(self.accounts_panel, text="Accounts").grid(row=0, column=0, sticky="ew", pady=styles.Spacing.XS)
        for row_index, account in enumerate(self.accounts, start=1):
            value = ctk.BooleanVar(value=(account["platform"], account["id"]) in selected)
            self.account_vars[(account["platform"], account["id"])] = value
            state = "normal" if account["connected"] else "disabled"
            label = f"{account['platform']} | {account['name']} | {account['status']}"
            CheckBox(self.accounts_panel, text=label, variable=value, state=state, command=self._render_targets).grid(row=row_index, column=0, sticky="w", pady=styles.Spacing.XS)

    def _render_targets(self, selected_targets=None):
        selected = {
            (target["platform"], int(target["account_id"]), int(target["target_id"]))
            for target in selected_targets or []
            if target.get("enabled", 1)
        }
        current = {key: var.get() for key, var in self.target_vars.items()}
        self.target_vars = {}

        for child in self.targets_panel.winfo_children():
            child.destroy()

        SectionTitle(self.targets_panel, text="Targets").grid(row=0, column=0, sticky="ew", pady=styles.Spacing.XS)
        account_ids = [account_id for (_platform, account_id), var in self.account_vars.items() if var.get()]
        targets = self.controller.available_targets(account_ids=account_ids)
        search = self.target_search_var.get().strip().lower()
        row_index = 1
        counts = {}

        for target in targets:
            if search and search not in (target["name"] or "").lower():
                continue

            key = (target["platform"], int(target["account_id"]), int(target["target_id"]))
            value = ctk.BooleanVar(value=current.get(key, key in selected or bool(target.get("enabled"))))
            self.target_vars[key] = value
            counts[(target["platform"], target["account_name"])] = counts.get((target["platform"], target["account_name"]), 0) + 1
            label = f"{target['platform']} | {target['account_name']} | {target['name']}"
            CheckBox(self.targets_panel, text=label, variable=value).grid(row=row_index, column=0, sticky="w", pady=styles.Spacing.XS)
            row_index += 1

        if row_index == 1:
            TableText(self.targets_panel, text="Select connected accounts to load targets.", text_color=colors.TEXT_MUTED).grid(row=1, column=0, sticky="ew")
        else:
            summary = ", ".join(f"{platform}/{account}: {count}" for (platform, account), count in sorted(counts.items()))
            TableText(self.targets_panel, text=summary, font=fonts.SMALL, text_color=colors.TEXT_MUTED).grid(row=row_index, column=0, sticky="ew", pady=styles.Spacing.SM)

    def _sync_post_selector(self):
        values = [f"{post['id']} | {post['title'] or 'Untitled'}" for post in self.posts] or ["No Ready posts"]
        self.post_select.configure(values=values)
        if self.post_var.get() not in values:
            self.post_var.set(values[0])

    def _set_post_value(self, post_id):
        for post in self.posts:
            if int(post["id"]) == int(post_id or 0):
                self.post_var.set(f"{post['id']} | {post['title'] or 'Untitled'}")
                return

        self._sync_post_selector()

    def _new_campaign(self):
        campaign = self.controller.create()
        self.refresh()
        self._load_campaign(campaign["id"])

    def _save_campaign(self):
        if not self.selected_campaign_id:
            self._new_campaign()

        data = {
            "name": self.name_var.get(),
            "description": self.description_var.get(),
            "post_id": self._selected_post_id(),
            "delay_min_seconds": self.delay_min_var.get(),
            "delay_max_seconds": self.delay_max_var.get(),
            "stop_on_error": self.stop_on_error_var.get(),
            "stop_on_checkpoint": self.stop_on_checkpoint_var.get(),
            "continue_other_platforms_after_facebook_rate_limit": self.continue_after_facebook_rate_limit_var.get(),
            "accounts": [
                {"platform": platform, "account_id": account_id, "enabled": 1}
                for (platform, account_id), var in self.account_vars.items()
                if var.get()
            ],
            "targets": [
                {"platform": platform, "account_id": account_id, "target_id": target_id, "enabled": 1}
                for (platform, account_id, target_id), var in self.target_vars.items()
                if var.get()
            ],
        }
        campaign = self.controller.save(self.selected_campaign_id, data)
        self.refresh()
        self._load_campaign(campaign["id"])

    def _duplicate_campaign(self):
        if not self.selected_campaign_id:
            return

        campaign = self.controller.duplicate(self.selected_campaign_id)
        self.refresh()
        if campaign:
            self._load_campaign(campaign["id"])

    def _delete_campaign(self):
        if not self.selected_campaign_id:
            return

        self.controller.delete(self.selected_campaign_id)
        self.selected_campaign_id = None
        self.refresh()

    def _archive_campaign(self):
        if not self.selected_campaign_id:
            return

        self.controller.archive(self.selected_campaign_id)
        self.selected_campaign_id = None
        self.refresh()

    def _start_campaign(self):
        if not self.selected_campaign_id:
            return

        self._save_campaign()
        validation = self.controller.validate(self.selected_campaign_id)
        self._render_validation(validation)

        if not validation["valid"]:
            return

        self.controller.start_async(
            self.selected_campaign_id,
            on_progress=lambda payload: self.after(0, lambda: self._render_progress(payload)),
            on_success=lambda result: self.after(0, lambda: self._campaign_finished(result)),
            on_error=lambda error: self.after(0, lambda: self._campaign_error(error)),
        )

    def _render_progress(self, payload):
        run = payload.get("run") or {}
        total = run.get("total_targets") or 0
        remaining = max(total - int(payload.get("processed") or 0), 0)
        text = (
            f"{payload.get('campaign_name') or ''} | {payload.get('operation') or ''} | "
            f"{payload.get('platform') or '-'} account {payload.get('account_id') or '-'} | "
            f"{payload.get('target_name') or '-'} | "
            f"{payload.get('processed', 0)}/{total} processed | "
            f"success {payload.get('success', 0)} failed {payload.get('failed', 0)} skipped {payload.get('skipped', 0)} | "
            f"remaining {remaining} | delay {payload.get('delay_remaining', 0)}s"
        )
        self.execution_text.configure(text=text)

        if payload.get("operation") == "Facebook rate limit":
            messagebox.showwarning(
                "Facebook Posting Limited",
                "Facebook temporarily limited posting for this account.\n"
                "Publishing has been stopped. Review Facebook Account Status and "
                "Support Inbox before trying again.\n\n"
                f"Affected account: {payload.get('account_id') or ''}\n"
                f"Detection time: {payload.get('detection_time') or datetime.now().isoformat(timespec='seconds')}\n"
                f"Current group: {payload.get('target_name') or ''}\n"
                f"Completed: {payload.get('processed', 0)}\n"
                f"Remaining: {remaining}",
                parent=self,
            )

    def _campaign_finished(self, result):
        self.execution_text.configure(text=result.get("message") or "Campaign finished.")
        self.refresh()

    def _campaign_error(self, error):
        self.execution_text.configure(text=str(error))
        self.refresh()

    def _render_validation(self, validation):
        if validation.get("valid"):
            self.validation_text.configure(text="Ready", text_color=colors.SUCCESS)
            self.start_button.configure(state="normal")
            return

        self.validation_text.configure(text=" | ".join(validation.get("errors") or ["Draft"]), text_color=colors.WARNING)
        self.start_button.configure(state="disabled")

    def _selected_post_id(self):
        value = self.post_var.get()
        if not value or value == "No Ready posts":
            return None
        return int(value.split("|", 1)[0].strip())

    def _set_targets(self, selected):
        for var in self.target_vars.values():
            var.set(bool(selected))

    def _open_history(self):
        if self.on_open_history:
            self.on_open_history()
