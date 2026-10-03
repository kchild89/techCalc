"""NEON//HUB desktop shell and calculator integration."""
import math
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import calculator_ui as legacy
from calculator_ui import BG, SIDE, PANEL, INPUT, BORDER, TEXT, MUTED, CYAN, RED, AMBER, MONO, UI
from calculator_core import CalculationError, FUNCTIONS, format_number
from hub_core import ACCENTS, FUNCTION_HINTS, WorkspaceStore, evaluate_statement
from intel import NewsCache, SOURCES
from tool_library import RECIPES, TOOLS
from widgets import SmartExpression, Tooltip
from labs_ui import LabsMixin
from intel_ui import IntelligenceMixin
from workspace_ui import WorkspaceMixin

PAGES = {
    "dashboard": ("Command center", "Your security workspace, connected.", "Current intelligence, practical references, and a lab for the details."),
    "intel": ("Threat intelligence", "Stay ahead of the next headline.", "News, zero-day reporting, and CISA known-exploited vulnerabilities. Every item links to its source."),
    "library": ("Tool library", "Know the tool. Understand the command.", "Search practical recipes, inspect every flag, and keep your most useful commands close."),
    "workspace": ("My workspace", "Keep your investigation together.", "Notes, saved calculations, named variables, bookmarks, and a software watchlist."),
    "calculator": ("Calculator", "Compute something brilliant.", "Scientific expressions, variables, syntax hints, and persistent history."),
    "bits": ("Bit inspector", "Every bit tells a story.", "Inspect machine words, toggle bits, and switch between signed and unsigned values."),
    "float": ("IEEE-754 inspector", "See what the machine actually stores.", "Decode the sign, exponent, and fraction of binary32 and binary64 values."),
    "graph": ("Graphing", "Put your expressions in perspective.", "Compare functions, explore their domains, and export the sampled values."),
    "complexity": ("Algorithm playground", "How fast does the work grow?", "Compare operation-count models and explore the effect of input size."),
    "units": ("Data units", "Get your bytes right.", "Convert decimal storage, binary memory units, bytes, and bits."),
    "codec": ("Codec lab", "Speak another encoding.", "Transform UTF-8 text, inspect bytes, and generate checksums."),
    "network": ("Subnet lab", "Know your neighborhood.", "Inspect IPv4 and IPv6 CIDR ranges without sending network probes."),
    "settings": ("Settings", "Make the station yours.", "Accent colors, motion preferences, news connectivity, and local storage."),
}


class CyberHub(IntelligenceMixin, WorkspaceMixin, LabsMixin, legacy.NeonCalculator):
    def __init__(self, data_dir=None, start_network=True):
        self.store = WorkspaceStore(data_dir)
        self.variables = self.store.workspace["variables"]
        self.accent = ACCENTS[self.store.state["settings"]["accent"]]
        legacy.GREEN = self.accent
        self.news = NewsCache(self.store.directory)
        self.news_queue = queue.Queue()
        self.news_busy = False
        self.news_stop = threading.Event()
        self.news_pending = 0
        self.last_refresh_attempt = 0
        self._ready = False
        self.save_job = None
        self.radar_angle = 0
        self.error_position = None
        self.palette_window = None
        super().__init__()
        self.title("NEON//HUB  |  Cybersecurity command station")
        self.build_dashboard()
        self.build_intelligence()
        self.build_library()
        self.build_workspace()
        self.build_float_lab()
        self.build_graph_lab()
        self.build_complexity_lab()
        self.build_settings()
        self._ready = True
        self.load_workspace()
        self.bind("<Control-k>", self.open_palette)
        self.bind("<Control-K>", self.open_palette)
        self.bind("<Control-s>", lambda event: self.save_now())
        self.bind("<Control-S>", lambda event: self.save_now())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.report_callback_exception = self.callback_error
        self.status_label.bind("<Button-1>", lambda event: self.jump_to_error())
        self.show_page("dashboard")
        self.refresh_dashboard()
        self.after(200, self.poll_news)
        self.after(120, self.animate_radar)
        self.after(60000, self.auto_refresh_tick)
        if start_network and self.store.state["settings"]["online_news"] and self.news.should_refresh():
            self.after(500, self.refresh_news)
        if self.store.warning or self.news.warning:
            self.status(self.store.warning or self.news.warning, True)
        try:
            from assets_icon import icon_photo
            self.app_icon = icon_photo(self)
            self.iconphoto(True, self.app_icon)
        except (ImportError, tk.TclError):
            pass

    def button(self, parent, text, command, kind="normal", **kwargs):
        button = super().button(parent, text, command, kind, **kwargs)
        if kind == "accent":
            button.bind("<Enter>", lambda event: button.configure(bg=self.accent))
            button.bind("<Leave>", lambda event: button.configure(bg=self.accent))
        hint = FUNCTION_HINTS.get(text)
        if hint:
            Tooltip(button, hint)
        return button

    def _build_shell(self):
        self.style = ttk.Style(self)
        self.style.configure("Neon.Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                             borderwidth=0, rowheight=self.px(31), font=(UI, 10))
        self.style.configure("Neon.Treeview.Heading", background=INPUT, foreground=MUTED,
                             font=(MONO, 9), relief="flat", padding=7)
        self.style.map("Neon.Treeview", background=[("selected", "#263D31")], foreground=[("selected", self.accent)])
        self.style.map("Neon.Treeview.Heading", background=[("active", "#20343F")])
        sidebar = tk.Frame(self, bg=SIDE, width=self.px(225))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = tk.Frame(sidebar, bg=SIDE)
        brand.pack(fill="x", padx=23, pady=(22, 15))
        self.label(brand, "[N]  NEON//HUB", 17, self.accent, MONO, anchor="w").pack(fill="x")
        self.label(brand, "CYBERSECURITY COMMAND STATION", 8, MUTED, MONO, anchor="w").pack(fill="x", pady=(6, 0))
        footer = tk.Frame(sidebar, bg=SIDE)
        footer.pack(side="bottom", fill="x", padx=23, pady=18)
        self.connection_label = self.label(footer, "PUBLIC INTEL + LOCAL TOOLS", 8, self.accent, MONO, anchor="w")
        self.connection_label.pack(fill="x")
        self.label(footer, "CTRL+K  command palette\nCTRL+S  save workspace\nCTRL+L  calculator", 9, MUTED, MONO,
                   justify="left", anchor="w").pack(fill="x", pady=(9, 0))
        nav_host = tk.Frame(sidebar, bg=SIDE)
        nav_host.pack(fill="both", expand=True)
        nav_canvas = tk.Canvas(nav_host, bg=SIDE, highlightthickness=0)
        nav_canvas.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(nav_host, orient="vertical", command=nav_canvas.yview)
        scroll.pack(side="right", fill="y")
        nav_canvas.configure(yscrollcommand=scroll.set)
        navigation = tk.Frame(nav_canvas, bg=SIDE)
        window = nav_canvas.create_window((0, 0), window=navigation, anchor="nw")
        navigation.bind("<Configure>", lambda event: nav_canvas.configure(scrollregion=nav_canvas.bbox("all")))
        nav_canvas.bind("<Configure>", lambda event: nav_canvas.itemconfigure(window, width=event.width))
        for index, (key, (title, _, _)) in enumerate(PAGES.items()):
            if key in ("dashboard", "calculator", "settings"):
                group = {"dashboard": "COMMAND", "calculator": "LABORATORY", "settings": "PERSONALIZE"}[key]
                self.label(navigation, group, 8, MUTED, MONO, anchor="w").pack(fill="x", padx=23, pady=(12, 7))
            button = tk.Button(navigation, text=f"{index + 1:02d}  {title}", command=lambda key=key: self.show_page(key),
                               bg=SIDE, fg=MUTED, activebackground=PANEL, activeforeground=self.accent,
                               anchor="w", relief="flat", bd=0, padx=13, pady=8, font=(MONO, 10),
                               cursor="hand2", highlightthickness=1, highlightbackground=SIDE,
                               highlightcolor=self.accent)
            button.pack(fill="x", padx=10, pady=2)
            button.bind("<MouseWheel>", lambda event: nav_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"))
            self.nav_buttons[key] = button
        workspace = tk.Frame(self, bg=BG)
        workspace.pack(side="left", fill="both", expand=True, padx=24)
        top = tk.Frame(workspace, bg=BG)
        top.pack(fill="x", pady=(17, 12))
        self.button(top, "SEARCH  /  CTRL+K", self.open_palette, "subtle").pack(side="left")
        self.workspace_choice = tk.StringVar(value=self.store.state["active"])
        self.workspace_combo = self.combo(top, self.workspace_choice, self.store.state["workspaces"], 17)
        self.workspace_combo.pack(side="left", padx=15)
        self.workspace_combo.bind("<<ComboboxSelected>>", self.switch_workspace)
        self.clock_label = self.label(top, "", 9, MUTED, MONO)
        self.clock_label.pack(side="right")
        self.feed_badge = self.label(top, "INTEL READY", 9, self.accent, MONO)
        self.feed_badge.pack(side="right", padx=20)
        tk.Frame(workspace, bg=BORDER, height=1).pack(fill="x")
        heading = tk.Frame(workspace, bg=BG)
        heading.pack(fill="x", pady=(17, 17))
        self.page_title = self.label(heading, "", 25, TEXT, UI, anchor="w")
        self.page_title.pack(fill="x")
        self.page_subtitle = self.label(heading, "", 10, MUTED, UI, anchor="w")
        self.page_subtitle.pack(fill="x", pady=(4, 0))
        foot = tk.Frame(workspace, bg=BG)
        foot.pack(side="bottom", fill="x", pady=(12, 15))
        self.status_label = tk.Label(foot, textvariable=self.status_var, bg=BG, fg=MUTED,
                                    font=(MONO, 9), anchor="w", cursor="hand2")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.label(foot, "NEON//HUB  2.0", 9, MUTED, MONO).pack(side="right", padx=(10, 0))
        self.page_host = tk.Frame(workspace, bg=BG)
        self.page_host.pack(fill="both", expand=True)
        for key in PAGES:
            self.pages[key] = tk.Frame(self.page_host, bg=BG)

    def show_page(self, name):
        if name not in self.pages:
            return
        if hasattr(self, "expression_entry") and isinstance(self.expression_entry, SmartExpression):
            self.expression_entry.hide_suggestions()
        for key, frame in self.pages.items():
            frame.pack_forget()
            self.nav_buttons[key].configure(bg=SIDE, fg=MUTED)
        self.pages[name].pack(fill="both", expand=True)
        self.nav_buttons[name].configure(bg="#21352C", fg=self.accent)
        self.active_page = name
        _, title, subtitle = PAGES[name]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        self.status("Workspace: " + self.store.state["active"] + "  /  Ctrl+K opens the command palette.")
        if name == "calculator" and hasattr(self, "expression_entry"):
            self.expression_entry.focus_set()
        if self._ready:
            if name == "dashboard":
                self.refresh_dashboard()
            elif name == "workspace":
                self.render_workspace()

    def make_text(self, parent, height=8, editable=False, expand=True):
        frame = tk.Frame(parent, bg=INPUT, highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="both", expand=expand)
        scroll = ttk.Scrollbar(frame, orient="vertical")
        scroll.pack(side="right", fill="y")
        widget = tk.Text(frame, bg=INPUT, fg=TEXT, insertbackground=self.accent,
                         wrap="word", font=(MONO, 11), bd=0, relief="flat",
                         padx=15, pady=14, height=height, width=1, undo=editable,
                         yscrollcommand=scroll.set, selectbackground="#30482C")
        widget.pack(side="left", fill="both", expand=True)
        scroll.configure(command=widget.yview)
        widget.tag_configure("heading", foreground=self.accent, font=(MONO, 12, "bold"), spacing1=10, spacing3=6)
        widget.tag_configure("muted", foreground=MUTED)
        widget.tag_configure("command", foreground=CYAN, spacing1=8, spacing3=12)
        widget.tag_configure("warning", foreground=AMBER)
        if not editable:
            widget.configure(state="disabled")
        return widget

    def text_set(self, widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")
        widget.yview_moveto(0)

    def make_tree(self, parent, columns, widths, height=10, expand=True):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="both", expand=expand)
        tree = ttk.Treeview(frame, columns=columns, show="headings", style="Neon.Treeview",
                            selectmode="browse", height=height)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(fill="both", expand=True)
        for index, (column, width) in enumerate(zip(columns, widths)):
            tree.heading(column, text=column)
            tree.column(column, width=self.px(width), minwidth=self.px(45),
                        stretch=index == len(columns) - 1, anchor="w")
        return tree

    def _build_calculator(self):
        super()._build_calculator()
        original = self.expression_entry
        parent = original.master
        position = parent.pack_slaves().index(original)
        following = parent.pack_slaves()[position + 1]
        original.destroy()
        self.expression_entry = SmartExpression(parent, self.expression, self)
        self.expression_entry.pack(fill="x", padx=15, pady=(13, 7), before=following)
        left = self.pages["calculator"].grid_slaves(row=0, column=0)[0]
        self.editor_hint = tk.StringVar(value="Tab: autocomplete   |   name = value: save a variable   |   Ctrl+K: commands")
        help_labels = left.grid_slaves(row=5, column=0)
        if help_labels:
            help_labels[0].configure(textvariable=self.editor_hint, font=(MONO, 8), cursor="hand2")
            help_labels[0].bind("<Button-1>", lambda event: self.jump_to_error())
        history_panel = self.history_list.master
        header = history_panel.pack_slaves()[0]
        self.button(header, "PIN", self.pin_calculation, "subtle", padx=7).pack(side="right", padx=(0, 5))
        Tooltip(self.expression_entry, "Tab completes function or variable names. Matching parentheses are highlighted. Use ** for powers and ^ for XOR.")

    def _expression_changed(self, *args):
        super()._expression_changed(*args)
        if self._ready:
            self.schedule_save()

    def calculate(self):
        source = self.expression.get()
        try:
            value, name = evaluate_statement(source, self.ans, self.variables)
        except CalculationError as exc:
            self.error_position = exc.position
            self.result_hint.configure(text="CHECK INPUT  /  CLICK STATUS TO JUMP", fg=RED)
            self.status(str(exc), True)
            if exc.position is not None:
                self.expression_entry.show_error(exc.position)
            return
        if name:
            self.variables[name] = value
        self.error_position = None
        self.ans = value
        self.last_result = format_number(value)
        self.result.set(self.last_result)
        kind = f"INTEGER / {abs(value).bit_length()} BITS" if type(value) is int else "REAL / FLOAT64"
        self.result_hint.configure(text=("SAVED " + name if name else "= " + kind), fg=self.accent)
        self.history.insert(0, (source, self.last_result))
        self.history = self.history[:100]
        self.render_history()
        self.schedule_save()
        self.status(f"Saved variable {name} = {self.last_result}" if name else "Calculated. Pin useful results or reuse them with ans.")

    def render_history(self):
        self.history_list.delete(0, "end")
        for expression, result in self.history:
            self.history_list.insert("end", expression, "  = " + result, "")
        if not self.history:
            self.history_list.insert("end", "Your calculations land here.")

    def clear_history(self):
        super().clear_history()
        self.schedule_save()

    def jump_to_error(self):
        if self.error_position is not None:
            self.show_page("calculator")
            self.expression_entry.show_error(self.error_position)

    def pin_calculation(self):
        if not self.history:
            self.status("Calculate an expression first.", True)
            return
        expression, result = self.history[0]
        pins = self.store.workspace["pins"]
        if any(item["expression"] == expression and item["result"] == result for item in pins):
            self.status("That calculation is already pinned.")
            return
        if len(pins) >= 100:
            self.status("Remove a pin before adding another (100 maximum).", True)
            return
        pins.insert(0, {"expression": expression, "result": result})
        if self.save_now():
            self.status("Calculation pinned to this workspace.")

    def _enter(self, event):
        if event.widget.winfo_toplevel() is not self:
            return
        if self.active_page == "float":
            self.inspect_float()
            return "break"
        if self.active_page == "graph":
            self.plot_graph()
            return "break"
        if self.active_page == "complexity":
            self.draw_complexity()
            return "break"
        return super()._enter(event)

    def callback_error(self, kind, value, trace):
        import traceback
        try:
            self.store.directory.mkdir(parents=True, exist_ok=True)
            with (self.store.directory / "error.log").open("a", encoding="utf-8") as handle:
                traceback.print_exception(kind, value, trace, file=handle)
        except OSError:
            pass
        self.status("Something went wrong: " + str(value), True)

    def close(self):
        try:
            self.save_now(raise_error=True)
        except OSError as exc:
            messagebox.showerror("Workspace could not be saved", str(exc), parent=self)
            return
        self.news_stop.set()
        if self.palette_window:
            self.palette_window.destroy()
        self.expression_entry.hide_suggestions()
        for job in self.tk.call("after", "info"):
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        super().destroy()

    def build_dashboard(self):
        page = self.pages["dashboard"]
        hero = self.panel(page)
        hero.pack(fill="x", pady=(0, 14))
        left = tk.Frame(hero, bg=PANEL)
        left.pack(side="left", fill="both", expand=True, padx=22, pady=18)
        self.label(left, "SITUATIONAL AWARENESS / PERSONAL WORKSPACE", 9, self.accent, MONO).pack(anchor="w")
        self.label(left, "One station. A clearer picture.", 21, TEXT).pack(anchor="w", pady=(10, 6))
        self.label(left, "Follow the signals. Learn the tools. Keep the evidence organized.", 10, MUTED).pack(anchor="w")
        actions = tk.Frame(left, bg=PANEL)
        actions.pack(fill="x", pady=(15, 0))
        self.button(actions, "OPEN INTELLIGENCE", lambda: self.show_page("intel"), "accent").pack(side="left")
        self.button(actions, "REFRESH FEEDS", self.refresh_news, "subtle").pack(side="left", padx=10)
        self.radar = tk.Canvas(hero, bg=PANEL, width=self.px(155), height=self.px(155), bd=0, highlightthickness=0)
        self.radar.pack(side="right", padx=22, pady=10)
        self.radar.bind("<Configure>", lambda event: self.draw_radar())
        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="x", pady=(0, 14))
        self.dashboard_metrics = {}
        for column, (key, title) in enumerate((
                ("feeds", "FRESH SOURCES"), ("kev", "CACHED KEV ENTRIES"),
                ("zero", "ZERO-DAY REPORTS"), ("favorites", "SAVED COMMANDS"))):
            cards.columnconfigure(column, weight=1, uniform="metrics")
            card = self.panel(cards)
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))
            self.label(card, title, 8, MUTED, MONO).pack(anchor="w", padx=15, pady=(12, 4))
            value = self.label(card, "—", 23, self.accent, MONO)
            value.pack(anchor="w", padx=15, pady=(0, 12))
            self.dashboard_metrics[key] = value
        lower = tk.Frame(page, bg=BG)
        lower.pack(fill="both", expand=True)
        lower.columnconfigure(0, weight=3)
        lower.columnconfigure(1, weight=1, minsize=self.px(240))
        lower.rowconfigure(0, weight=1)
        stories = tk.Frame(lower, bg=BG)
        stories.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        self.label(stories, "LATEST CACHED HEADLINES", 10, self.accent, MONO).pack(anchor="w", pady=(0, 10))
        self.dashboard_news = self.make_tree(stories, ("DATE", "SOURCE", "HEADLINE"), (85, 125, 400))
        self.dashboard_news.bind("<Double-Button-1>", self.open_dashboard_story)
        self.dashboard_news.bind("<Return>", self.open_dashboard_story)
        right = tk.Frame(lower, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        self.label(right, "SOURCE HEALTH", 10, self.accent, MONO).pack(anchor="w", pady=(0, 10))
        self.dashboard_sources = self.make_text(right, height=10)
        quick = tk.Frame(right, bg=BG)
        quick.pack(fill="x", pady=(12, 0))
        self.button(quick, "NMAP RECIPES", lambda: self.open_tool("Nmap"), "cyan").pack(fill="x", pady=(0, 7))
        self.button(quick, "WORKSPACE NOTES", lambda: self.show_page("workspace"), "subtle").pack(fill="x")
        self.draw_radar()

    def draw_radar(self):
        if not hasattr(self, "radar"):
            return
        canvas = self.radar
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        center_x, center_y = width / 2, height / 2
        radius = min(width, height) * 0.42
        for factor in (0.35, 0.65, 1):
            distance = radius * factor
            canvas.create_oval(center_x - distance, center_y - distance, center_x + distance, center_y + distance,
                               outline="#2A433B")
        canvas.create_line(center_x - radius, center_y, center_x + radius, center_y, fill="#233B33")
        canvas.create_line(center_x, center_y - radius, center_x, center_y + radius, fill="#233B33")
        angle = math.radians(self.radar_angle)
        canvas.create_line(center_x, center_y, center_x + radius * math.cos(angle),
                           center_y + radius * math.sin(angle), fill=self.accent, width=2)
        canvas.create_oval(center_x - 4, center_y - 4, center_x + 4, center_y + 4,
                           fill=self.accent, outline="")
        canvas.create_text(center_x, height - 5, text="INTEL / RSS + KEV", fill=MUTED, font=(MONO, 8), anchor="s")

    def animate_radar(self):
        if self.active_page == "dashboard" and not self.store.state["settings"]["reduced_motion"]:
            self.radar_angle = (self.radar_angle + 3) % 360
            self.draw_radar()
        self.after(120, self.animate_radar)

    def refresh_dashboard(self):
        if not hasattr(self, "dashboard_metrics"):
            return
        from datetime import datetime
        items = self.news.items
        fresh = 0
        for source in SOURCES:
            record = self.news.sources.get(source["id"], {})
            try:
                age = time.time() - datetime.fromisoformat(record.get("fetched", "")).timestamp()
                if age <= 1800 and not record.get("error"):
                    fresh += 1
            except (ValueError, TypeError):
                pass
        values = {"feeds": f"{fresh}/{len(SOURCES)}", "kev": f'{sum(item.get("kind") == "kev" for item in items):,}',
                  "zero": str(sum(bool(item.get("zero_day")) for item in items)),
                  "favorites": str(len(self.store.workspace["favorites"]))}
        for key, value in values.items():
            self.dashboard_metrics[key].configure(text=value)
        self.dashboard_news.delete(*self.dashboard_news.get_children())
        stories = [item for item in items if item.get("kind") == "news"][:16]
        for item in stories:
            self.dashboard_news.insert("", "end", iid=item["id"], values=(
                item.get("published", "")[:10] or "Undated", item["source"], item["title"]))
        if not stories:
            self.dashboard_news.insert("", "end", iid="empty", values=("", "", "Refresh feeds to load current headlines."))
        lines = []
        for source in SOURCES:
            result = self.news.sources.get(source["id"], {})
            timestamp = result.get("fetched", "")
            state = "Cached / retry needed" if result.get("error") and timestamp else "Unavailable" if result.get("error") else "Fetched" if timestamp else "Not fetched"
            lines.append(source["name"] + "\n" + state + "\n" + (timestamp[:16].replace("T", " ") + " UTC" if timestamp else "No successful fetch yet"))
        lines.append("Zero-day reports are tagged from publisher headlines.\nKEV means known exploitation; it does not imply a zero-day.")
        self.text_set(self.dashboard_sources, "\n\n".join(lines))
        online = self.store.state["settings"]["online_news"]
        self.feed_badge.configure(text="REFRESHING..." if self.news_busy else f"FEEDS {fresh}/{len(SOURCES)}" if online else "OFFLINE MODE",
                                  fg=self.accent if online else AMBER)

    def open_dashboard_story(self, event=None):
        selected = self.dashboard_news.selection()
        if selected and selected[0] != "empty":
            self.show_page("intel")
            self.intel_query.set("")
            self.intel_category.set("All intelligence")
            self.intel_source.set("All sources")
            self.render_intelligence()
            if self.intel_tree.exists(selected[0]):
                self.intel_tree.selection_set(selected[0])
                self.intel_tree.see(selected[0])
                self.select_intelligence()
        return "break"

