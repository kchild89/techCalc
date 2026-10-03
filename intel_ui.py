"""Security intelligence and command-reference views."""
from datetime import datetime
import queue
import threading
import time
import tkinter as tk
import webbrowser

from calculator_ui import BG, PANEL, INPUT, TEXT, MUTED, CYAN, AMBER, RED, MONO
from intel import SOURCES, filter_items, safe_url
from tool_library import TOOLS, RECIPES, RECIPE_BY_ID, build_command, search_recipes


class IntelligenceMixin:
    def build_intelligence(self):
        page = self.pages["intel"]
        controls = self.panel(page)
        controls.pack(fill="x", pady=(0, 12))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=15, pady=14)
        self.intel_query = tk.StringVar()
        self.entry(row, self.intel_query, 11).pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 10))
        self.intel_category = tk.StringVar(value="All intelligence")
        self.combo(row, self.intel_category, (
            "All intelligence", "News & research", "Zero-day reports", "Known exploited (CISA)", "Watchlist", "Bookmarked"), 23).pack(side="left", padx=(0, 10))
        self.intel_source = tk.StringVar(value="All sources")
        self.combo(row, self.intel_source, ["All sources"] + [source["name"] for source in SOURCES], 18).pack(side="left")
        self.news_refresh_button = self.button(row, "REFRESH", self.refresh_news, "accent")
        self.news_refresh_button.pack(side="left", padx=(10, 0))
        self.intel_count = tk.StringVar(value="Search title, CVE, vendor, or product.")
        tk.Label(page, textvariable=self.intel_count, bg=BG, fg=MUTED, font=(MONO, 9),
                 anchor="w").pack(fill="x", pady=(0, 10))
        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3, uniform="intel_body")
        body.columnconfigure(1, weight=2, uniform="intel_body")
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 13))
        self.intel_tree = self.make_tree(left, ("DATE", "SOURCE", "TYPE", "HEADLINE"), (80, 100, 70, 290))
        self.intel_tree.tag_configure("zero", foreground=AMBER)
        self.intel_tree.tag_configure("kev", foreground=CYAN)
        self.intel_tree.bind("<<TreeviewSelect>>", self.select_intelligence)
        self.intel_tree.bind("<Double-Button-1>", lambda event: self.open_news_article())
        self.intel_tree.bind("<Return>", lambda event: self.open_news_article())
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        self.intel_detail = self.make_text(right, height=15)
        actions = tk.Frame(right, bg=BG)
        actions.pack(fill="x", pady=(12, 0))
        self.article_button = self.button(actions, "OPEN SOURCE", self.open_news_article, "accent")
        self.article_button.pack(side="left")
        self.bookmark_button = self.button(actions, "BOOKMARK", self.bookmark_article, "subtle")
        self.bookmark_button.pack(side="left", padx=8)
        self.cve_button = self.button(actions, "CVE / NVD", self.open_cve, "cyan")
        self.cve_button.pack(side="left")
        self.source_status = tk.StringVar(value="")
        tk.Label(page, textvariable=self.source_status, bg=BG, fg=MUTED, font=(MONO, 8), anchor="w",
                 justify="left").pack(fill="x", pady=(12, 5))
        self.label(page, "Zero-day tag = publisher headline wording. KEV = known exploitation, not necessarily a zero-day.\n"
                         "CISA dates are catalog additions; agency remediation due dates are not universal deadlines.",
                   9, MUTED, justify="left", anchor="w").pack(fill="x")
        self.selected_article = None
        self.intel_visible = {}
        for variable in (self.intel_query, self.intel_category, self.intel_source):
            variable.trace_add("write", lambda *args: self.render_intelligence())
        self.render_intelligence()

    def all_intelligence(self):
        items = {item["id"]: item for item in self.news.items}
        for key, value in self.store.workspace["bookmarks"].items():
            items.setdefault(key, value)
        return sorted(items.values(), key=lambda item: item.get("published", ""), reverse=True)

    def render_intelligence(self):
        if not hasattr(self, "intel_tree"):
            return
        old_selection = self.intel_tree.selection()
        matches = filter_items(self.all_intelligence(), self.intel_query.get(), self.intel_category.get(),
                               self.intel_source.get(), self.store.workspace["watchlist"],
                               self.store.workspace["bookmarks"])
        self.intel_visible = {item["id"]: item for item in matches[:500]}
        self.intel_tree.delete(*self.intel_tree.get_children())
        for item in self.intel_visible.values():
            category = "KEV" if item.get("kind") == "kev" else "Zero-day" if item.get("zero_day") else "News"
            tag = "kev" if category == "KEV" else "zero" if category == "Zero-day" else ""
            self.intel_tree.insert("", "end", iid=item["id"], values=(
                item.get("published", "")[:10] or "Undated", item.get("source", ""), category, item["title"]), tags=(tag,))
        self.intel_count.set(f"Showing {len(self.intel_visible):,} of {len(matches):,} matches  /  Search title, CVE, vendor, or product"
                             + ("  /  Refine your search for older records" if len(matches) > 500 else ""))
        if old_selection and old_selection[0] in self.intel_visible:
            self.intel_tree.selection_set(old_selection[0])
        elif self.intel_visible:
            self.intel_tree.selection_set(next(iter(self.intel_visible)))
        self.select_intelligence()
        states = []
        for source in SOURCES:
            record = self.news.sources.get(source["id"], {})
            label = "ERROR / cached" if record.get("error") and record.get("items") else "ERROR" if record.get("error") else "FETCHED" if record.get("fetched") else "NOT FETCHED"
            stamp = record.get("fetched", "")[:16].replace("T", " ")
            states.append(f'{source["name"]}: {label}' + (" " + stamp + " UTC" if stamp else ""))
        self.source_status.set("\n".join(("  |  ".join(states[:2]), "  |  ".join(states[2:]))))

    def select_intelligence(self, event=None):
        selected = self.intel_tree.selection()
        self.selected_article = self.intel_visible.get(selected[0]) if selected else None
        item = self.selected_article
        for button in (self.article_button, self.bookmark_button, self.cve_button):
            button.configure(state="normal" if item else "disabled")
        if not item:
            self.text_set(self.intel_detail, "NO MATCHING INTELLIGENCE\n\nRefresh the feeds, broaden your filters, or add software names to your workspace watchlist.\n\n"
                          "The original publication and fetch times are shown for each item. Cached results remain available when a source cannot be reached.")
            return
        self.cve_button.configure(state="normal" if item.get("cves") else "disabled")
        saved = item["id"] in self.store.workspace["bookmarks"]
        self.bookmark_button.configure(text="SAVED / REMOVE" if saved else "BOOKMARK")
        record = self.news.sources.get(item.get("source_id"), {})
        widget = self.intel_detail
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", item["title"] + "\n\n", "heading")
        date_label = "Added to CISA KEV" if item.get("kind") == "kev" else "Published"
        widget.insert("end", f'{item.get("source", "")}\n{date_label}: {item.get("published", "") or "Date not supplied"}\n'
                      f'Last successful fetch: {record.get("fetched", "Saved bookmark / no feed cache")}\n\n', "muted")
        if record.get("error"):
            widget.insert("end", "SOURCE UNAVAILABLE / CACHED COPY\n" + str(record["error"]) + "\n\n", "warning")
        if item.get("zero_day"):
            widget.insert("end", "ZERO-DAY COVERAGE\nTagged from the publisher's headline; consult the source for exploitation and patch details.\n\n", "warning")
        widget.insert("end", item.get("summary", "") + "\n\n")
        if item.get("kind") == "kev":
            widget.insert("end", "KNOWN EXPLOITATION / CISA\n", "heading")
            widget.insert("end", f'Vendor: {item.get("vendor", "")}\nProduct: {item.get("product", "")}\n'
                          f'Known ransomware campaign use: {item.get("ransomware", "Unknown")}\n'
                          f'CISA agency due date: {item.get("due", "")}\n\n')
            widget.insert("end", "REQUIRED ACTION IN CISA CATALOG\n", "heading")
            widget.insert("end", item.get("action", "") + "\n\n")
            if item.get("references"):
                widget.insert("end", "VENDOR / ADVISORY REFERENCES\n", "heading")
                for url in item["references"]:
                    widget.insert("end", url + "\n", "command")
        if item.get("cves"):
            widget.insert("end", "\nCVE REFERENCES\n", "heading")
            widget.insert("end", "\n".join(item["cves"]) + "\n")
        widget.insert("end", "\nORIGINAL SOURCE\n" + item.get("url", ""), "muted")
        widget.configure(state="disabled")
        widget.yview_moveto(0)

    def open_url(self, url):
        url = safe_url(url)
        if not url:
            self.status("That source does not have a valid web address.", True)
            return
        webbrowser.open(url)
        self.status("Opened the source in your browser.")

    def open_news_article(self):
        if self.selected_article:
            self.open_url(self.selected_article.get("url", ""))
        return "break"

    def open_cve(self):
        if self.selected_article and self.selected_article.get("cves"):
            self.open_url("https://nvd.nist.gov/vuln/detail/" + self.selected_article["cves"][0])

    def bookmark_article(self):
        if not self.selected_article:
            return
        bookmarks = self.store.workspace["bookmarks"]
        key = self.selected_article["id"]
        if key in bookmarks:
            bookmarks.pop(key)
        elif len(bookmarks) < 200:
            bookmarks[key] = dict(self.selected_article)
        else:
            self.status("A workspace supports up to 200 article bookmarks.", True)
            return
        self.save_now()
        self.render_intelligence()
        self.status("Article bookmarks updated.")

    def refresh_news(self):
        if not self.store.state["settings"]["online_news"]:
            self.status("Offline mode is enabled. Turn on news connectivity in Settings to refresh.")
            return
        if self.news_busy:
            self.status("The feeds are already refreshing.")
            return
        if time.monotonic() - self.last_refresh_attempt < 30:
            self.status("Please allow 30 seconds between feed refreshes.")
            return
        self.news_busy = True
        self.news_pending = len(SOURCES)
        self.last_refresh_attempt = time.monotonic()
        if hasattr(self, "news_refresh_button"):
            self.news_refresh_button.configure(state="disabled", text="FETCHING")
        self.feed_badge.configure(text="REFRESHING...")
        self.status("Fetching public RSS and CISA intelligence in the background...")
        def worker():
            try:
                self.news.refresh(lambda key, value: self.news_queue.put((key, value)), self.news_stop)
            finally:
                self.news_queue.put(("done", {}))
        threading.Thread(target=worker, name="neon-news", daemon=True).start()

    def poll_news(self):
        if self.news_stop.is_set():
            return
        changed = False
        while True:
            try:
                source_id, result = self.news_queue.get_nowait()
            except queue.Empty:
                break
            if source_id == "done":
                self.news_busy = False
                self.news_refresh_button.configure(state="normal", text="REFRESH")
                try:
                    self.news.save()
                    failures = sum(bool(record.get("error")) for record in self.news.sources.values())
                    self.status(f"Refresh finished. {failures} source(s) unavailable; successful data and cached results remain visible."
                                if failures else "All four intelligence sources refreshed successfully.")
                except OSError as exc:
                    self.status("Feeds loaded, but the local cache could not be saved: " + str(exc), True)
            else:
                self.news.accept(source_id, result)
                self.news_pending -= 1
            changed = True
        if changed:
            self.render_intelligence()
            self.refresh_dashboard()
            if hasattr(self, "settings_sources"):
                self.render_source_settings()
        self.after(200, self.poll_news)

    def auto_refresh_tick(self):
        settings = self.store.state["settings"]
        if (settings["online_news"] and settings["auto_refresh"] and not self.news_busy
                and time.monotonic() - self.last_refresh_attempt >= 1800 and self.news.should_refresh()):
            self.refresh_news()
        self.after(60000, self.auto_refresh_tick)

    def build_library(self):
        page = self.pages["library"]
        toolbar = self.panel(page)
        toolbar.pack(fill="x", pady=(0, 13))
        row = tk.Frame(toolbar, bg=PANEL)
        row.pack(fill="x", padx=16, pady=14)
        self.library_query = tk.StringVar()
        self.entry(row, self.library_query, 12).pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 12))
        self.library_tool = tk.StringVar(value="All tools")
        self.combo(row, self.library_tool, ["All tools"] + list(TOOLS), 22).pack(side="left")
        self.library_favorites = tk.BooleanVar(value=False)
        tk.Checkbutton(row, text="Saved only", variable=self.library_favorites, command=self.render_library,
                       bg=PANEL, fg=TEXT, selectcolor=INPUT, activebackground=PANEL,
                       activeforeground=self.accent, font=(MONO, 10)).pack(side="left", padx=(14, 0))
        self.library_count = tk.StringVar()
        tk.Label(page, textvariable=self.library_count, bg=BG, fg=MUTED, font=(MONO, 9),
                 anchor="w").pack(fill="x", pady=(0, 10))
        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2, uniform="library")
        body.columnconfigure(1, weight=3, uniform="library")
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 13))
        self.recipe_tree = self.make_tree(left, ("TOOL", "RECIPE"), (130, 260))
        self.recipe_tree.bind("<<TreeviewSelect>>", self.select_recipe)
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        self.recipe_detail = self.make_text(right, height=10)
        params = self.panel(right)
        params.pack(fill="x", pady=(12, 0))
        fields = tk.Frame(params, bg=PANEL)
        fields.pack(fill="x", padx=13, pady=12)
        self.label(fields, "TARGET", 9, MUTED, MONO).pack(side="left", padx=(0, 7))
        self.command_host = tk.StringVar(value="127.0.0.1")
        self.entry(fields, self.command_host, 11, width=18).pack(side="left", fill="x", expand=True, ipady=7)
        self.label(fields, "PORTS", 9, MUTED, MONO).pack(side="left", padx=(12, 7))
        self.command_ports = tk.StringVar(value="22,80,443")
        self.entry(fields, self.command_ports, 11, width=12).pack(side="left", ipady=7)
        self.command_preview = self.make_text(params, height=3, expand=False)
        self.command_preview.tag_configure("command", foreground=CYAN)
        buttons = tk.Frame(right, bg=BG)
        buttons.pack(fill="x", pady=(12, 0))
        self.copy_command_button = self.button(buttons, "COPY COMMAND", self.copy_command, "accent")
        self.copy_command_button.pack(side="left")
        self.favorite_button = self.button(buttons, "SAVE", self.toggle_recipe_favorite, "subtle")
        self.favorite_button.pack(side="left", padx=8)
        self.docs_button = self.button(buttons, "OFFICIAL DOCS", self.open_recipe_docs, "cyan")
        self.docs_button.pack(side="left")
        self.label(page, "Reference commands are copied for review and use in your terminal. Use network examples on systems you own or are authorized to assess.",
                   9, MUTED, anchor="w").pack(fill="x", pady=(12, 0))
        self.selected_recipe = None
        self.generated_command = ""
        for variable in (self.library_query, self.library_tool):
            variable.trace_add("write", lambda *args: self.render_library())
        for variable in (self.command_host, self.command_ports):
            variable.trace_add("write", lambda *args: self.update_command())
        self.render_library()

    def render_library(self):
        if not hasattr(self, "recipe_tree"):
            return
        previous = self.recipe_tree.selection()
        entries = search_recipes(self.library_query.get(), self.library_tool.get(),
                                 self.store.workspace["favorites"] if self.library_favorites.get() else None)
        self.recipe_tree.delete(*self.recipe_tree.get_children())
        for entry in entries:
            self.recipe_tree.insert("", "end", iid=entry["id"], values=(entry["tool"], entry["title"]))
        self.library_count.set(f"{len(entries)} matching recipes  /  {len(TOOLS)} tools  /  Search commands, flags, purpose, or category")
        if previous and self.recipe_tree.exists(previous[0]):
            self.recipe_tree.selection_set(previous[0])
        elif entries:
            self.recipe_tree.selection_set(entries[0]["id"])
        self.select_recipe()

    def select_recipe(self, event=None):
        selected = self.recipe_tree.selection()
        self.selected_recipe = RECIPE_BY_ID.get(selected[0]) if selected else None
        entry = self.selected_recipe
        for button in (self.favorite_button, self.docs_button):
            button.configure(state="normal" if entry else "disabled")
        if not entry:
            self.text_set(self.recipe_detail, "NO MATCHING RECIPES\n\nTry a broader search or choose another tool.")
            self.update_command()
            return
        tool = TOOLS[entry["tool"]]
        widget = self.recipe_detail
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", entry["tool"] + " / " + entry["title"] + "\n", "heading")
        widget.insert("end", tool["category"] + "\n" + tool["platform"] + "\n\n", "muted")
        widget.insert("end", tool["about"] + "\n\n")
        for heading, text in (
            ("WHEN TO USE IT", entry["purpose"]),
            ("WHAT THE FLAGS DO", entry["flags"]),
            ("WHAT TO EXPECT", entry["output"]),
            ("BEFORE YOU START", tool["setup"]),
        ):
            widget.insert("end", heading + "\n", "heading")
            widget.insert("end", text + "\n\n")
        if entry["note"]:
            widget.insert("end", entry["note"] + "\n\n", "warning")
        widget.insert("end", "OFFICIAL REFERENCES\n", "heading")
        widget.insert("end", entry["docs"] + "\n\n" + tool["download"], "muted")
        widget.configure(state="disabled")
        widget.yview_moveto(0)
        self.favorite_button.configure(text="SAVED / REMOVE" if entry["id"] in self.store.workspace["favorites"] else "SAVE")
        self.update_command()

    def update_command(self):
        if not hasattr(self, "command_preview"):
            return
        try:
            self.generated_command = build_command(self.selected_recipe, self.command_host.get(), self.command_ports.get()) if self.selected_recipe else ""
            self.text_set(self.command_preview, self.generated_command or "Select a recipe.")
            self.copy_command_button.configure(state="normal" if self.generated_command else "disabled")
        except ValueError as exc:
            self.generated_command = ""
            self.text_set(self.command_preview, str(exc))
            self.copy_command_button.configure(state="disabled")

    def copy_command(self):
        if self.generated_command:
            self.copy(self.generated_command)

    def toggle_recipe_favorite(self):
        if not self.selected_recipe:
            return
        favorites = self.store.workspace["favorites"]
        key = self.selected_recipe["id"]
        if key in favorites:
            favorites.remove(key)
        else:
            favorites.append(key)
        self.save_now()
        self.render_library()
        self.refresh_dashboard()
        self.status("Saved commands updated for this workspace.")

    def open_recipe_docs(self):
        if self.selected_recipe:
            self.open_url(self.selected_recipe["docs"])

    def open_tool(self, name):
        self.show_page("library")
        self.library_favorites.set(False)
        self.library_query.set("")
        self.library_tool.set(name)
        self.render_library()

    def open_recipe(self, key):
        if key not in RECIPE_BY_ID:
            return
        self.open_tool(RECIPE_BY_ID[key]["tool"])
        self.recipe_tree.selection_set(key)
        self.recipe_tree.see(key)
        self.select_recipe()

