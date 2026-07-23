import customtkinter as ctk

from app.controllers.telegram_controller import TelegramController
from app.ui.theme import colors, fonts, styles
from app.ui.widgets import (
    CheckBox,
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


class TelegramPage(ctk.CTkFrame):
    route = "telegram"
    title = "Telegram"

    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, fg_color=colors.TRANSPARENT, **kwargs)
        self.controller = controller or TelegramController()
        self.account_var = ctk.StringVar(value="No Telegram bots")
        self.target_var = ctk.StringVar(value="No targets")
        self.target_input_var = ctk.StringVar()
        self.test_text_var = ctk.StringVar()
        self.accounts = []
        self.targets = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_accounts()
        self._build_targets()
        self._build_test_message()
        self.refresh()

    def refresh(self):
        self.accounts = self.controller.accounts()
        self._sync_accounts()
        self.targets = self.controller.targets(self._selected_account_id())
        self._sync_targets()
        self._render_targets()

    def _build_accounts(self):
        panel = SectionPanel(self)
        panel.grid(row=0, column=0, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Padding.PAGE_Y, styles.Spacing.MD))
        panel.grid_columnconfigure(1, weight=1)
        SectionTitle(panel, text="Bot Accounts").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

        self.account_select = SelectBox(panel, values=["No Telegram bots"], variable=self.account_var, command=lambda _value: self.refresh())
        self.account_select.grid(row=0, column=1, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)

        self.account_status = StatusBadge(panel, text="Ready", variant="neutral")
        self.account_status.grid(row=0, column=2, padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)

        SecondaryButton(panel, text="Check Connection", command=self._check_connection).grid(row=0, column=3, padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        SecondaryButton(panel, text="Remove", command=self._remove_account).grid(row=0, column=4, padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

    def _build_targets(self):
        panel = SectionPanel(self)
        panel.grid(row=1, column=0, sticky="nsew", padx=styles.Padding.PAGE_X, pady=(styles.Radius.NONE, styles.Spacing.MD))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        SectionTitle(panel, text="Targets").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.target_input = SearchBox(panel, textvariable=self.target_input_var, placeholder_text="@channel_username or numeric chat id")
        self.target_input.grid(row=0, column=1, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        PrimaryButton(panel, text="Add Target", command=self._add_target).grid(row=0, column=2, padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        SecondaryButton(panel, text="Discover Recent Chats", command=self._discover).grid(row=0, column=3, padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        SecondaryButton(panel, text="Refresh", command=self.refresh).grid(row=0, column=4, padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

        header = ctk.CTkFrame(panel, fg_color=colors.TRANSPARENT)
        header.grid(row=1, column=0, columnspan=5, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        columns = ["Selected", "Type", "Title", "Username / Chat ID", "Permission", "Status"]

        for index, label in enumerate(columns):
            header.grid_columnconfigure(index, weight=1)
            TableText(header, text=label, font=fonts.SMALL_BOLD).grid(row=0, column=index, sticky="ew", padx=styles.Spacing.XS)

        self.targets_rows = ctk.CTkScrollableFrame(panel, fg_color=colors.TRANSPARENT, corner_radius=styles.Radius.NONE)
        self.targets_rows.grid(row=2, column=0, columnspan=5, sticky="nsew", padx=styles.Padding.FRAME_X, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))

        for index in range(len(columns)):
            self.targets_rows.grid_columnconfigure(index, weight=1)

    def _build_test_message(self):
        panel = SectionPanel(self)
        panel.grid(row=2, column=0, sticky="ew", padx=styles.Padding.PAGE_X, pady=(styles.Radius.NONE, styles.Padding.PAGE_Y))
        panel.grid_columnconfigure(1, weight=1)
        SectionTitle(panel, text="Test Message").grid(row=0, column=0, sticky="ew", padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.target_select = SelectBox(panel, values=["No targets"], variable=self.target_var)
        self.target_select.grid(row=0, column=1, sticky="ew", padx=styles.Spacing.SM, pady=styles.Padding.FRAME_Y)
        self.test_input = TextInput(panel, textvariable=self.test_text_var, placeholder_text="Short test message")
        self.test_input.grid(row=1, column=1, sticky="ew", padx=styles.Spacing.SM, pady=(styles.Radius.NONE, styles.Padding.FRAME_Y))
        PrimaryButton(panel, text="Send Test", command=self._send_test).grid(row=1, column=2, padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)
        self.test_status = StatusBadge(panel, text="Ready", variant="neutral")
        self.test_status.grid(row=0, column=2, padx=styles.Padding.FRAME_X, pady=styles.Padding.FRAME_Y)

    def _sync_accounts(self):
        values = [f"{account['id']} | {account['name']} (@{account.get('bot_username') or 'unknown'})" for account in self.accounts]
        values = values or ["No Telegram bots"]
        self.account_select.configure(values=values)

        if self.account_var.get() not in values:
            self.account_var.set(values[0])

        account = self._selected_account()
        status = account.get("status") if account else "No bot"
        self.account_status.set_status(status, "success" if status == "Connected" else "warning")

    def _sync_targets(self):
        values = [f"{target['id']} | {target.get('name') or target.get('external_id')}" for target in self.targets]
        values = values or ["No targets"]
        self.target_select.configure(values=values)

        if self.target_var.get() not in values:
            self.target_var.set(values[0])

    def _render_targets(self):
        for child in self.targets_rows.winfo_children():
            child.destroy()

        if not self.targets:
            TableText(self.targets_rows, text="No Telegram targets yet.", text_color=colors.TEXT_MUTED).grid(row=0, column=0, sticky="ew", pady=styles.Spacing.MD)
            return

        for row_index, target in enumerate(self.targets):
            selected_var = ctk.IntVar(value=1 if target.get("selected") else 0)
            CheckBox(
                self.targets_rows,
                text="",
                variable=selected_var,
                command=lambda target_id=target["id"], variable=selected_var: self._set_selected(target_id, variable.get()),
            ).grid(row=row_index, column=0, sticky="w", padx=styles.Spacing.XS, pady=styles.Spacing.XS)
            values = [
                target.get("target_type") or "",
                target.get("name") or "",
                target.get("username") or target.get("external_id") or "",
                "Can post" if target.get("can_post") else "No permission",
                target.get("status") or "",
            ]

            for column_index, value in enumerate(values, start=1):
                TableText(self.targets_rows, text=str(value)[:120], font=fonts.SMALL).grid(row=row_index, column=column_index, sticky="ew", padx=styles.Spacing.XS, pady=styles.Spacing.XS)

    def _selected_account_id(self):
        value = self.account_var.get()

        if "|" not in value:
            return None

        return int(value.split("|", 1)[0].strip())

    def _selected_account(self):
        account_id = self._selected_account_id()

        for account in self.accounts:
            if account["id"] == account_id:
                return account

        return None

    def _selected_target_id(self):
        value = self.target_var.get()

        if "|" not in value:
            return None

        return int(value.split("|", 1)[0].strip())

    def _check_connection(self):
        account_id = self._selected_account_id()

        if not account_id:
            self.account_status.set_status("Choose a bot", "warning")
            return

        self.account_status.set_status("Checking", "info")
        self.controller.run_async(
            lambda: self.controller.check_connection(account_id),
            lambda _result: self.after(0, lambda: self._finish("Connected", "success")),
            lambda error: self.after(0, lambda: self._finish(str(error), "danger")),
        )

    def _remove_account(self):
        account_id = self._selected_account_id()

        if not account_id:
            return

        self.controller.remove_account(account_id)
        self.refresh()

    def _add_target(self):
        account_id = self._selected_account_id()
        chat_identifier = self.target_input_var.get().strip()

        if not account_id or not chat_identifier:
            self.account_status.set_status("Choose bot and target", "warning")
            return

        self.account_status.set_status("Adding target", "info")
        self.controller.run_async(
            lambda: self.controller.add_target(account_id, chat_identifier),
            lambda _result: self.after(0, lambda: self._finish("Target added", "success")),
            lambda error: self.after(0, lambda: self._finish(str(error), "danger")),
        )

    def _discover(self):
        account_id = self._selected_account_id()

        if not account_id:
            self.account_status.set_status("Choose a bot", "warning")
            return

        self.account_status.set_status("Discovering", "info")
        self.controller.run_async(
            lambda: self.controller.discover_recent_chats(account_id),
            lambda result: self.after(0, lambda: self._finish(f"{len(result)} chats discovered", "success")),
            lambda error: self.after(0, lambda: self._finish(str(error), "danger")),
        )

    def _set_selected(self, target_id, selected):
        self.controller.set_target_selected(target_id, selected)
        self.refresh()

    def _send_test(self):
        account_id = self._selected_account_id()
        target_id = self._selected_target_id()
        text = self.test_text_var.get().strip()

        if not account_id or not target_id or not text:
            self.test_status.set_status("Choose target and text", "warning")
            return

        self.test_status.set_status("Sending", "info")
        self.controller.run_async(
            lambda: self.controller.send_test_message(account_id, target_id, text),
            lambda result: self.after(0, lambda: self.test_status.set_status(result.get("message") or "Sent", "success" if result.get("success") else "danger")),
            lambda error: self.after(0, lambda: self.test_status.set_status(str(error), "danger")),
        )

    def _finish(self, message, variant):
        self.account_status.set_status(message, variant)
        self.refresh()
