import customtkinter as ctk
from tkinter import messagebox

from app.controllers.accounts_controller import AccountsController
from app.ui.theme import colors, styles
from app.ui.widgets import (
    AccountCard,
    PromptDialog,
    PrimaryButton,
    SectionPanel,
    SectionTitle,
    StatusBadge,
)


class AccountsPage(ctk.CTkFrame):
    route = "accounts"
    title = "Accounts"

    def __init__(self, master, controller=None, on_accounts_changed=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)

        self.controller = controller or AccountsController()
        self.on_accounts_changed = on_accounts_changed

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_accounts()
        self.refresh()

    def refresh(self):
        accounts = self.controller.list_accounts()
        self._render_accounts(accounts)
        self._notify_changed()

    def _build_toolbar(self):
        toolbar = SectionPanel(self)
        toolbar.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Padding.PAGE_Y, styles.Spacing.MD),
        )
        toolbar.grid_columnconfigure(0, weight=1)

        SectionTitle(
            toolbar,
            text="Facebook Accounts",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Padding.FRAME_Y,
        )

        self.status = StatusBadge(toolbar, text="Ready", variant="neutral")
        self.status.grid(row=0, column=1, padx=styles.Spacing.SM)

        PrimaryButton(
            toolbar,
            text="Add Account",
            command=self._add_account,
        ).grid(
            row=0,
            column=2,
            padx=(styles.Spacing.SM, styles.Padding.FRAME_X),
            pady=styles.Padding.FRAME_Y,
        )

    def _build_accounts(self):
        self.accounts_panel = SectionPanel(self)
        self.accounts_panel.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styles.Padding.PAGE_X,
            pady=(styles.Radius.NONE, styles.Padding.PAGE_Y),
        )
        self.accounts_panel.grid_columnconfigure(0, weight=1)
        self.accounts_panel.grid_rowconfigure(0, weight=1)

        self.accounts_list = ctk.CTkScrollableFrame(
            self.accounts_panel,
            fg_color=colors.TRANSPARENT,
            corner_radius=styles.Radius.NONE,
        )
        self.accounts_list.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=styles.Padding.FRAME_X,
            pady=styles.Padding.FRAME_Y,
        )
        self.accounts_list.grid_columnconfigure(0, weight=1)

    def _render_accounts(self, accounts):
        for child in self.accounts_list.winfo_children():
            child.destroy()

        if not accounts:
            StatusBadge(
                self.accounts_list,
                text="No accounts yet. Add one to begin.",
                variant="info",
            ).grid(row=0, column=0, sticky="w", pady=styles.Spacing.MD)
            return

        for index, account in enumerate(accounts):
            AccountCard(
                self.accounts_list,
                account=account,
                on_rename=self._rename_account,
                on_login=self._open_login,
                on_set_active=self._set_active,
                on_open_browser=self._open_browser,
                on_refresh_status=self._refresh_status,
                on_reset_profile=self._reset_profile,
                on_remove=self._remove_account,
            ).grid(row=index, column=0, sticky="ew", pady=styles.Spacing.SM)

    def _add_account(self):
        PromptDialog(
            self,
            title="Add Account",
            label="Account display name",
            on_submit=self._create_account,
        )

    def _create_account(self, name):
        try:
            self.controller.add_account(name)
            self._set_status("Account added", "success")
            self.refresh()
        except Exception as error:
            self._set_status(str(error), "danger")

    def _rename_account(self, account_id):
        account = self._account(account_id)
        PromptDialog(
            self,
            title="Rename Account",
            label="Account display name",
            initial_value=account["name"],
            on_submit=lambda name: self._save_rename(account_id, name),
        )

    def _save_rename(self, account_id, name):
        try:
            self.controller.rename_account(account_id, name)
            self._set_status("Account renamed", "success")
            self.refresh()
        except Exception as error:
            self._set_status(str(error), "danger")

    def _set_active(self, account_id):
        try:
            self.controller.set_active(account_id)
            self._set_status("Active account updated", "success")
            self.refresh()
        except Exception as error:
            self._set_status(str(error), "danger")

    def _open_login(self, account_id):
        self._set_status("Opening manual Chrome login...", "info")
        self.controller.open_login_async(
            account_id,
            self._thread_success(
                "Complete Facebook login in Chrome, then close Chrome and click Check Login."
            ),
            self._thread_error,
        )

    def _open_browser(self, account_id):
        self._set_status("Opening browser...", "info")
        self.controller.open_browser_async(
            account_id,
            self._thread_success("Browser opened"),
            self._thread_error,
        )

    def _refresh_status(self, account_id):
        self._set_status("Checking login. Chrome must be closed first...", "info")
        self.controller.refresh_status_async(
            account_id,
            self._thread_success("Status refreshed"),
            self._thread_error,
        )

    def _remove_account(self, account_id):
        try:
            self.controller.remove_account(account_id)
            self._set_status("Account removed", "warning")
            self.refresh()
        except Exception as error:
            self._set_status(str(error), "danger")

    def _reset_profile(self, account_id):
        confirmed = messagebox.askyesno(
            "Reset Login Profile",
            "Close the browser and reset this account login profile? The old profile will be renamed as a backup.",
            parent=self,
        )

        if not confirmed:
            return

        try:
            result = self.controller.reset_login_profile(account_id)
            backup_path = result.get("backup_path")
            message = "Login profile reset"

            if backup_path:
                message = f"{message}. Backup: {backup_path}"

            self._set_status(message, "warning")
            self.refresh()
        except Exception as error:
            self._set_status(str(error), "danger")

    def _thread_success(self, message):
        def callback(_result):
            self.after(0, lambda: self._finish_async(message, "success"))

        return callback

    def _thread_error(self, error):
        self.after(0, lambda: self._finish_async(str(error), "danger"))

    def _finish_async(self, message, variant):
        self._set_status(message, variant)
        self.refresh()

    def _set_status(self, text, variant):
        self.status.set_status(text, variant)

    def _notify_changed(self):
        if self.on_accounts_changed:
            self.on_accounts_changed()

    def _account(self, account_id):
        for account in self.controller.list_accounts():
            if account["id"] == account_id:
                return account

        raise ValueError("Account not found.")
