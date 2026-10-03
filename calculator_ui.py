"""NEON//CALC -- a local, dependency-free calculator and computer science toolkit.

Run with: python script.py
"""
import time
import tkinter as tk
from tkinter import ttk

from calculator_core import (
    CODECS, FUNCTIONS, UNITS, CalculationError, convert_data, evaluate,
    format_number, inspect_network, transform_text, word_details,
)

BG = "#080D12"
SIDE = "#0C131A"
PANEL = "#111C25"
INPUT = "#0A1219"
BORDER = "#233541"
TEXT = "#E6F0F5"
MUTED = "#8499A9"
GREEN = "#BAFF69"
CYAN = "#66D9EF"
RED = "#FF7F8F"
AMBER = "#FFD08A"
MONO = "Consolas"
UI = "Segoe UI"


class NeonCalculator(tk.Tk):
    def __init__(self):
        # Match fixed panel dimensions to Tk's font scaling on high-DPI displays.
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, AttributeError, OSError):
            pass
        super().__init__()
        self.title("NEON//CALC  |  Programmer's pocket lab")
        self.configure(bg=BG)
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        self.ui_scale = min(float(self.tk.call("tk", "scaling")) / (96 / 72),
                            (screen_width - 80) / 1100, (screen_height - 100) / 780)
        self.tk.call("tk", "scaling", (96 / 72) * self.ui_scale)
        width = min(self.px(1320), screen_width - 80)
        height = min(self.px(880), screen_height - 100)
        self.geometry(f"{width}x{height}+{(screen_width - width) // 2}+{(screen_height - height) // 2}")
        self.minsize(self.px(1100), self.px(780))
        self.option_add("*Font", (UI, 10))
        self.option_add("*insertBackground", GREEN)
        self.option_add("*selectBackground", "#30482C")
        self.option_add("*selectForeground", TEXT)
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", "#2A4535")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=INPUT, background=PANEL,
                        foreground=TEXT, arrowcolor=GREEN, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, padding=8)
        style.map("TCombobox", fieldbackground=[("readonly", INPUT)],
                  foreground=[("readonly", TEXT)], selectbackground=[("readonly", INPUT)])
        style.configure("Vertical.TScrollbar", background=BORDER, troughcolor=INPUT,
                        bordercolor=INPUT, arrowcolor=MUTED, lightcolor=BORDER,
                        darkcolor=BORDER, gripcount=0)
        style.map("Vertical.TScrollbar", background=[("active", "#354E5F"), ("!active", BORDER)],
                  arrowcolor=[("active", GREEN), ("!active", MUTED)])
        self.active_page = ""
        self.ans = 0
        self.last_result = "0"
        self.history = []
        self.status_var = tk.StringVar(value="Ready. Your next idea starts here.")
        self.pages = {}
        self.nav_buttons = {}
        self.word_width = tk.IntVar(value=16)
        self.signed = tk.BooleanVar(value=False)
        self.word_value = 0
        self._build_shell()
        self._build_calculator()
        self._build_bits()
        self._build_units()
        self._build_codec()
        self._build_network()
        self.show_page("calculator")
        self.expression_entry.selection_range(0, "end")
        self.expression_entry.icursor("end")
        self.bind("<Return>", self._enter)
        self.bind("<KP_Enter>", self._enter)
        self.bind("<Escape>", self._escape)
        self.bind("<Control-l>", self._focus_expression)
        self.bind("<Control-L>", self._focus_expression)
        for number, name in enumerate(list(self.pages)[:9], 1):
            self.bind(f"<Control-Key-{number}>", lambda event, key=name: self.show_page(key))
        self.bind("<Control-Shift-C>", lambda event: self.copy(self.last_result))
        self._tick()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def px(self, value):
        return round(value * self.ui_scale)

    def label(self, parent, text="", size=10, color=TEXT, font=UI, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=(font, size), **kwargs)

    def button(self, parent, text, command, kind="normal", **kwargs):
        palette = {
            "normal": ("#1A2A36", TEXT, "#263D4C"),
            "accent": (GREEN, "#14200D", "#D0FF99"),
            "subtle": (INPUT, MUTED, "#1A2C37"),
            "cyan": ("#12313A", CYAN, "#1A414B"),
            "danger": ("#36222B", RED, "#4B2B37"),
        }
        base, foreground, hover = palette[kind]
        button = tk.Button(parent, text=text, command=command, bg=base, fg=foreground,
                           activebackground=hover, activeforeground=foreground,
                           relief="flat", bd=0, cursor="hand2", padx=kwargs.pop("padx", 12), pady=9,
                           font=(MONO, 10), highlightthickness=1,
                           highlightbackground=base, highlightcolor=GREEN, **kwargs)
        button.bind("<Enter>", lambda event: button.configure(bg=hover))
        button.bind("<Leave>", lambda event: button.configure(bg=base))
        return button

    def entry(self, parent, variable, size=13, **kwargs):
        return tk.Entry(parent, textvariable=variable, font=(MONO, size), bg=INPUT,
                        fg=TEXT, relief="flat", bd=0, insertwidth=2,
                        highlightthickness=1, highlightbackground=BORDER,
                        highlightcolor=GREEN, selectborderwidth=0, **kwargs)

    def panel(self, parent, **kwargs):
        return tk.Frame(parent, bg=PANEL, highlightthickness=1,
                        highlightbackground=BORDER, **kwargs)

    def combo(self, parent, variable, choices, width=18):
        return ttk.Combobox(parent, textvariable=variable, values=tuple(choices),
                            state="readonly", width=width, font=(MONO, 10))

    def _build_shell(self):
        sidebar = tk.Frame(self, bg=SIDE, width=self.px(202), highlightthickness=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = tk.Frame(sidebar, bg=SIDE)
        brand.pack(fill="x", padx=22, pady=(31, 0))
        self.label(brand, ">_", 31, GREEN, MONO, anchor="w").pack(fill="x")
        self.label(brand, "NEON//CALC", 18, TEXT, MONO, anchor="w").pack(fill="x", pady=(8, 0))
        self.label(brand, "PROGRAMMER'S POCKET LAB", 8, MUTED, MONO, anchor="w").pack(fill="x", pady=(5, 0))
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=22, pady=26)
        self.label(sidebar, "WORKSPACE", 9, MUTED, MONO, anchor="w").pack(fill="x", padx=23, pady=(0, 12))
        labels = [
            ("calculator", "01   Calculator"),
            ("bits", "02   Bit inspector"),
            ("units", "03   Data units"),
            ("codec", "04   Codec lab"),
            ("network", "05   Subnet lab"),
        ]
        for key, title in labels:
            button = tk.Button(sidebar, text=title, command=lambda name=key: self.show_page(name),
                               anchor="w", bg=SIDE, fg=MUTED, activebackground=PANEL,
                               activeforeground=GREEN, relief="flat", bd=0, padx=15,
                               pady=16, font=(MONO, 11), cursor="hand2",
                               highlightthickness=1, highlightbackground=SIDE, highlightcolor=GREEN)
            button.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[key] = button
        foot = tk.Frame(sidebar, bg=SIDE)
        foot.pack(side="bottom", fill="x", padx=23, pady=24)
        self.label(foot, "[+] LOCAL SESSION", 10, GREEN, MONO, anchor="w").pack(fill="x")
        self.label(foot, "No accounts. No network.\nJust you and the numbers.", 9, MUTED,
                   justify="left", anchor="w").pack(fill="x", pady=(10, 20))
        self.label(foot, "CTRL + 1..5  switch tools\nCTRL + L     expression\nENTER        execute", 9,
                   MUTED, MONO, justify="left", anchor="w").pack(fill="x")
        workspace = tk.Frame(self, bg=BG)
        workspace.pack(side="left", fill="both", expand=True, padx=28)
        top = tk.Frame(workspace, bg=BG)
        top.pack(fill="x", pady=(26, 19))
        self.label(top, "TOOLS FOR THE CURIOUS MIND", 9, MUTED, MONO).pack(side="left")
        self.clock_label = self.label(top, "", 9, MUTED, MONO)
        self.clock_label.pack(side="right")
        self.label(top, "●  SYSTEM READY", 9, GREEN, MONO).pack(side="right", padx=24)
        tk.Frame(workspace, bg=BORDER, height=1).pack(fill="x")
        heading = tk.Frame(workspace, bg=BG)
        heading.pack(fill="x", pady=(21, 19))
        self.page_title = self.label(heading, "", 25, TEXT, UI, anchor="w")
        self.page_title.pack(fill="x")
        self.page_subtitle = self.label(heading, "", 10, MUTED, UI, anchor="w")
        self.page_subtitle.pack(fill="x", pady=(5, 0))
        footer = tk.Frame(workspace, bg=BG)
        footer.pack(side="bottom", fill="x", pady=(12, 18))
        self.status_label = tk.Label(footer, textvariable=self.status_var, bg=BG,
                                    fg=MUTED, font=(MONO, 9), anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.label(footer, "NEON OS / v1.0", 9, MUTED, MONO).pack(side="right", padx=(12, 0))
        self.page_host = tk.Frame(workspace, bg=BG)
        self.page_host.pack(fill="both", expand=True)
        for name, _ in labels:
            self.pages[name] = tk.Frame(self.page_host, bg=BG)

    def show_page(self, name):
        descriptions = {
            "calculator": ("Compute something brilliant.", "Scientific math, programmer expressions, and a little terminal energy."),
            "bits": ("Every bit tells a story.", "Inspect machine words. Flip bits. See the number underneath."),
            "units": ("Get your bytes right.", "Decimal storage meets binary memory. Convert without the guesswork."),
            "codec": ("Speak another encoding.", "Transform UTF-8 text, inspect bytes, and generate checksums."),
            "network": ("Know your neighborhood.", "A CIDR workbench for IPv4 and IPv6 networks."),
        }
        for key, frame in self.pages.items():
            frame.pack_forget()
            self.nav_buttons[key].configure(bg=SIDE, fg=MUTED)
        self.pages[name].pack(fill="both", expand=True)
        self.nav_buttons[name].configure(bg="#203326", fg=GREEN)
        self.active_page = name
        title, subtitle = descriptions[name]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        self.status("Ready. All processing stays on this computer.")
        if name == "calculator":
            self.expression_entry.focus_set()

    def status(self, text, error=False):
        self.status_var.set(text)
        self.status_label.configure(fg=RED if error else MUTED)

    def copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(str(text))
        self.status("Copied to clipboard.")

    def _tick(self):
        self.clock_label.configure(text=time.strftime("%H:%M:%S") + " / LOCAL")
        self.after(1000, self._tick)

    def _enter(self, event):
        if self.active_page == "calculator":
            self.calculate()
            return "break"
        if self.active_page == "bits":
            self.inspect_bits()
            return "break"
        if self.active_page == "network":
            self.calculate_network()
            return "break"

    def _escape(self, event):
        if self.active_page == "calculator":
            self.clear_expression()
            return "break"

    def _focus_expression(self, event=None):
        self.show_page("calculator")
        self.expression_entry.focus_set()
        self.expression_entry.selection_range(0, "end")
        return "break"

    def _build_calculator(self):
        page = self.pages["calculator"]
        page.columnconfigure(0, weight=1)
        page.columnconfigure(1, weight=0, minsize=self.px(265))
        page.rowconfigure(0, weight=1)
        left = self.panel(page)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(4, weight=1)
        heading = tk.Frame(left, bg=PANEL)
        heading.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 11))
        self.label(heading, "EXPRESSION", 9, MUTED, MONO).pack(side="left")
        self.label(heading, "RAD  /  PYTHON SYNTAX", 9, CYAN, MONO).pack(side="right")
        display = tk.Frame(left, bg=INPUT, highlightbackground=BORDER, highlightthickness=1)
        display.grid(row=1, column=0, sticky="ew", padx=18)
        self.expression = tk.StringVar(value="2 ** 10")
        self.expression_entry = self.entry(display, self.expression, 17)
        self.expression_entry.configure(highlightthickness=0)
        self.expression_entry.pack(fill="x", padx=15, pady=(17, 12), ipady=4)
        self.expression.trace_add("write", self._expression_changed)
        self.result = tk.StringVar(value="1024")
        result_entry = tk.Entry(display, textvariable=self.result, font=(MONO, 34),
                                justify="right", readonlybackground=INPUT, fg=GREEN,
                                relief="flat", bd=0, state="readonly")
        result_entry.pack(fill="x", padx=15, pady=(0, 8))
        result_bar = tk.Frame(display, bg=INPUT)
        result_bar.pack(fill="x", padx=15, pady=(0, 12))
        self.result_hint = self.label(result_bar, "= RESULT  /  11 BITS", 9, MUTED, MONO)
        self.result_hint.pack(side="left")
        self.button(result_bar, "COPY", lambda: self.copy(self.last_result), "subtle").pack(side="right")
        samples = tk.Frame(left, bg=PANEL)
        samples.grid(row=2, column=0, sticky="ew", padx=18, pady=12)
        for sample in ("2 ** 20", "0xFF & 0b1010", "log2(1024)"):
            self.button(samples, sample, lambda text=sample: self.load_expression(text), "subtle").pack(side="left", padx=(0, 7))
        function_row = tk.Frame(left, bg=PANEL)
        function_row.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 8))
        for index, name in enumerate(("sin", "cos", "tan", "log10", "gcd", "popcount")):
            function_row.columnconfigure(index, weight=1, uniform="functions")
            self.button(function_row, name, lambda name=name: self.insert(name + "("), "cyan",
                        padx=0).grid(row=0, column=index, sticky="ew", padx=3)
        keypad = tk.Frame(left, bg=PANEL)
        keypad.grid(row=4, column=0, sticky="nsew", padx=15, pady=(0, 14))
        keys = [
            [("AC", "clear"), ("DEL", "delete"), ("(", "("), (")", ")"), ("mod", "%"), ("÷", "/")],
            [("7", "7"), ("8", "8"), ("9", "9"), ("√", "sqrt("), ("xʸ", "**"), ("×", "*")],
            [("4", "4"), ("5", "5"), ("6", "6"), ("log₂", "log2("), ("floor ÷", "//"), ("−", "-")],
            [("1", "1"), ("2", "2"), ("3", "3"), ("abs", "abs("), ("ans", "ans"), ("+", "+")],
            [("0", "0"), (".", "."), ("π", "pi"), ("e", "e"), ("n!", "fact("), ("=", "execute")],
        ]
        for row, values in enumerate(keys):
            keypad.rowconfigure(row, weight=1, uniform="keys")
            for column, (label, token) in enumerate(values):
                keypad.columnconfigure(column, weight=1, uniform="keys")
                kind = "accent" if token == "execute" else "danger" if token == "clear" else "normal" if label.isdigit() or token == "." else "cyan"
                self.button(keypad, label, lambda token=token: self.keypress(token), kind,
                            padx=0).grid(row=row, column=column, sticky="nsew", padx=3, pady=3)
        self.label(left, "** power   •   ^ XOR   •   % remainder   •   trig in radians",
                   9, MUTED, MONO).grid(row=5, column=0, sticky="w", padx=20, pady=(0, 15))
        right = tk.Frame(page, bg=BG, width=self.px(265))
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_propagate(False)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        history_panel = self.panel(right)
        history_panel.grid(row=0, column=0, sticky="nsew")
        history_header = tk.Frame(history_panel, bg=PANEL)
        history_header.pack(fill="x", padx=15, pady=(14, 12))
        self.label(history_header, "SESSION HISTORY", 9, MUTED, MONO).pack(side="left")
        self.button(history_header, "CLR", self.clear_history, "subtle").pack(side="right")
        self.history_list = tk.Listbox(history_panel, bg=PANEL, fg=TEXT, font=(MONO, 11),
                                       relief="flat", bd=0, highlightthickness=0,
                                       selectbackground="#29402E", selectforeground=GREEN,
                                       activestyle="none", exportselection=False)
        self.history_list.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.history_list.bind("<Double-Button-1>", self.recall_history)
        self.history_list.bind("<Return>", self.recall_history)
        self.history_list.insert("end", "Your calculations land here.")
        self.label(history_panel, "Double-click an entry to reuse.", 9, MUTED).pack(anchor="w", padx=15, pady=(0, 14))
        note = self.panel(right)
        note.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        self.label(note, "// QUICK REFERENCE", 10, GREEN, MONO, anchor="w").pack(fill="x", padx=15, pady=(16, 10))
        self.label(note, "0b1010   binary literal\n0o755    octal literal\n0xFF     hexadecimal\n\n&  |  ^  ~    bitwise\n<<  >>        shifts\nans           last result\n\nTry: (1 << 8) - 1", 10,
                   MUTED, MONO, justify="left", anchor="w").pack(fill="x", padx=15, pady=(0, 18))
        self.last_result = "1024"
        self.ans = 1024

    def _expression_changed(self, *args):
        self.result_hint.configure(text="PRESS ENTER TO EVALUATE", fg=MUTED)

    def insert(self, token):
        entry = self.expression_entry
        if entry.selection_present():
            entry.delete("sel.first", "sel.last")
        entry.insert("insert", token)
        entry.focus_set()

    def keypress(self, token):
        if token == "clear":
            self.clear_expression()
        elif token == "delete":
            entry = self.expression_entry
            if entry.selection_present():
                entry.delete("sel.first", "sel.last")
            elif entry.index("insert") > 0:
                entry.delete(entry.index("insert") - 1)
            entry.focus_set()
        elif token == "execute":
            self.calculate()
        else:
            self.insert(token)

    def clear_expression(self):
        self.expression.set("")
        self.result.set("0")
        self.last_result = "0"
        self.result_hint.configure(text="READY FOR INPUT", fg=MUTED)
        self.expression_entry.focus_set()

    def load_expression(self, text):
        self.expression.set(text)
        self.expression_entry.icursor("end")
        self.expression_entry.focus_set()
        self.calculate()

    def calculate(self):
        source = self.expression.get()
        try:
            value = evaluate(source, self.ans)
        except CalculationError as exc:
            self.result_hint.configure(text="CHECK INPUT", fg=RED)
            self.status(str(exc), error=True)
            return
        self.ans = value
        self.last_result = format_number(value)
        self.result.set(self.last_result)
        hint = f"INTEGER / {abs(value).bit_length()} BITS" if type(value) is int else "REAL NUMBER / FLOAT64"
        self.result_hint.configure(text="= " + hint, fg=GREEN)
        self.history.insert(0, (source, self.last_result))
        self.history = self.history[:40]
        self.history_list.delete(0, "end")
        for expression, result in self.history:
            self.history_list.insert("end", expression, "  = " + result, "")
        self.status("Calculated. Use ans to refer to this result.")

    def clear_history(self):
        self.history.clear()
        self.history_list.delete(0, "end")
        self.history_list.insert("end", "Your calculations land here.")
        self.status("Session history cleared.")

    def recall_history(self, event=None):
        selected = self.history_list.curselection()
        if selected and self.history:
            index = selected[0] // 3
            if index < len(self.history):
                self.expression.set(self.history[index][0])
                self.expression_entry.focus_set()
                self.expression_entry.icursor("end")
        return "break"


    def _build_bits(self):
        page = self.pages["bits"]
        control = self.panel(page)
        control.pack(fill="x")
        self.label(control, "INTEGER EXPRESSION", 9, MUTED, MONO).pack(anchor="w", padx=18, pady=(14, 9))
        row = tk.Frame(control, bg=PANEL)
        row.pack(fill="x", padx=18, pady=(0, 15))
        self.bit_expression = tk.StringVar(value="0xBEEF")
        self.bit_entry = self.entry(row, self.bit_expression, 16)
        self.bit_entry.pack(side="left", fill="x", expand=True, ipady=9)
        self.button(row, "INSPECT  ↵", self.inspect_bits, "accent").pack(side="left", padx=(12, 0))
        settings = tk.Frame(control, bg=PANEL)
        settings.pack(fill="x", padx=18, pady=(0, 15))
        self.label(settings, "WORD SIZE", 9, MUTED, MONO).pack(side="left", padx=(0, 12))
        for width in (8, 16, 32, 64):
            tk.Radiobutton(settings, text=str(width), variable=self.word_width, value=width,
                           command=self.inspect_bits, indicatoron=False, bg=INPUT, fg=MUTED,
                           selectcolor="#29402E", activebackground="#29402E", activeforeground=GREEN,
                           relief="flat", bd=0, padx=14, pady=6, font=(MONO, 10),
                           cursor="hand2").pack(side="left", padx=3)
        tk.Checkbutton(settings, text="Signed / two's complement", variable=self.signed,
                       command=self.render_bits, bg=PANEL, fg=TEXT, selectcolor=INPUT,
                       activebackground=PANEL, activeforeground=GREEN, font=(MONO, 10),
                       cursor="hand2").pack(side="right")
        grid_panel = self.panel(page)
        grid_panel.pack(fill="x", pady=14)
        grid_head = tk.Frame(grid_panel, bg=PANEL)
        grid_head.pack(fill="x", padx=18, pady=(13, 6))
        self.label(grid_head, "LIVE REGISTER", 9, GREEN, MONO).pack(side="left")
        self.bit_count_label = self.label(grid_head, "", 9, MUTED, MONO)
        self.bit_count_label.pack(side="right")
        self.bit_grid = tk.Frame(grid_panel, bg=PANEL)
        self.bit_grid.pack(fill="x", padx=15, pady=(0, 12))
        for column in range(32):
            self.bit_grid.columnconfigure(column, weight=1, uniform="bits")
        self.bit_cells = []
        for position in range(64):
            frame = tk.Frame(self.bit_grid, bg=PANEL)
            index_label = self.label(frame, "", 8, MUTED, MONO)
            index_label.pack()
            button = tk.Button(frame, text="0", font=(MONO, 12), bg=INPUT, fg=MUTED,
                               activebackground=GREEN, activeforeground=BG, relief="flat", bd=0,
                               cursor="hand2", pady=5, highlightthickness=1,
                               highlightbackground=BORDER, highlightcolor=GREEN,
                               command=lambda pos=position: self.flip_bit(pos))
            button.pack(fill="x", padx=2)
            self.bit_cells.append((frame, index_label, button))
        self.bit_note = self.label(grid_panel, "", 9, MUTED, MONO, anchor="w")
        self.bit_note.pack(fill="x", padx=18, pady=(0, 13))
        values = tk.Frame(page, bg=BG)
        values.pack(fill="x")
        self.word_labels = {}
        for column, name in enumerate(("DECIMAL", "HEXADECIMAL", "OCTAL")):
            values.columnconfigure(column, weight=1, uniform="values")
            card = self.panel(values)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
            self.label(card, name, 9, MUTED, MONO).pack(anchor="w", padx=15, pady=(13, 7))
            variable = tk.StringVar()
            self.word_labels[name] = variable
            field = tk.Entry(card, textvariable=variable, state="readonly", readonlybackground=PANEL,
                             fg=GREEN if column == 0 else CYAN, relief="flat", bd=0, font=(MONO, 15))
            field.pack(fill="x", padx=15, pady=(0, 13))
        self.binary_text = tk.StringVar()
        binary_card = self.panel(page)
        binary_card.pack(fill="x", pady=14)
        self.label(binary_card, "BINARY  /  MOST SIGNIFICANT BIT FIRST", 9, MUTED, MONO).pack(anchor="w", padx=16, pady=(12, 7))
        binary_entry = tk.Entry(binary_card, textvariable=self.binary_text, state="readonly",
                                readonlybackground=PANEL, fg=TEXT, relief="flat", bd=0, font=(MONO, 12))
        binary_entry.pack(fill="x", padx=16, pady=(0, 12))
        operations = self.panel(page)
        operations.pack(fill="x")
        row = tk.Frame(operations, bg=PANEL)
        row.pack(fill="x", padx=14, pady=12)
        self.label(row, "B =", 10, MUTED, MONO).pack(side="left", padx=(0, 8))
        self.operand = tk.StringVar(value="0x0F")
        self.entry(row, self.operand, 12, width=10).pack(side="left", ipady=8, padx=(0, 9))
        for op in ("AND", "OR", "XOR", "NOT", "<< 1", ">> 1"):
            self.button(row, op, lambda op=op: self.word_operation(op), "cyan", padx=10).pack(side="left", padx=3)
        self.button(row, "COPY BITS", lambda: self.copy(word_details(self.word_value, self.word_width.get())["binary"]),
                    "subtle").pack(side="right")
        self.inspect_bits()

    def inspect_bits(self):
        try:
            value = evaluate(self.bit_expression.get(), self.ans)
            details = word_details(value, self.word_width.get())
        except CalculationError as exc:
            self.status(str(exc), error=True)
            return False
        self.word_value = details["unsigned"]
        self.render_bits()
        if details["wrapped"]:
            self.bit_note.configure(text="Input wrapped to the low " + str(self.word_width.get()) + " bits. Click a bit to toggle it.", fg=AMBER)
        self.status("Register loaded. Bitwise results wrap to the selected word size.")
        return True

    def render_bits(self):
        width = self.word_width.get()
        details = word_details(self.word_value, width)
        columns = min(width, 32)
        for column in range(32):
            self.bit_grid.columnconfigure(column, weight=1 if column < columns else 0,
                                          uniform="bits" if column < columns else "")
        self.word_value = details["unsigned"]
        for position, (frame, label, button) in enumerate(self.bit_cells):
            frame.grid_forget()
            if position < width:
                frame.grid(row=position // columns, column=position % columns, sticky="ew", pady=2)
                label.configure(text=str(width - 1 - position))
                bit = details["binary"][position]
                button.configure(text=bit, bg=GREEN if bit == "1" else INPUT,
                                 fg="#14200D" if bit == "1" else MUTED,
                                 highlightbackground=GREEN if bit == "1" else BORDER)
        self.word_labels["DECIMAL"].set(str(details["signed"] if self.signed.get() else details["unsigned"]))
        self.word_labels["HEXADECIMAL"].set(details["hex"])
        self.word_labels["OCTAL"].set(details["octal"])
        binary = details["binary"]
        self.binary_text.set(" ".join(binary[index:index + 4] for index in range(0, width, 4)))
        self.bit_count_label.configure(text=f'{details["ones"]} SET / {width - details["ones"]} CLEAR')
        interpretation = "SIGNED" if self.signed.get() else "UNSIGNED"
        self.bit_note.configure(text=f"{width}-BIT {interpretation}  /  Click any bit to toggle it.", fg=MUTED)

    def flip_bit(self, position):
        self.word_value ^= 1 << (self.word_width.get() - 1 - position)
        self.bit_expression.set(str(self.word_value))
        self.render_bits()
        self.status("Bit toggled. Number representations updated.")

    def word_operation(self, operation):
        if not self.inspect_bits():
            return
        try:
            details = word_details(self.word_value, self.word_width.get())
            value = details["signed"] if self.signed.get() else details["unsigned"]
            if operation in ("AND", "OR", "XOR"):
                operand = evaluate(self.operand.get(), self.ans)
                if type(operand) is not int:
                    raise CalculationError("Operand B must be an integer.")
                value = {"AND": lambda: value & operand, "OR": lambda: value | operand,
                         "XOR": lambda: value ^ operand}[operation]()
            elif operation == "NOT":
                value = ~value
            elif operation == "<< 1":
                value <<= 1
            elif operation == ">> 1":
                value >>= 1
            self.word_value = word_details(value, self.word_width.get())["unsigned"]
            self.bit_expression.set(str(self.word_value))
            self.render_bits()
            self.status(f"{operation} applied. Right shift is {'arithmetic' if self.signed.get() else 'logical'}.")
        except CalculationError as exc:
            self.status(str(exc), error=True)

    def _build_units(self):
        page = self.pages["units"]
        page.columnconfigure(0, weight=3, uniform="unit_columns")
        page.columnconfigure(1, weight=2, uniform="unit_columns")
        page.rowconfigure(0, weight=1)
        left = self.panel(page)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.label(left, "STORAGE / MEMORY / BANDWIDTH", 9, GREEN, MONO).pack(anchor="w", padx=22, pady=(22, 20))
        self.label(left, "AMOUNT", 9, MUTED, MONO).pack(anchor="w", padx=22, pady=(0, 8))
        self.unit_amount = tk.StringVar(value="1")
        self.unit_from = tk.StringVar(value="GiB")
        self.unit_to = tk.StringVar(value="MB")
        self.entry(left, self.unit_amount, 23).pack(fill="x", padx=22, ipady=14)
        row = tk.Frame(left, bg=PANEL)
        row.pack(fill="x", padx=22, pady=20)
        row.columnconfigure(0, weight=1)
        row.columnconfigure(2, weight=1)
        self.combo(row, self.unit_from, UNITS, 10).grid(row=0, column=0, sticky="ew")
        self.button(row, "⇄", self.swap_units, "cyan").grid(row=0, column=1, padx=12)
        self.combo(row, self.unit_to, UNITS, 10).grid(row=0, column=2, sticky="ew")
        result_card = tk.Frame(left, bg=INPUT, highlightbackground=BORDER, highlightthickness=1)
        result_card.pack(fill="x", padx=22)
        self.label(result_card, "CONVERTED VALUE", 9, MUTED, MONO).pack(anchor="w", padx=17, pady=(17, 12))
        self.unit_result = tk.StringVar()
        tk.Entry(result_card, textvariable=self.unit_result, state="readonly", readonlybackground=INPUT,
                 fg=GREEN, font=(MONO, 26), bd=0, relief="flat").pack(fill="x", padx=17)
        self.unit_result_label = self.label(result_card, "", 10, MUTED, MONO)
        self.unit_result_label.pack(anchor="w", padx=17, pady=(7, 17))
        self.unit_copy_button = self.button(left, "COPY VALUE", self.copy_unit_result, "accent")
        self.unit_copy_button.pack(anchor="w", padx=22, pady=18)
        presets = tk.Frame(left, bg=PANEL)
        presets.pack(fill="x", padx=22, pady=(8, 0))
        self.label(presets, "TRY A PRESET", 9, MUTED, MONO).pack(anchor="w", pady=(0, 8))
        buttons = tk.Frame(presets, bg=PANEL)
        buttons.pack(fill="x")
        for amount, unit in (("1", "GiB"), ("512", "MiB"), ("4096", "B")):
            self.button(buttons, amount + " " + unit,
                        lambda a=amount, u=unit: self.unit_preset(a, u), "subtle").pack(side="left", padx=(0, 8))
        self.label(left, "SI:  kB = 1,000 bytes\nIEC: KiB = 1,024 bytes\n1 byte = 8 bits",
                   11, MUTED, MONO, justify="left", anchor="w").pack(fill="x", padx=22, pady=25)
        right = self.panel(page)
        right.grid(row=0, column=1, sticky="nsew")
        self.label(right, "ONE INPUT. EVERY UNIT.", 10, GREEN, MONO).pack(anchor="w", padx=18, pady=(22, 16))
        self.unit_rows = {}
        for unit in UNITS:
            row = tk.Frame(right, bg=PANEL)
            row.pack(fill="x", padx=18, pady=5)
            self.label(row, unit, 11, CYAN, MONO, width=5, anchor="w").pack(side="left")
            value = self.label(row, "", 11, TEXT, MONO, anchor="e")
            value.pack(side="right", fill="x", expand=True)
            self.unit_rows[unit] = value
        self.label(right, "Display rounded to 12 significant digits.\nCopy preserves the full conversion value.",
                   9, MUTED, justify="left", anchor="w").pack(fill="x", padx=18, pady=22)
        for variable in (self.unit_amount, self.unit_from, self.unit_to):
            variable.trace_add("write", self.update_units)
        self.update_units()

    def update_units(self, *args):
        try:
            value = convert_data(self.unit_amount.get(), self.unit_from.get(), self.unit_to.get())
            self.unit_result.set(self.decimal_display(value))
            self.unit_result_label.configure(text=self.unit_to.get(), fg=MUTED)
            for unit, label in self.unit_rows.items():
                converted = convert_data(self.unit_amount.get(), self.unit_from.get(), unit)
                label.configure(text=self.decimal_display(converted), fg=TEXT)
            self.unit_copy_button.configure(state="normal")
            if self.active_page == "units":
                self.status("Conversions updated. SI uses powers of 1000; IEC uses powers of 1024.")
        except CalculationError as exc:
            self.unit_result.set("—")
            self.unit_result_label.configure(text="Enter a valid nonnegative amount.", fg=RED)
            self.unit_copy_button.configure(state="disabled")
            for label in self.unit_rows.values():
                label.configure(text="—")
            self.status(str(exc), error=True)

    @staticmethod
    def decimal_display(value):
        if not value:
            return "0"
        result = format(value, ".12g")
        if "." in result and "e" not in result.lower():
            result = result.rstrip("0").rstrip(".")
        return result

    def copy_unit_result(self):
        try:
            value = convert_data(self.unit_amount.get(), self.unit_from.get(), self.unit_to.get())
            self.copy(format(value, "f"))
        except CalculationError as exc:
            self.status(str(exc), error=True)

    def swap_units(self):
        source, target = self.unit_from.get(), self.unit_to.get()
        self.unit_from.set(target)
        self.unit_to.set(source)

    def unit_preset(self, amount, unit):
        self.unit_from.set(unit)
        self.unit_amount.set(amount)

    def text_area(self, parent, readonly=False):
        container = tk.Frame(parent, bg=INPUT, highlightthickness=1, highlightbackground=BORDER)
        container.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        scrollbar = ttk.Scrollbar(container, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        widget = tk.Text(container, bg=INPUT, fg=TEXT, insertbackground=GREEN, relief="flat",
                         bd=0, font=(MONO, 12), wrap="word", padx=13, pady=13,
                         undo=not readonly, height=9, width=1, yscrollcommand=scrollbar.set)
        widget.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=widget.yview)
        if readonly:
            widget.configure(state="disabled", fg=GREEN)
        return widget

    def _build_codec(self):
        page = self.pages["codec"]
        toolbar = self.panel(page)
        toolbar.pack(fill="x", pady=(0, 15))
        row = tk.Frame(toolbar, bg=PANEL)
        row.pack(fill="x", padx=17, pady=16)
        self.label(row, "OPERATION", 9, MUTED, MONO).pack(side="left", padx=(0, 14))
        self.codec_mode = tk.StringVar(value=CODECS[0])
        mode = self.combo(row, self.codec_mode, CODECS, 22)
        mode.pack(side="left")
        mode.bind("<<ComboboxSelected>>", lambda event: self.run_codec())
        self.button(row, "RUN TRANSFORM", self.run_codec, "accent").pack(side="left", padx=14)
        self.button(row, "CLEAR", self.clear_codec, "subtle").pack(side="right")
        self.codec_stats = tk.StringVar(value="")
        self.label(page, "UTF-8 BY DEFAULT  /  CTRL + ENTER TO TRANSFORM", 9, MUTED, MONO).pack(anchor="w", pady=(0, 13))
        columns = tk.Frame(page, bg=BG)
        columns.pack(fill="both", expand=True)
        columns.columnconfigure(0, weight=1, uniform="codec")
        columns.columnconfigure(1, weight=1, uniform="codec")
        columns.rowconfigure(0, weight=1)
        source_panel = self.panel(columns)
        source_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.label(source_panel, "01 / INPUT", 10, MUTED, MONO).pack(anchor="w", padx=16, pady=16)
        self.codec_input = self.text_area(source_panel)
        self.codec_input.insert("1.0", "Hello, world. Stay curious.")
        self.codec_input.bind("<Control-Return>", self._codec_shortcut)
        self.codec_input.bind("<<Modified>>", self._codec_modified)
        output_panel = self.panel(columns)
        output_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.label(output_panel, "02 / OUTPUT", 10, GREEN, MONO).pack(anchor="w", padx=16, pady=16)
        self.codec_output = self.text_area(output_panel, readonly=True)
        actions = tk.Frame(page, bg=BG)
        actions.pack(fill="x", pady=15)
        self.button(actions, "COPY OUTPUT", self.copy_codec, "cyan").pack(side="left")
        self.button(actions, "OUTPUT → INPUT", self.reuse_codec, "subtle").pack(side="left", padx=10)
        tk.Label(actions, textvariable=self.codec_stats, bg=BG, fg=MUTED,
                 font=(MONO, 9)).pack(side="right")
        note = self.panel(page)
        note.pack(fill="x")
        self.label(note, "ENCODING IS REVERSIBLE. HASHING IS ONE-WAY.", 10, GREEN, MONO).pack(anchor="w", padx=17, pady=(15, 8))
        self.label(note, "Base64 and hex represent bytes as text. SHA and MD5 produce fixed-length digests.\n"
                        "Text is processed exactly as entered, including whitespace and line breaks.",
                   10, MUTED, justify="left", anchor="w").pack(fill="x", padx=17, pady=(0, 15))
        self.run_codec()

    def _codec_shortcut(self, event):
        self.run_codec()
        return "break"

    def _codec_modified(self, event):
        if self.codec_input.edit_modified():
            self.codec_input.edit_modified(False)
            self.codec_stats.set("Input changed / run to update")
            if hasattr(self, "codec_output"):
                self.set_codec_output("")

    def set_codec_output(self, text):
        self.codec_output.configure(state="normal")
        self.codec_output.delete("1.0", "end")
        self.codec_output.insert("1.0", text)
        self.codec_output.configure(state="disabled")

    def run_codec(self):
        source = self.codec_input.get("1.0", "end-1c")
        try:
            output = transform_text(source, self.codec_mode.get())
        except CalculationError as exc:
            self.set_codec_output("")
            self.codec_stats.set("Invalid input")
            self.status(str(exc), error=True)
            return
        self.codec_input.edit_modified(False)
        self.set_codec_output(output)
        self.codec_stats.set(f"{len(source.encode('utf-8')):,} BYTES IN  /  {len(output.encode('utf-8')):,} BYTES OUT")
        self.status(self.codec_mode.get() + " complete.")

    def copy_codec(self):
        self.copy(self.codec_output.get("1.0", "end-1c"))

    def reuse_codec(self):
        output = self.codec_output.get("1.0", "end-1c")
        pairs = {"Text to Base64": "Base64 to text", "Base64 to text": "Text to Base64",
                 "Text to hex": "Hex to text", "Hex to text": "Text to hex",
                 "URL encode": "URL decode", "URL decode": "URL encode"}
        self.codec_input.delete("1.0", "end")
        self.codec_input.insert("1.0", output)
        self.codec_mode.set(pairs.get(self.codec_mode.get(), self.codec_mode.get()))
        self.run_codec()

    def clear_codec(self):
        self.codec_input.delete("1.0", "end")
        self.set_codec_output("")
        self.codec_stats.set("0 BYTES")
        self.codec_input.focus_set()

    def _build_network(self):
        page = self.pages["network"]
        control = self.panel(page)
        control.pack(fill="x")
        self.label(control, "ADDRESS / PREFIX", 9, MUTED, MONO).pack(anchor="w", padx=19, pady=(17, 10))
        row = tk.Frame(control, bg=PANEL)
        row.pack(fill="x", padx=19, pady=(0, 17))
        self.network_input = tk.StringVar(value="192.168.1.42/24")
        self.entry(row, self.network_input, 19).pack(side="left", fill="x", expand=True, ipady=12)
        self.button(row, "MAP NETWORK  ↵", self.calculate_network, "accent").pack(side="left", padx=(14, 0))
        presets = tk.Frame(page, bg=BG)
        presets.pack(fill="x", pady=14)
        for cidr in ("192.168.1.42/24", "10.0.0.0/16", "172.16.0.0/30", "2001:db8::/64"):
            self.button(presets, cidr, lambda text=cidr: self.network_preset(text), "subtle").pack(side="left", padx=(0, 8))
        results = self.panel(page)
        results.pack(fill="both", expand=True)
        head = tk.Frame(results, bg=PANEL)
        head.pack(fill="x", padx=19, pady=(16, 9))
        self.label(head, "NETWORK INTELLIGENCE", 10, GREEN, MONO).pack(side="left")
        self.button(head, "COPY REPORT", self.copy_network, "cyan").pack(side="right")
        self.network_rows = []
        for index in range(10):
            row = tk.Frame(results, bg=PANEL if index % 2 == 0 else "#14212B")
            row.pack(fill="both", expand=True, padx=12)
            key = self.label(row, "", 10, MUTED, MONO, width=18, anchor="w")
            key.pack(side="left", padx=9)
            variable = tk.StringVar()
            value = tk.Entry(row, textvariable=variable, state="readonly",
                             readonlybackground=row.cget("bg"), fg=TEXT, font=(MONO, 11),
                             relief="flat", bd=0, justify="right")
            value.pack(side="right", fill="x", expand=True, padx=10, pady=5)
            self.network_rows.append((key, variable))
        self.label(results, "Host input is normalized to its network boundary.", 9, MUTED).pack(anchor="w", padx=20, pady=13)
        self.label(page, "IPv4 /31 and /32 include all addresses. IPv6 has no broadcast; the subnet-router\n"
                         "anycast address is excluded from host counts except for /127 and /128.",
                   9, MUTED, justify="left", anchor="w").pack(fill="x", pady=(13, 0))
        self.network_report = {}
        self.calculate_network()
        self.network_input.trace_add("write", self._network_changed)

    def _network_changed(self, *args):
        self.network_report = {}
        for key, variable in self.network_rows:
            variable.set("—")
        self.status("Address changed. Press Enter to map the network.")

    def calculate_network(self):
        try:
            report = inspect_network(self.network_input.get())
        except CalculationError as exc:
            self.network_report = {}
            for key, variable in self.network_rows:
                variable.set("—")
            self.status(str(exc), error=True)
            return
        self.network_report = report
        for (key, variable), (name, value) in zip(self.network_rows, report.items()):
            key.configure(text=name)
            variable.set(value)
        self.status("Network mapped locally. No network requests were made.")

    def network_preset(self, cidr):
        self.network_input.set(cidr)
        self.calculate_network()

    def copy_network(self):
        if self.network_report:
            self.copy("\n".join(key + ": " + value for key, value in self.network_report.items()))
        else:
            self.status("Map a valid network first.", error=True)


def main():
    app = NeonCalculator()
    app.mainloop()


if __name__ == "__main__":
    main()

