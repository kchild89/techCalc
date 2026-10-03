"""IEEE-754, graphing, and algorithm growth screens for the command hub."""
import csv
import math
import tkinter as tk
from tkinter import filedialog, ttk

from calculator_core import CalculationError
from calculator_ui import BG, PANEL, INPUT, BORDER, TEXT, MUTED, CYAN, RED, AMBER, MONO
from hub_core import COMPLEXITIES, CURVE_COLORS, complexity_estimate, float_details, growth_log10, sample_graph


class LabsMixin:
    def build_float_lab(self):
        page = self.pages["float"]
        controls = self.panel(page)
        controls.pack(fill="x", pady=(0, 14))
        self.label(controls, "VALUE OR EXPRESSION", 9, MUTED, MONO).pack(anchor="w", padx=18, pady=(15, 8))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=18, pady=(0, 15))
        self.float_source = tk.StringVar(value="0.1 + 0.2")
        self.entry(row, self.float_source, 18).pack(side="left", fill="x", expand=True, ipady=10)
        self.float_width = tk.StringVar(value="64")
        self.combo(row, self.float_width, ("32", "64"), 5).pack(side="left", padx=12)
        self.button(row, "INSPECT FLOAT", self.inspect_float, "accent").pack(side="left")
        examples = tk.Frame(page, bg=BG)
        examples.pack(fill="x", pady=(0, 12))
        for value in ("0.1 + 0.2", "0.3", "-0.0", "1e-40", "inf", "nan"):
            self.button(examples, value, lambda value=value: self.float_preset(value), "subtle").pack(side="left", padx=(0, 8))
        panel = self.panel(page)
        panel.pack(fill="x", pady=(0, 14))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", padx=17, pady=(15, 9))
        for text, color in (("SIGN", RED), ("EXPONENT", AMBER), ("FRACTION / MANTISSA", CYAN)):
            self.label(row, text, 10, color, MONO).pack(side="left", padx=(0, 28))
        self.float_canvas = tk.Canvas(panel, bg=INPUT, bd=0, highlightthickness=0, height=self.px(125))
        self.float_canvas.pack(fill="x", padx=17, pady=(0, 15))
        self.float_canvas.bind("<Configure>", lambda event: self.draw_float())
        self.float_info = self.make_text(page, height=9)
        note = self.panel(page)
        note.pack(fill="x", pady=(12, 0))
        self.label(note, "WHY 0.1 + 0.2 IS NOT EXACTLY 0.3", 10, self.accent, MONO).pack(anchor="w", padx=17, pady=(13, 7))
        self.label(note, "Most decimal fractions repeat in binary. Each operand is rounded to a representable value, then the sum is rounded again.\n"
                         "Binary32 rounds the evaluated Python binary64 value to 32 bits. The exact decimal readout reveals what is stored.",
                   10, MUTED, justify="left", anchor="w").pack(fill="x", padx=17, pady=(0, 14))
        self.float_data = None
        self.float_width.trace_add("write", lambda *args: self.inspect_float())
        self.inspect_float()

    def float_preset(self, value):
        self.float_source.set(value)
        self.inspect_float()

    def inspect_float(self):
        try:
            details = float_details(self.float_source.get(), int(self.float_width.get()), self.variables)
        except (CalculationError, ValueError) as exc:
            self.float_data = None
            self.float_canvas.delete("all")
            self.text_set(self.float_info, "Unable to inspect this input.\n\n" + str(exc))
            self.status(str(exc), True)
            return
        self.float_data = details
        self.draw_float()
        normal = details["classification"] == "Normal"
        formula = "(-1)^sign × (1 + fraction / 2^p) × 2^(exponent - bias)" if normal else (
            "(-1)^sign × (fraction / 2^p) × 2^(1 - bias)" if details["classification"] in ("Subnormal", "Signed zero")
            else "The all-ones exponent encodes infinity or NaN.")
        self.text_set(self.float_info,
            f'IEEE-754 BINARY{details["width"]}  /  {details["classification"]}\n\n'
            f'Stored value         {details["value"]}\n'
            f'Raw hexadecimal      {details["hex"]}\n'
            f'Sign                 {details["sign"]}  ({"negative" if details["sign"] == "1" else "positive"})\n'
            f'Exponent field       {details["exponent"]}   |   bias {details["bias"]}   |   unbiased {details["unbiased"]}\n'
            f'Fraction precision   {details["fraction_width"]} stored bits\n'
            f'Hex float            {details["float_hex"]}\n\n'
            f'EXACT DECIMAL\n{details["exact"]}\n\n{formula}')
        self.status("Floating-point representation decoded locally.")

    def draw_float(self):
        if not getattr(self, "float_data", None):
            return
        canvas, details = self.float_canvas, self.float_data
        canvas.delete("all")
        width = max(300, canvas.winfo_width())
        columns = 32 if details["width"] == 64 else 32
        box = (width - 24) / columns
        exponent_end = 1 + len(details["exponent_bits"])
        for index, bit in enumerate(details["bits"]):
            row, column = divmod(index, columns)
            x = 12 + column * box
            y = 10 + row * self.px(52)
            color = RED if index == 0 else AMBER if index < exponent_end else CYAN
            canvas.create_text(x + box / 2, y, text=str(details["width"] - index - 1),
                               fill=MUTED, font=(MONO, 8), anchor="n")
            canvas.create_rectangle(x + 1, y + self.px(15), x + box - 2, y + self.px(45),
                                    fill="#172630", outline=color)
            canvas.create_text(x + box / 2, y + self.px(30), text=bit, fill=color, font=(MONO, 12))

    def build_graph_lab(self):
        page = self.pages["graph"]
        controls = self.panel(page)
        controls.pack(fill="x", pady=(0, 12))
        self.label(controls, "FUNCTIONS OF x  /  SEPARATE UP TO THREE WITH ;", 9, MUTED, MONO).pack(anchor="w", padx=17, pady=(14, 8))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=17, pady=(0, 12))
        self.graph_source = tk.StringVar(value="sin(x); cos(x)")
        self.entry(row, self.graph_source, 15).pack(side="left", fill="x", expand=True, ipady=9)
        self.button(row, "PLOT", self.plot_graph, "accent").pack(side="left", padx=(12, 0))
        options = tk.Frame(controls, bg=PANEL)
        options.pack(fill="x", padx=17, pady=(0, 14))
        self.graph_xmin, self.graph_xmax = tk.StringVar(value="-10"), tk.StringVar(value="10")
        for title, variable in (("X MIN", self.graph_xmin), ("X MAX", self.graph_xmax)):
            self.label(options, title, 9, MUTED, MONO).pack(side="left", padx=(0, 8))
            self.entry(options, variable, 11, width=9).pack(side="left", ipady=7, padx=(0, 18))
        self.button(options, "RESET VIEW", self.reset_graph, "subtle").pack(side="left", padx=(0, 8))
        self.button(options, "EXPORT CSV", self.export_graph, "subtle").pack(side="right")
        examples = tk.Frame(page, bg=BG)
        examples.pack(fill="x", pady=(0, 10))
        for expression in ("sin(x); cos(x)", "x; x**2", "log2(x); sqrt(x)", "1/x"):
            self.button(examples, expression, lambda value=expression: self.graph_preset(value), "subtle").pack(side="left", padx=(0, 8))
        self.graph_canvas = tk.Canvas(page, bg=INPUT, bd=0, highlightbackground=BORDER, highlightthickness=1)
        self.graph_canvas.pack(fill="both", expand=True)
        self.graph_canvas.bind("<Configure>", lambda event: self.draw_graph())
        self.graph_canvas.bind("<MouseWheel>", self.zoom_graph)
        self.graph_canvas.bind("<Button-4>", lambda event: self.zoom_graph(event, 1))
        self.graph_canvas.bind("<Button-5>", lambda event: self.zoom_graph(event, -1))
        self.graph_canvas.bind("<ButtonPress-1>", self.start_graph_pan)
        self.graph_canvas.bind("<B1-Motion>", self.pan_graph)
        self.graph_canvas.bind("<ButtonRelease-1>", self.end_graph_pan)
        self.graph_canvas.bind("<Motion>", self.graph_pointer)
        self.graph_help = tk.StringVar(value="Scroll to zoom  /  Drag to pan  /  Plot to fit y automatically")
        tk.Label(page, textvariable=self.graph_help, bg=BG, fg=MUTED, font=(MONO, 9),
                 anchor="w").pack(fill="x", pady=(10, 0))
        self.graph_series = []
        self.graph_bounds = (-10, 10, -1.2, 1.2)
        self.graph_drag = None
        self.graph_error = ""
        self.plot_graph()

    def graph_preset(self, expression):
        self.graph_source.set(expression)
        self.reset_graph()

    def reset_graph(self):
        self.graph_xmin.set("-10")
        self.graph_xmax.set("10")
        self.plot_graph()

    def plot_graph(self, keep_y=False):
        try:
            expressions = [text.strip() for text in self.graph_source.get().split(";") if text.strip()]
            if not expressions or len(expressions) > 3:
                raise CalculationError("Enter one to three expressions separated by semicolons.")
            minimum, maximum = float(self.graph_xmin.get()), float(self.graph_xmax.get())
            series = [(expression, sample_graph(expression, minimum, maximum, self.variables))
                      for expression in expressions]
            values = [y for _, points in series for _, y in points if y is not None]
            if keep_y:
                y_min, y_max = self.graph_bounds[2:]
            else:
                y_min, y_max = min(values), max(values)
                padding = max((y_max - y_min) * 0.1, abs(y_min) * 0.05, 1e-9)
                if y_min == y_max == 0:
                    padding = 1
                y_min, y_max = y_min - padding, y_max + padding
            self.graph_bounds = (minimum, maximum, y_min, y_max)
            self.graph_series = series
            self.graph_error = ""
            invalid = sum(y is None for _, points in series for _, y in points)
            self.graph_help.set(f"{len(series)} curves  /  {invalid} undefined samples skipped  /  Scroll: zoom  /  Drag: pan")
            self.draw_graph()
            self.status("Graph sampled using the calculator's bounded expression engine.")
        except (CalculationError, ValueError, OverflowError) as exc:
            self.graph_error = str(exc)
            self.graph_series = []
            self.draw_graph()
            self.status(str(exc), True)

    def graph_rectangle(self):
        canvas = self.graph_canvas
        return self.px(65), self.px(45), max(self.px(180), canvas.winfo_width() - self.px(25)), max(self.px(130), canvas.winfo_height() - self.px(45))

    def draw_graph(self):
        if not hasattr(self, "graph_series"):
            return
        canvas = self.graph_canvas
        canvas.delete("all")
        left, top, right, bottom = self.graph_rectangle()
        x_min, x_max, y_min, y_max = self.graph_bounds
        if x_max <= x_min or y_max <= y_min:
            return
        def point(x, y):
            return left + (x - x_min) / (x_max - x_min) * (right - left), bottom - (y - y_min) / (y_max - y_min) * (bottom - top)
        for tick in range(6):
            ratio = tick / 5
            x = left + ratio * (right - left)
            y = bottom - ratio * (bottom - top)
            canvas.create_line(x, top, x, bottom, fill="#1A2C37")
            canvas.create_line(left, y, right, y, fill="#1A2C37")
            canvas.create_text(x, bottom + self.px(18), text=f"{x_min + ratio * (x_max - x_min):.3g}", fill=MUTED, font=(MONO, 9))
            canvas.create_text(left - self.px(8), y, text=f"{y_min + ratio * (y_max - y_min):.3g}", fill=MUTED, font=(MONO, 9), anchor="e")
        if x_min <= 0 <= x_max:
            x, _ = point(0, 0)
            canvas.create_line(x, top, x, bottom, fill="#496170")
        if y_min <= 0 <= y_max:
            _, y = point(0, 0)
            canvas.create_line(left, y, right, y, fill="#496170")
        for index, (expression, points) in enumerate(self.graph_series):
            color = CURVE_COLORS[index]
            canvas.create_text(left + index * self.px(220), self.px(18), text=expression[:35],
                               fill=color, font=(MONO, 10), anchor="w")
            previous = None
            for x, y in points:
                if y is None or y < y_min or y > y_max:
                    previous = None
                    continue
                current = point(x, y)
                if previous and abs(current[1] - previous[1]) < (bottom - top) * 0.75:
                    canvas.create_line(*previous, *current, fill=color, width=2)
                previous = current
        if self.graph_error:
            canvas.create_text((left + right) / 2, (top + bottom) / 2, text=self.graph_error,
                               fill=RED, font=(MONO, 12), width=right - left - 30)

    def zoom_graph(self, event, direction=None):
        if not self.graph_series:
            return "break"
        direction = direction if direction is not None else (1 if event.delta > 0 else -1)
        factor = 0.8 if direction > 0 else 1.25
        left, top, right, bottom = self.graph_rectangle()
        ratio_x = max(0, min(1, (event.x - left) / (right - left)))
        ratio_y = max(0, min(1, (bottom - event.y) / (bottom - top)))
        x_min, x_max, y_min, y_max = self.graph_bounds
        center_x = x_min + ratio_x * (x_max - x_min)
        center_y = y_min + ratio_y * (y_max - y_min)
        new_min, new_max = center_x + (x_min - center_x) * factor, center_x + (x_max - center_x) * factor
        if new_max - new_min < 1e-10 or new_min < -1e6 or new_max > 1e6:
            return "break"
        self.graph_bounds = (new_min, new_max, center_y + (y_min - center_y) * factor, center_y + (y_max - center_y) * factor)
        self.graph_xmin.set(f"{new_min:.12g}")
        self.graph_xmax.set(f"{new_max:.12g}")
        self.plot_graph(keep_y=True)
        return "break"

    def start_graph_pan(self, event):
        self.graph_drag = (event.x, event.y, self.graph_bounds)

    def pan_graph(self, event):
        if not self.graph_drag:
            return
        start_x, start_y, bounds = self.graph_drag
        left, top, right, bottom = self.graph_rectangle()
        dx = (event.x - start_x) / (right - left) * (bounds[1] - bounds[0])
        dy = (event.y - start_y) / (bottom - top) * (bounds[3] - bounds[2])
        new_bounds = (bounds[0] - dx, bounds[1] - dx, bounds[2] + dy, bounds[3] + dy)
        if new_bounds[0] < -1e6 or new_bounds[1] > 1e6:
            return
        self.graph_bounds = new_bounds
        self.draw_graph()

    def end_graph_pan(self, event):
        if self.graph_drag:
            self.graph_drag = None
            self.graph_xmin.set(f"{self.graph_bounds[0]:.12g}")
            self.graph_xmax.set(f"{self.graph_bounds[1]:.12g}")
            self.plot_graph(keep_y=True)

    def graph_pointer(self, event):
        if self.graph_drag:
            return
        left, top, right, bottom = self.graph_rectangle()
        x_min, x_max, y_min, y_max = self.graph_bounds
        x = x_min + (event.x - left) / (right - left) * (x_max - x_min)
        y = y_max - (event.y - top) / (bottom - top) * (y_max - y_min)
        self.graph_help.set(f"Cursor x={x:.6g}, y={y:.6g}  /  Scroll: zoom  /  Drag: pan  /  Undefined samples break the curve")

    def export_graph(self):
        if not self.graph_series:
            self.status("Plot a graph before exporting.", True)
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile="neon-graph.csv",
                                           filetypes=[("CSV", "*.csv")])
        if path:
            try:
                with open(path, "w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["x"] + ["y: " + expression for expression, _ in self.graph_series])
                    for index in range(len(self.graph_series[0][1])):
                        writer.writerow([self.graph_series[0][1][index][0]] + [
                            "" if points[index][1] is None else points[index][1] for _, points in self.graph_series])
                self.status("Graph samples exported.")
            except OSError as exc:
                self.status("Export failed: " + str(exc), True)

    def build_complexity_lab(self):
        page = self.pages["complexity"]
        controls = self.panel(page)
        controls.pack(fill="x", pady=(0, 12))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=18, pady=(15, 9))
        self.label(row, "INPUT SIZE n", 9, MUTED, MONO).pack(side="left", padx=(0, 9))
        self.complex_n = tk.StringVar(value="1024")
        self.entry(row, self.complex_n, 13, width=10).pack(side="left", ipady=7)
        self.label(row, "COST / OPERATION (ns)", 9, MUTED, MONO).pack(side="left", padx=(24, 9))
        self.complex_cost = tk.StringVar(value="1")
        self.entry(row, self.complex_cost, 13, width=10).pack(side="left", ipady=7)
        self.button(row, "COMPARE", self.draw_complexity, "accent").pack(side="right")
        self.complex_slider = tk.Scale(controls, from_=0, to=5, resolution=0.0001, orient="horizontal",
                                       showvalue=False, bg=PANEL, troughcolor=INPUT, fg=MUTED,
                                       activebackground=CYAN, highlightthickness=0, bd=0,
                                       command=self.complex_slide)
        self.complex_slider.set(math.log10(1024))
        self.complex_slider.pack(fill="x", padx=18, pady=(0, 5))
        checks = tk.Frame(controls, bg=PANEL)
        checks.pack(fill="x", padx=18, pady=(0, 12))
        self.complex_visible = {}
        for index, name in enumerate(COMPLEXITIES):
            variable = tk.BooleanVar(value=index < 4)
            self.complex_visible[name] = variable
            tk.Checkbutton(checks, text=name, variable=variable, command=self.draw_complexity,
                           bg=PANEL, fg=CURVE_COLORS[index], selectcolor=INPUT,
                           activebackground=PANEL, activeforeground=TEXT,
                           font=(MONO, 10)).pack(side="left", padx=(0, 16))
        self.complex_canvas = tk.Canvas(page, bg=INPUT, highlightbackground=BORDER, highlightthickness=1)
        self.complex_canvas.pack(fill="both", expand=True, pady=(0, 12))
        self.complex_canvas.bind("<Configure>", lambda event: self.draw_complexity())
        self.complex_table = self.make_tree(page, ("MODEL", "OPERATIONS", "ESTIMATED TIME"),
                                           (180, 250, 320), height=6, expand=False)
        note = self.label(page, "Slider uses log10(n). Chart uses log10(max(1, operations)). These are growth models, not benchmarks;\n"
                          "real hardware, implementation, constants, and input characteristics change actual runtime.",
                          9, MUTED, justify="left", anchor="w")
        note.pack(side="bottom", fill="x", pady=(10, 0), before=self.complex_canvas)
        self.complex_table.master.pack_configure(side="bottom", before=self.complex_canvas)
        self.draw_complexity()

    def complex_slide(self, value):
        if hasattr(self, "complex_n"):
            try:
                current = int(self.complex_n.get())
                if current > 0 and abs(math.log10(current) - float(value)) < 0.00006:
                    return
            except ValueError:
                pass
            self.complex_n.set(str(round(10 ** float(value))))
        if hasattr(self, "complex_table"):
            self.draw_complexity()

    def draw_complexity(self):
        if not hasattr(self, "complex_table"):
            return
        try:
            n = int(self.complex_n.get())
            cost = float(self.complex_cost.get())
            estimates = [(name, *complexity_estimate(name, n, cost)) for name in COMPLEXITIES]
        except (ValueError, CalculationError, OverflowError) as exc:
            self.status(str(exc) or "Enter a valid input size and operation cost.", True)
            return
        if abs(float(self.complex_slider.get()) - math.log10(n)) > 0.00006:
            self.complex_slider.set(math.log10(n))
        self.complex_table.delete(*self.complex_table.get_children())
        for row in estimates:
            self.complex_table.insert("", "end", values=row)
        canvas = self.complex_canvas
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 400), max(canvas.winfo_height(), 180)
        left, top, right, bottom = self.px(65), self.px(24), width - self.px(25), height - self.px(40)
        active = [name for name, variable in self.complex_visible.items() if variable.get()]
        maximum = max([growth_log10(name, n) for name in active] + [1])
        for tick in range(6):
            ratio = tick / 5
            y = bottom - ratio * (bottom - top)
            x = left + ratio * (right - left)
            canvas.create_line(left, y, right, y, fill="#1A2C37")
            canvas.create_line(x, top, x, bottom, fill="#1A2C37")
            exponent = maximum * ratio
            label = f"1e{exponent:.1f}" if exponent < 1000 else f"1e{exponent:.0f}"
            canvas.create_text(left - 8, y, text=label, fill=MUTED, font=(MONO, 8), anchor="e")
            canvas.create_text(x, bottom + self.px(17), text=f"{max(1, round(n * ratio)):,}", fill=MUTED, font=(MONO, 9))
        for name in active:
            points = []
            for index in range(181):
                value = 1 + (n - 1) * index / 180
                points.extend((left + index / 180 * (right - left),
                               bottom - growth_log10(name, value) / maximum * (bottom - top)))
            canvas.create_line(*points, fill=CURVE_COLORS[COMPLEXITIES.index(name)], width=2)
        if not active:
            canvas.create_text((left + right) / 2, (top + bottom) / 2, text="Select a model above to plot it.",
                               fill=MUTED, font=(MONO, 12))

