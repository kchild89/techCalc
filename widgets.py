"""Small Tk widgets shared by the hub; no optional GUI dependencies."""
import re
import tkinter as tk

from calculator_core import FUNCTIONS
from hub_core import FUNCTION_HINTS

BG = "#080D12"
PANEL = "#111C25"
INPUT = "#0A1219"
TEXT = "#E6F0F5"
MUTED = "#8499A9"
BORDER = "#233541"


class Tooltip:
    def __init__(self, widget, message):
        self.widget, self.message = widget, message
        self.window = None
        self.timer = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def schedule(self, event=None):
        self.hide()
        self.timer = self.widget.after(500, self.show)

    def show(self):
        self.timer = None
        if not self.widget.winfo_exists():
            return
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.geometry(f"+{self.widget.winfo_rootx() + 12}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 8}")
        tk.Label(self.window, text=self.message, bg="#22313B", fg=TEXT, padx=12, pady=9,
                 font=("Segoe UI", 10), wraplength=430, justify="left",
                 relief="solid", borderwidth=1).pack()

    def hide(self, event=None):
        if self.timer:
            try:
                self.widget.after_cancel(self.timer)
            except tk.TclError:
                pass
            self.timer = None
        if self.window:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None


class SmartExpression(tk.Text):
    """One-line syntax editor with the Entry methods used by the original keypad."""
    def __init__(self, parent, variable, app):
        super().__init__(parent, height=1, wrap="none", bg=INPUT, fg=TEXT,
                         insertbackground=app.accent, font=("Consolas", 17),
                         relief="flat", bd=0, undo=True, padx=0, pady=4,
                         selectbackground="#30482C", selectforeground=TEXT,
                         highlightthickness=0)
        self.variable, self.app = variable, app
        self.guard = False
        self.popup = None
        self.suggestions = []
        self.suggestion_list = None
        self.trace_id = variable.trace_add("write", self._from_variable)
        self.tag_configure("number", foreground="#66D9EF")
        self.tag_configure("function", foreground="#C7ABFF")
        self.tag_configure("match", background="#36532C", foreground=TEXT)
        self.tag_configure("error", background="#552B38", foreground="#FFB5C0")
        self.bind("<<Modified>>", self._modified)
        self.bind("<KeyRelease>", self._key_release)
        self.bind("<ButtonRelease-1>", lambda event: self.highlight())
        self.bind("<Return>", lambda event: self._calculate())
        self.bind("<KP_Enter>", lambda event: self._calculate())
        self.bind("<Tab>", self.complete)
        self.bind("<Down>", self.focus_suggestions)
        self.bind("<Escape>", self.dismiss)
        self.bind("<Destroy>", self._cleanup)
        self._from_variable()

    def _calculate(self):
        self.hide_suggestions()
        self.app.calculate()
        return "break"

    def _cleanup(self, event):
        if event.widget is self:
            self.hide_suggestions()
            try:
                self.variable.trace_remove("write", self.trace_id)
            except tk.TclError:
                pass

    def _offset(self, index):
        if isinstance(index, int):
            return index
        if index == "end":
            return len(super().get("1.0", "end-1c"))
        return int(super().index(index).split(".")[1])

    def _text_index(self, index):
        return f"1.{max(0, self._offset(index))}"

    def index(self, index):
        return self._offset(index)

    def icursor(self, index):
        self.mark_set("insert", self._text_index(index))
        self.see("insert")
        self.highlight()

    def selection_present(self):
        return bool(self.tag_ranges("sel"))

    def selection_range(self, first, last):
        self.tag_remove("sel", "1.0", "end")
        self.tag_add("sel", self._text_index(first), self._text_index(last))

    def selection_clear(self):
        self.tag_remove("sel", "1.0", "end")

    def insert(self, index, text, *args):
        super().insert(self._text_index(index), str(text).replace("\n", " ").replace("\r", " "), *args)
        self._modified()

    def delete(self, first, last=None):
        start = self._offset(first)
        stop = start + 1 if last is None else self._offset(last)
        super().delete(f"1.{start}", f"1.{stop}")
        self._modified()

    def _from_variable(self, *args):
        if self.guard:
            return
        value = self.variable.get().replace("\r", " ").replace("\n", " ")[:512]
        if super().get("1.0", "end-1c") == value:
            return
        position = self._offset("insert")
        self.guard = True
        super().delete("1.0", "end")
        super().insert("1.0", value)
        self.mark_set("insert", f"1.{min(position, len(value))}")
        self.edit_modified(False)
        self.guard = False
        self.highlight()

    def _modified(self, event=None):
        if self.guard or not self.edit_modified():
            return
        self.guard = True
        value = super().get("1.0", "end-1c").replace("\r", " ").replace("\n", " ")[:512]
        if super().get("1.0", "end-1c") != value:
            super().delete("1.0", "end")
            super().insert("1.0", value)
        self.variable.set(value)
        self.edit_modified(False)
        self.guard = False
        self.highlight()

    def highlight(self):
        text = super().get("1.0", "end-1c")
        for tag in ("function", "number", "match", "error"):
            self.tag_remove(tag, "1.0", "end")
        for match in re.finditer(r"\b(?:0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+(?:\.\d*)?(?:e[+-]?\d+)?)", text):
            self.tag_add("number", f"1.{match.start()}", f"1.{match.end()}")
        for match in re.finditer(r"\b[A-Za-z_]\w*(?=\s*\()", text):
            self.tag_add("function", f"1.{match.start()}", f"1.{match.end()}")
        caret = self._offset("insert")
        position = caret - 1 if caret > 0 and text[caret - 1:caret] in ("(", ")") else caret
        if 0 <= position < len(text) and text[position] in "()":
            step = 1 if text[position] == "(" else -1
            balance = 0
            for offset in range(position, len(text) if step == 1 else -1, step):
                char = text[offset]
                balance += (1 if char == text[position] else -1) if char in "()" else 0
                if balance == 0:
                    for target in (position, offset):
                        self.tag_add("match", f"1.{target}", f"1.{target + 1}")
                    break
        calls = re.findall(r"\b([A-Za-z_]\w*)\([^()]*$", text[:caret])
        hint = FUNCTION_HINTS.get(calls[-1], "") if calls else ""
        if hasattr(self.app, "editor_hint"):
            self.app.editor_hint.set(hint or "Tab: autocomplete   |   name = value: save a variable   |   Ctrl+K: commands")

    def show_error(self, position):
        position = max(0, min(position or 0, max(0, len(self.variable.get()) - 1)))
        self.tag_add("error", f"1.{position}", f"1.{position + 1}")
        self.icursor(position)
        # icursor refreshes syntax, so apply the error mark after moving.
        self.tag_add("error", f"1.{position}", f"1.{position + 1}")
        self.focus_set()

    def _key_release(self, event):
        if event.keysym in ("Return", "Escape", "Tab", "Up", "Down", "Left", "Right", "Control_L", "Control_R"):
            return
        self.highlight()
        self.show_suggestions()

    def show_suggestions(self):
        position = self._offset("insert")
        match = re.search(r"[A-Za-z_]\w*$", self.variable.get()[:position])
        candidates = sorted(set(FUNCTIONS) | {"ans", "pi", "e", "tau"} | set(self.app.variables))
        self.suggestions = [name for name in candidates if match and name.startswith(match.group()) and name != match.group()]
        if not match or len(match.group()) < 2 or not self.suggestions:
            self.hide_suggestions()
            return
        if self.popup is None:
            self.popup = tk.Toplevel(self)
            self.popup.overrideredirect(True)
            self.popup.attributes("-topmost", True)
            self.suggestion_list = tk.Listbox(
                self.popup, bg=PANEL, fg=TEXT, font=("Consolas", 11), bd=1, relief="solid",
                selectbackground="#29402E", selectforeground=self.app.accent,
                activestyle="none", exportselection=False, width=26)
            self.suggestion_list.pack()
            self.suggestion_list.bind("<Return>", self.complete)
            self.suggestion_list.bind("<Tab>", self.complete)
            self.suggestion_list.bind("<ButtonRelease-1>", self.complete)
            self.suggestion_list.bind("<Escape>", self.dismiss)
        self.popup.geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        self.suggestion_list.delete(0, "end")
        for name in self.suggestions[:7]:
            self.suggestion_list.insert("end", name + ("(" if name in FUNCTIONS else ""))
        self.suggestion_list.configure(height=min(7, len(self.suggestions)))
        self.suggestion_list.selection_set(0)

    def complete(self, event=None):
        if not self.suggestions:
            self.show_suggestions()
        if self.suggestions:
            selected = self.suggestion_list.curselection() if self.suggestion_list else ()
            choice = self.suggestions[selected[0] if selected else 0]
            position = self._offset("insert")
            match = re.search(r"[A-Za-z_]\w*$", self.variable.get()[:position])
            if match:
                self.delete(match.start(), position)
                self.insert(match.start(), choice + ("(" if choice in FUNCTIONS else ""))
                self.icursor(match.start() + len(choice) + (1 if choice in FUNCTIONS else 0))
        self.hide_suggestions()
        self.focus_set()
        return "break"

    def focus_suggestions(self, event=None):
        if self.popup:
            self.suggestion_list.focus_set()
            return "break"

    def hide_suggestions(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
        self.suggestion_list = None
        self.suggestions = []

    def dismiss(self, event=None):
        if self.popup:
            self.hide_suggestions()
        else:
            self.app.clear_expression()
        self.focus_set()
        return "break"

