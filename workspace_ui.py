"""Workspace, command palette, and personalization views."""
import copy
import json
import tkinter as tk
from tkinter import filedialog, ttk

import calculator_ui as legacy
from calculator_ui import BG, PANEL, INPUT, TEXT, MUTED, CYAN, AMBER, MONO
from calculator_core import FUNCTIONS, format_number
from hub_core import ACCENTS, atomic_json
from intel import SOURCES
from tool_library import RECIPES


class WorkspaceMixin:
    def build_workspace(self):
        page = self.pages["workspace"]
        toolbar = self.panel(page)
        toolbar.pack(fill="x", pady=(0, 14))
        row = tk.Frame(toolbar, bg=PANEL)
        row.pack(fill="x", padx=16, pady=13)
        self.label(row, "NEW WORKSPACE", 9, MUTED, MONO).pack(side="left", padx=(0, 10))
        self.new_workspace_name = tk.StringVar()
        self.entry(row, self.new_workspace_name, 11).pack(side="left", fill="x", expand=True, ipady=9)
        self.button(row, "CREATE", self.create_workspace, "accent").pack(side="left", padx=12)
        self.button(row, "EXPORT BACKUP", self.export_workspace, "subtle").pack(side="right")
        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1, uniform="workspace_body")
        body.columnconfigure(1, weight=1, uniform="workspace_body")
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        self.label(left, "INVESTIGATION NOTES", 10, self.accent, MONO).pack(anchor="w", pady=(0, 10))
        self.notes_editor = self.make_text(left, height=12, editable=True)
        self.notes_editor.bind("<<Modified>>", self.notes_changed)
        self.notes_save_label = self.label(left, "Autosaved locally after edits.", 9, MUTED, MONO, anchor="w")
        self.notes_save_label.pack(fill="x", pady=(8, 12))
        watch = self.panel(left)
        watch.pack(fill="x")
        self.label(watch, "SOFTWARE WATCHLIST", 10, self.accent, MONO).pack(anchor="w", padx=15, pady=(13, 7))
        self.label(watch, "Comma-separated product or vendor names.", 9, MUTED,
                   anchor="w", justify="left", wraplength=self.px(430)).pack(fill="x", padx=15)
        self.watchlist_var = tk.StringVar()
        self.entry(watch, self.watchlist_var, 11).pack(fill="x", padx=15, pady=10, ipady=9)
        self.button(watch, "APPLY WATCHLIST", self.apply_watchlist, "cyan").pack(anchor="w", padx=15, pady=(0, 13))
        self.watchlist_var.trace_add("write", lambda *args: self.schedule_save())
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        self.label(right, "PINNED CALCULATIONS", 10, self.accent, MONO).pack(anchor="w", pady=(0, 10))
        self.pin_tree = self.make_tree(right, ("EXPRESSION", "RESULT"), (230, 210), height=4)
        self.pin_tree.bind("<Double-Button-1>", self.reuse_pin)
        self.pin_tree.bind("<Return>", self.reuse_pin)
        actions = tk.Frame(right, bg=BG)
        actions.pack(fill="x", pady=(10, 16))
        self.button(actions, "REUSE EXPRESSION", self.reuse_pin, "cyan").pack(side="left")
        self.button(actions, "REMOVE PIN", self.remove_pin, "subtle").pack(side="left", padx=8)
        self.label(right, "NAMED VARIABLES", 10, self.accent, MONO).pack(anchor="w", pady=(0, 10))
        self.variable_tree = self.make_tree(right, ("NAME", "VALUE"), (140, 300), height=3)
        actions = tk.Frame(right, bg=BG)
        actions.pack(fill="x", pady=(10, 0))
        self.button(actions, "REMOVE VARIABLE", self.remove_variable, "subtle").pack(side="left")
        self.label(actions, "Set one in Calculator: page_size = 4096", 9, MUTED).pack(side="left", padx=12)
        self.loading_workspace = False

    def load_workspace(self):
        self.loading_workspace = True
        workspace = self.store.workspace
        self.variables = workspace["variables"]
        self.ans = workspace.get("ans", 0)
        self.history = [tuple(row) for row in workspace["history"]]
        self.last_result = format_number(self.ans)
        self.result.set(self.last_result)
        self.expression.set(workspace.get("expression", ""))
        self.result_hint.configure(text="SAVED ANSWER  /  ENTER TO CALCULATE", fg=MUTED)
        self.render_history()
        self.notes_editor.delete("1.0", "end")
        self.notes_editor.insert("1.0", workspace["notes"])
        self.notes_editor.edit_modified(False)
        self.watchlist_var.set(", ".join(workspace["watchlist"]))
        self.workspace_choice.set(self.store.state["active"])
        self.workspace_combo.configure(values=tuple(self.store.state["workspaces"]))
        self.loading_workspace = False
        self.render_workspace()
        self.render_library()
        self.render_intelligence()
        self.refresh_dashboard()
        self.notes_save_label.configure(text="Autosaved locally after edits.")
        self.expression_entry.icursor("end")
        self.inspect_float()
        self.plot_graph()

    def capture_workspace(self):
        workspace = self.store.workspace
        notes = self.notes_editor.get("1.0", "end-1c")
        if len(notes) > 200000:
            raise ValueError("Notes exceed 200,000 characters. Shorten or export the text before saving.")
        terms = [term.strip() for term in self.watchlist_var.get().split(",") if term.strip()]
        if len(terms) > 40 or any(len(term) > 64 for term in terms):
            raise ValueError("Watchlists support 40 terms of up to 64 characters each.")
        workspace.update(history=[list(row) for row in self.history], variables=dict(self.variables),
                         ans=self.ans, expression=self.expression.get(), notes=notes,
                         watchlist=list(dict.fromkeys(terms)))

    def schedule_save(self):
        if not self._ready or getattr(self, "loading_workspace", False):
            return
        if self.save_job:
            self.after_cancel(self.save_job)
        self.save_job = self.after(750, self.save_now)

    def save_now(self, raise_error=False):
        if not self._ready:
            return True
        if self.save_job:
            self.after_cancel(self.save_job)
            self.save_job = None
        try:
            self.capture_workspace()
            self.store.save()
            self.notes_save_label.configure(text="Saved locally / " + self.store.state["active"])
            return True
        except (OSError, ValueError) as exc:
            self.status("Save failed: " + str(exc), True)
            self.notes_save_label.configure(text="Not saved. See status for details.")
            if raise_error:
                raise OSError(str(exc)) from exc
            return False

    def notes_changed(self, event=None):
        if self.notes_editor.edit_modified():
            self.notes_editor.edit_modified(False)
            self.notes_save_label.configure(text="Unsaved edits...")
            self.schedule_save()

    def render_workspace(self):
        if not hasattr(self, "pin_tree"):
            return
        self.pin_tree.delete(*self.pin_tree.get_children())
        for index, item in enumerate(self.store.workspace["pins"]):
            self.pin_tree.insert("", "end", iid=str(index), values=(item["expression"], item["result"]))
        self.variable_tree.delete(*self.variable_tree.get_children())
        for name, value in sorted(self.variables.items()):
            self.variable_tree.insert("", "end", iid=name, values=(name, format_number(value)))

    def switch_workspace(self, event=None):
        selected = self.workspace_choice.get()
        if selected == self.store.state["active"]:
            return
        if selected not in self.store.state["workspaces"] or not self.save_now():
            self.workspace_choice.set(self.store.state["active"])
            return
        self.store.state["active"] = selected
        self.load_workspace()
        self.save_now()
        self.status("Switched to workspace " + selected + ".")

    def create_workspace(self):
        if not self.save_now():
            return
        try:
            self.store.create(self.new_workspace_name.get())
        except (ValueError, OSError) as exc:
            self.status(str(exc), True)
            return
        self.new_workspace_name.set("")
        self.load_workspace()
        self.status("Created workspace " + self.store.state["active"] + ".")

    def export_workspace(self):
        if not self.save_now():
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json",
                                           initialfile="neon-workspace-backup.json",
                                           filetypes=[("JSON backup", "*.json")])
        if path:
            payload = {"version": 2, "active": self.store.state["active"],
                       "workspaces": {self.store.state["active"]: copy.deepcopy(self.store.workspace)},
                       "settings": dict(self.store.state["settings"])}
            try:
                atomic_json(path, payload)
                self.status("Workspace backup exported, including its notes and saved items.")
            except OSError as exc:
                self.status("Export failed: " + str(exc), True)

    def apply_watchlist(self):
        if self.save_now():
            self.render_intelligence()
            self.status("Software watchlist updated. Choose Watchlist in Threat intelligence.")

    def reuse_pin(self, event=None):
        selected = self.pin_tree.selection()
        if selected:
            item = self.store.workspace["pins"][int(selected[0])]
            self.show_page("calculator")
            self.expression.set(item["expression"])
            self.expression_entry.icursor("end")
            self.calculate()
        return "break"

    def remove_pin(self):
        selected = self.pin_tree.selection()
        if selected:
            self.store.workspace["pins"].pop(int(selected[0]))
            self.save_now()
            self.render_workspace()
            self.status("Pin removed.")

    def remove_variable(self):
        selected = self.variable_tree.selection()
        if selected:
            self.variables.pop(selected[0], None)
            self.save_now()
            self.render_workspace()
            self.status("Variable removed.")

    def build_settings(self):
        page = self.pages["settings"]
        upper = self.panel(page)
        upper.pack(fill="x", pady=(0, 15))
        self.label(upper, "PERSONALIZE THE INTERFACE", 10, self.accent, MONO).pack(anchor="w", padx=20, pady=(18, 12))
        row = tk.Frame(upper, bg=PANEL)
        row.pack(fill="x", padx=20, pady=(0, 17))
        self.label(row, "ACCENT COLOR", 9, MUTED, MONO).pack(side="left", padx=(0, 13))
        self.accent_choice = tk.StringVar(value=self.store.state["settings"]["accent"])
        selector = self.combo(row, self.accent_choice, ACCENTS, 16)
        selector.pack(side="left")
        selector.bind("<<ComboboxSelected>>", self.change_accent)
        self.reduced_motion = tk.BooleanVar(value=self.store.state["settings"]["reduced_motion"])
        tk.Checkbutton(row, text="Reduce motion", variable=self.reduced_motion, command=self.settings_changed,
                       bg=PANEL, fg=TEXT, selectcolor=INPUT, activebackground=PANEL,
                       activeforeground=self.accent, font=(MONO, 10)).pack(side="left", padx=25)
        connectivity = self.panel(page)
        connectivity.pack(fill="x", pady=(0, 15))
        self.label(connectivity, "INTELLIGENCE CONNECTIVITY", 10, self.accent, MONO).pack(anchor="w", padx=20, pady=(18, 12))
        self.online_news = tk.BooleanVar(value=self.store.state["settings"]["online_news"])
        self.automatic_news = tk.BooleanVar(value=self.store.state["settings"]["auto_refresh"])
        row = tk.Frame(connectivity, bg=PANEL)
        row.pack(fill="x", padx=20, pady=(0, 10))
        for text, variable in (("Enable public news feeds", self.online_news), ("Refresh every 30 minutes while open", self.automatic_news)):
            tk.Checkbutton(row, text=text, variable=variable, command=self.settings_changed, bg=PANEL, fg=TEXT,
                           selectcolor=INPUT, activebackground=PANEL, activeforeground=self.accent,
                           font=(MONO, 10)).pack(side="left", padx=(0, 25))
        self.label(connectivity, "Online mode fetches public RSS and CISA data at startup when the cache is older than 30 minutes.\n"
                               "Offline mode keeps the cache and all local tools available. Notes and calculator inputs are never sent to these feeds.",
                   10, MUTED, justify="left", anchor="w").pack(fill="x", padx=20, pady=(0, 18))
        self.settings_sources = self.make_text(page, height=10)
        foot = self.panel(page)
        foot.pack(fill="x", pady=(15, 0))
        self.label(foot, "LOCAL WORKSPACE STORAGE", 10, self.accent, MONO).pack(anchor="w", padx=20, pady=(15, 8))
        self.label(foot, str(self.store.directory), 10, CYAN, MONO, anchor="w").pack(fill="x", padx=20)
        self.label(foot, "Workspaces and news cache are local JSON files. Notes are stored as plain text inside the workspace file.\n"
                         "The command library is a reference: the hub does not launch the copied commands.",
                   10, MUTED, justify="left", anchor="w").pack(fill="x", padx=20, pady=(9, 16))
        self.render_source_settings()

    def settings_changed(self):
        was_online = self.store.state["settings"]["online_news"]
        self.store.state["settings"].update(
            reduced_motion=self.reduced_motion.get(), online_news=self.online_news.get(),
            auto_refresh=self.automatic_news.get())
        self.save_now()
        self.refresh_dashboard()
        self.status("Preferences saved. Feed requests already in progress may finish.")
        if self.online_news.get() and not was_online and self.news.should_refresh():
            self.refresh_news()

    def change_accent(self, event=None):
        name = self.accent_choice.get()
        if name not in ACCENTS:
            return
        old, self.accent = self.accent, ACCENTS[name]
        legacy.GREEN = self.accent
        self.store.state["settings"]["accent"] = name
        def recolor(widget):
            options = widget.configure()
            for option in ("fg", "foreground", "bg", "background", "activeforeground", "activebackground",
                           "insertbackground", "selectforeground", "highlightcolor", "highlightbackground"):
                if option in options:
                    try:
                        if str(widget.cget(option)).lower() == old.lower():
                            widget.configure(**{option: self.accent})
                    except tk.TclError:
                        pass
            if isinstance(widget, tk.Text):
                widget.tag_configure("heading", foreground=self.accent)
            for child in widget.winfo_children():
                recolor(child)
        recolor(self)
        self.style.configure("TCombobox", arrowcolor=self.accent)
        self.style.map("Neon.Treeview", background=[("selected", "#263D31")], foreground=[("selected", self.accent)])
        self.style.map("Vertical.TScrollbar", arrowcolor=[("active", self.accent), ("!active", MUTED)])
        self.draw_radar()
        self.save_now()
        self.status("Accent color updated.")

    def render_source_settings(self):
        lines = []
        for source in SOURCES:
            result = self.news.sources.get(source["id"], {})
            lines.append(source["name"] + "\n" + source["url"] + "\n"
                         + "Last success: " + result.get("fetched", "Never fetched")
                         + "\n" + ("Last error: " + result["error"] if result.get("error") else "Status: available" if result.get("fetched") else "Status: waiting for first refresh"))
        self.text_set(self.settings_sources, "\n\n".join(lines))

    def open_palette(self, event=None):
        if not self._ready:
            return "break"
        if self.palette_window and self.palette_window.winfo_exists():
            self.palette_window.lift()
            return "break"
        from hub_ui import PAGES
        window = tk.Toplevel(self)
        self.palette_window = window
        window.title("NEON//HUB — Command palette")
        window.configure(bg=PANEL)
        window.transient(self)
        width, height = self.px(740), self.px(480)
        window.geometry(f"{width}x{height}+{self.winfo_rootx() + (self.winfo_width() - width) // 2}+{self.winfo_rooty() + self.px(100)}")
        window.minsize(self.px(500), self.px(350))
        self.label(window, "GO ANYWHERE. FIND ANY TOOL.", 11, self.accent, MONO).pack(anchor="w", padx=20, pady=(18, 12))
        query = tk.StringVar()
        field = self.entry(window, query, 14)
        field.pack(fill="x", padx=20, ipady=12)
        choices = tk.Listbox(window, bg=INPUT, fg=TEXT, font=(MONO, 12), relief="flat",
                             bd=0, selectbackground="#29402E", selectforeground=self.accent,
                             activestyle="none", highlightthickness=0, exportselection=False)
        choices.pack(fill="both", expand=True, padx=20, pady=15)
        self.label(window, "Enter: open   /   Arrow keys: select   /   Esc: close", 9, MUTED, MONO).pack(anchor="w", padx=20, pady=(0, 15))
        actions = [(PAGES[key][0] + "  /  open page", lambda key=key: self.show_page(key)) for key in PAGES]
        actions.append(("Refresh news feeds", self.refresh_news))
        actions.extend((entry["tool"] + " / " + entry["title"], lambda key=entry["id"]: self.open_recipe(key)) for entry in RECIPES)
        actions.extend(("Function / " + name, lambda name=name: self.palette_function(name)) for name in FUNCTIONS)
        filtered = []
        def refresh(*args):
            terms = query.get().lower().split()
            filtered[:] = [(label, action) for label, action in actions if all(term in label.lower() for term in terms)][:40]
            choices.delete(0, "end")
            for label, action in filtered:
                choices.insert("end", label)
            if filtered:
                choices.selection_set(0)
        def close(event=None):
            self.palette_window = None
            window.destroy()
            return "break"
        def execute(event=None):
            selected = choices.curselection()
            if selected and selected[0] < len(filtered):
                action = filtered[selected[0]][1]
                close()
                action()
            return "break"
        def move(event, direction):
            if filtered:
                selected = choices.curselection()
                index = max(0, min(len(filtered) - 1, (selected[0] if selected else 0) + direction))
                choices.selection_clear(0, "end")
                choices.selection_set(index)
                choices.see(index)
            return "break"
        query.trace_add("write", refresh)
        window.bind("<Escape>", close)
        window.bind("<Return>", execute)
        field.bind("<Down>", lambda event: move(event, 1))
        field.bind("<Up>", lambda event: move(event, -1))
        choices.bind("<Double-Button-1>", execute)
        window.protocol("WM_DELETE_WINDOW", close)
        refresh()
        window.grab_set()
        field.focus_set()
        return "break"

    def palette_function(self, name):
        self.show_page("calculator")
        self.insert(name + "(")

