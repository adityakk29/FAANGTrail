"""Desktop interface for practicing roadmap challenges locally."""

from __future__ import annotations

import queue
import io
import builtins
import re
import threading
import tkinter as tk
import tokenize
import token
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .roadmap import Challenge, load_challenges
from .runner import RunResult, run_python


COLORS = {
    "activity": "#141719",
    "sidebar": "#1c2022",
    "editor": "#171b1d",
    "panel": "#202628",
    "input": "#2b3537",
    "border": "#303b3d",
    "text": "#c8d2d0",
    "bright": "#f2f7f5",
    "muted": "#82908e",
    "blue": "#43c6a3",
    "blue_hover": "#55d5b2",
    "selection": "#264f78",
    "green": "#89d185",
    "orange": "#e6b86a",
    "coral": "#e98470",
    "code_background": "#15191b",
    "code_text": "#d6e0dd",
}

SYNTAX_COLORS = {
    "keyword": "#e89ac7",
    "builtin": "#67d6c2",
    "function": "#f0c77b",
    "class": "#67d6c2",
    "variable": "#9fcbea",
    "string": "#e9a487",
    "number": "#b9d995",
    "comment": "#729b83",
    "operator": "#d6e0dd",
}


STARTER_CODE = """def solve():
    # Write your solution here.
    pass


if __name__ == \"__main__\":
    solve()
"""


class PracticeApp(tk.Tk):
    """A small, local-first coding practice workspace."""

    def __init__(self) -> None:
        super().__init__()
        self.title("FAANGTrail | Local Practice")
        self.geometry("1280x820")
        self.minsize(980, 640)
        self.configure(bg=COLORS["editor"])

        self.challenges = load_challenges()
        self.selected_challenge: Challenge | None = None
        self.result_queue: queue.Queue[RunResult] = queue.Queue()
        self.is_running = False
        self.navigator_visible = True
        self._status_animation_id: str | None = None
        self._navigator_animation_id: str | None = None

        self._configure_styles()
        self._build_layout()
        self._load_challenge(0)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=COLORS["editor"])
        style.configure("Titlebar.TFrame", background=COLORS["activity"])
        style.configure("Sidebar.TFrame", background=COLORS["sidebar"])
        style.configure("Activity.TFrame", background=COLORS["activity"])
        style.configure("Editor.TFrame", background=COLORS["editor"])
        style.configure("Tab.TFrame", background=COLORS["editor"])
        style.configure("Title.TLabel", background=COLORS["activity"], foreground=COLORS["muted"], font=("Segoe UI", 10))
        style.configure("Brand.TLabel", background=COLORS["activity"], foreground=COLORS["blue"], font=("Segoe UI", 10, "bold"))
        style.configure("Section.TLabel", background=COLORS["sidebar"], foreground="#bbbbbb", font=("Segoe UI", 9, "bold"))
        style.configure("Panel.TLabel", background=COLORS["sidebar"], foreground=COLORS["text"], font=("Segoe UI", 11))
        style.configure("Muted.TLabel", background=COLORS["sidebar"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("EditorLabel.TLabel", background=COLORS["editor"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Tab.TLabel", background=COLORS["editor"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=COLORS["editor"], foreground=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        style.configure("Badge.TLabel", background=COLORS["input"], foreground=COLORS["blue"], font=("Segoe UI", 9, "bold"), padding=(8, 3))
        style.configure("Accent.TButton", background=COLORS["blue"], foreground=COLORS["activity"], font=("Segoe UI", 9, "bold"), padding=(12, 6), borderwidth=0)
        style.map("Accent.TButton", background=[("active", COLORS["blue_hover"]), ("disabled", "#3c3c3c")])
        style.configure("Secondary.TButton", background=COLORS["input"], foreground=COLORS["text"], font=("Segoe UI", 9), padding=(9, 6), borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#4b4b4b")])

    def _build_layout(self) -> None:
        shell = ttk.Frame(self, style="App.TFrame")
        shell.pack(fill="both", expand=True)

        titlebar = ttk.Frame(shell, style="Titlebar.TFrame", height=42)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)
        ttk.Label(titlebar, text="FAANGTrail", style="Brand.TLabel").pack(side="left", padx=16)
        ttk.Label(titlebar, text="  /  LOCAL PRACTICE", style="Title.TLabel").pack(side="left")
        ttk.Label(titlebar, text="PYTHON 3.10+", style="Title.TLabel").pack(side="right", padx=16)
        self.motion_bar = tk.Frame(shell, bg=COLORS["blue"], height=2)
        self.motion_bar.pack(fill="x")
        self.motion_bar.pack_propagate(False)

        body = ttk.Frame(shell, style="App.TFrame")
        body.pack(fill="both", expand=True)

        activity = ttk.Frame(body, style="Activity.TFrame", width=52)
        activity.pack(side="left", fill="y")
        activity.pack_propagate(False)
        tk.Label(activity, text="FT", bg=COLORS["blue"], fg=COLORS["activity"], font=("Segoe UI", 10, "bold"), pady=8).pack(fill="x", pady=(12, 16))
        tk.Label(activity, text="ROAD", bg=COLORS["activity"], fg=COLORS["text"], font=("Segoe UI", 8, "bold"), pady=8).pack(fill="x")
        tk.Label(activity, text="CODE", bg=COLORS["activity"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold"), pady=8).pack(fill="x")
        self.activity_toggle_button = tk.Button(activity, text="‹", command=self._toggle_navigator, bg=COLORS["activity"], fg=COLORS["muted"], activebackground=COLORS["input"], activeforeground=COLORS["bright"], relief="flat", bd=0, font=("Segoe UI", 16), cursor="hand2")
        self.activity_toggle_button.pack(side="bottom", fill="x", pady=10)

        self.navigator = tk.Frame(body, bg=COLORS["sidebar"], width=260, bd=0, highlightbackground=COLORS["border"], highlightthickness=1)
        navigator = self.navigator
        navigator.pack(side="left", fill="y")
        navigator.pack_propagate(False)
        explorer_header = ttk.Frame(navigator, style="Sidebar.TFrame", height=42)
        explorer_header.pack(fill="x")
        explorer_header.pack_propagate(False)
        ttk.Label(explorer_header, text="EXPLORER", style="Section.TLabel").pack(side="left", padx=14, pady=14)
        self.toggle_navigator_button = tk.Button(explorer_header, text="‹", command=self._toggle_navigator, bg=COLORS["sidebar"], fg=COLORS["muted"], activebackground=COLORS["input"], activeforeground=COLORS["bright"], relief="flat", bd=0, font=("Segoe UI", 16), cursor="hand2")
        self.toggle_navigator_button.pack(side="right", padx=8)
        roadmap_header = ttk.Frame(navigator, style="Sidebar.TFrame")
        roadmap_header.pack(fill="x", padx=10, pady=(2, 8))
        ttk.Label(roadmap_header, text="ROADMAP", style="Section.TLabel").pack(side="left")
        ttk.Label(roadmap_header, text=f"{len(self.challenges)} problems", style="Muted.TLabel").pack(side="right")
        self.challenge_list = tk.Listbox(
            navigator,
            activestyle="none",
            bg=COLORS["code_background"],
            fg=COLORS["code_text"],
            selectbackground=COLORS["selection"],
            selectforeground=COLORS["bright"],
            relief="flat",
            highlightthickness=0,
            font=("Cascadia Mono", 9),
            exportselection=False,
        )
        self.challenge_list.pack(fill="both", expand=True, padx=0)
        for challenge in self.challenges:
            self.challenge_list.insert("end", f"  {challenge.title}  ·  {challenge.difficulty}")
        self.challenge_list.bind("<<ListboxSelect>>", self._on_challenge_selected)

        self.content_panes = ttk.PanedWindow(body, orient="horizontal")
        self.content_panes.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=(12, 12))

        self.problem_pane = tk.Frame(self.content_panes, bg=COLORS["panel"], bd=0, highlightbackground=COLORS["border"], highlightthickness=1)
        self.content_panes.add(self.problem_pane, weight=2)
        problem_header = tk.Frame(self.problem_pane, bg=COLORS["panel"], height=42)
        problem_header.pack(fill="x")
        problem_header.pack_propagate(False)
        tk.Label(problem_header, text="PROBLEM", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=14)
        self.problem_text = ScrolledText(self.problem_pane, state="disabled", wrap="word", bg=COLORS["panel"], fg=COLORS["text"], insertbackground="#ffffff", selectbackground=COLORS["selection"], relief="flat", padx=18, pady=12, font=("Segoe UI", 10), spacing1=2, spacing3=4)
        self.problem_text.tag_configure("problem_title", foreground=COLORS["bright"], font=("Segoe UI", 16, "bold"), spacing3=8)
        self.problem_text.tag_configure("section", foreground=COLORS["bright"], font=("Segoe UI", 10, "bold"), spacing1=10, spacing3=4)
        self.problem_text.tag_configure("body", foreground=COLORS["text"], font=("Segoe UI", 10), spacing3=8)
        self.problem_text.tag_configure("example", foreground="#d4d4d4", background=COLORS["editor"], font=("Cascadia Mono", 9), lmargin1=8, lmargin2=8, spacing1=2, spacing3=6)
        self.problem_text.tag_configure("constraints", foreground=COLORS["code_text"], background=COLORS["code_background"], font=("Cascadia Mono", 9), lmargin1=8, lmargin2=8, spacing1=2, spacing3=6)
        self.problem_text.pack(fill="both", expand=True)

        workspace = ttk.Frame(self.content_panes, style="Editor.TFrame")
        self.content_panes.add(workspace, weight=5)

        tab = ttk.Frame(workspace, style="Tab.TFrame", height=38)
        tab.pack(fill="x")
        tab.pack_propagate(False)
        ttk.Label(tab, text="  problem.py", style="Tab.TLabel").pack(side="left", fill="y", padx=(4, 0), pady=10)
        ttk.Label(tab, text="×", style="EditorLabel.TLabel").pack(side="left", padx=8)

        editor_header = ttk.Frame(workspace, style="Editor.TFrame", padding=(14, 0, 14, 0))
        editor_header.pack(fill="x")
        self.challenge_title = ttk.Label(editor_header, style="Title.TLabel", text="")
        self.challenge_title.configure(background=COLORS["editor"], foreground=COLORS["bright"], font=("Segoe UI", 14, "bold"))
        self.challenge_title.pack(side="left")
        self.challenge_meta = ttk.Label(editor_header, style="Badge.TLabel")
        self.challenge_meta.pack(side="left", padx=(12, 0))
        self.run_button = ttk.Button(editor_header, text="Run tests", style="Accent.TButton", command=self._run_submission)
        self.run_button.pack(side="right")
        self.reset_button = ttk.Button(editor_header, text="Reset", style="Secondary.TButton", command=self._reset_code)
        self.reset_button.pack(side="right", padx=(0, 8))

        panes = ttk.PanedWindow(workspace, orient="vertical")
        panes.pack(fill="both", expand=True, padx=(0, 8), pady=(8, 12))

        editor_panel = tk.Frame(panes, bg=COLORS["code_background"], bd=0, highlightbackground=COLORS["border"], highlightthickness=1)
        self.editor = ScrolledText(editor_panel, undo=True, wrap="none", height=15, bg=COLORS["code_background"], fg=COLORS["code_text"], insertbackground="#ffffff", selectbackground=COLORS["selection"], relief="flat", padx=24, pady=12, font=("Cascadia Mono", 11))
        for tag_name, color in SYNTAX_COLORS.items():
            self.editor.tag_configure(tag_name, foreground=color)
        self.editor.bind("<KeyRelease>", self._schedule_highlight)
        self.editor.pack(fill="both", expand=True)
        panes.add(editor_panel, weight=3)

        output_header = ttk.Frame(workspace, style="Editor.TFrame", padding=(14, 0, 14, 0))
        output_header.pack(fill="x")
        ttk.Label(output_header, text="TEST RESULTS", style="EditorLabel.TLabel").pack(side="left")
        self.status = ttk.Label(output_header, text="Ready", style="EditorLabel.TLabel")
        self.status.pack(side="right")
        output_panel = tk.Frame(panes, bg=COLORS["code_background"], bd=0, highlightbackground=COLORS["border"], highlightthickness=1)
        self.output = ScrolledText(output_panel, height=8, state="disabled", wrap="word", bg=COLORS["code_background"], fg=COLORS["code_text"], relief="flat", padx=24, pady=12, font=("Cascadia Mono", 10))
        self.output.pack(fill="both", expand=True)
        panes.add(output_panel, weight=1)

        statusbar = tk.Frame(shell, bg=COLORS["activity"], height=28)
        statusbar.pack(fill="x")
        statusbar.pack_propagate(False)
        tk.Label(statusbar, text="  o  FAANGTRAIL", bg=COLORS["activity"], fg=COLORS["blue"], font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(statusbar, text="Python 3  |  LOCAL INTERPRETER  |  UTF-8  ", bg=COLORS["activity"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(side="right")

    def _on_challenge_selected(self, _event: tk.Event) -> None:
        selection = self.challenge_list.curselection()
        if selection:
            self._load_challenge(selection[0])

    def _load_challenge(self, index: int) -> None:
        self.selected_challenge = self.challenges[index]
        self.challenge_list.selection_clear(0, "end")
        self.challenge_list.selection_set(index)
        self.challenge_list.see(index)
        challenge = self.selected_challenge
        self.challenge_title.configure(text=challenge.title)
        self.challenge_meta.configure(text=f"{challenge.topic.upper()}  /  {challenge.difficulty.upper()}")
        self._render_problem(challenge)
        self._reset_code()
        self._set_output("")
        self.status.configure(text="Ready")
        self._animate_motion_bar()

    def _render_problem(self, challenge: Challenge) -> None:
        self.problem_text.configure(state="normal")
        self.problem_text.delete("1.0", "end")
        self.problem_text.insert("end", challenge.title + "\n", "problem_title")
        self.problem_text.insert("end", f"{challenge.topic.upper()}  /  {challenge.difficulty.upper()}\n\n", "body")
        self.problem_text.insert("end", "Problem\n", "section")
        self.problem_text.insert("end", challenge.prompt + "\n" + challenge.description + "\n", "body")
        self.problem_text.insert("end", "Examples\n", "section")
        self.problem_text.insert("end", challenge.examples + "\n", "example")
        self.problem_text.insert("end", "Constraints\n", "section")
        self.problem_text.insert("end", self._format_constraints(challenge.constraints), "constraints")
        self.problem_text.configure(state="disabled")

    @staticmethod
    def _format_constraints(constraints: str) -> str:
        """Make compact constraint prose easier to scan in the problem pane."""
        normalized = re.sub(r"\s*\n\s*", "\n", constraints.strip())
        normalized = re.sub(r"\.\s+(?=\S)", ".\n", normalized)
        return normalized + "\n"

    def _toggle_navigator(self) -> None:
        if self._navigator_animation_id is not None:
            return

        if self.navigator_visible:
            self.navigator_visible = False
            self.toggle_navigator_button.configure(text="›")
            self.activity_toggle_button.configure(text="›")
            self._animate_navigator(260, 0, False)
        else:
            self.navigator_visible = True
            self.navigator.pack(side="left", fill="y", before=self.content_panes)
            self.navigator.configure(width=0)
            self.toggle_navigator_button.configure(text="‹")
            self.activity_toggle_button.configure(text="‹")
            self._animate_navigator(0, 260, True)

    def _animate_navigator(self, start_width: int, end_width: int, expanding: bool) -> None:
        duration = 180
        steps = 12
        step_delay = duration // steps

        def step(step_index: int) -> None:
            progress = step_index / steps
            eased = 1 - (1 - progress) ** 3
            width = round(start_width + (end_width - start_width) * eased)
            self.navigator.configure(width=width)
            if step_index < steps:
                self._navigator_animation_id = self.after(step_delay, step, step_index + 1)
                return
            self._navigator_animation_id = None
            if not expanding:
                self.navigator.pack_forget()

        step(0)

    def _reset_code(self) -> None:
        self.editor.delete("1.0", "end")
        starter = self.selected_challenge.starter if self.selected_challenge else STARTER_CODE
        self.editor.insert("1.0", starter)
        self._highlight_editor()

    def _schedule_highlight(self, _event: tk.Event) -> None:
        self.after_idle(self._highlight_editor)

    def _animate_motion_bar(self) -> None:
        colors = [COLORS["blue"], COLORS["bright"], COLORS["coral"], COLORS["blue"]]

        def step(index: int) -> None:
            if index >= len(colors):
                return
            self.motion_bar.configure(bg=colors[index])
            self.after(75, step, index + 1)

        step(0)

    def _animate_status(self) -> None:
        if not self.is_running:
            self._status_animation_id = None
            return
        current = self.status.cget("foreground")
        next_color = COLORS["bright"] if current == COLORS["blue"] else COLORS["blue"]
        self.status.configure(foreground=next_color)
        self._status_animation_id = self.after(420, self._animate_status)

    def _stop_status_animation(self) -> None:
        if self._status_animation_id is not None:
            self.after_cancel(self._status_animation_id)
            self._status_animation_id = None
        self.status.configure(foreground=COLORS["muted"])

    def _highlight_editor(self) -> None:
        source = self.editor.get("1.0", "end-1c")
        for tag_name in SYNTAX_COLORS:
            self.editor.tag_remove(tag_name, "1.0", "end")

        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        except (IndentationError, tokenize.TokenError):
            return

        significant_tokens = [item for item in tokens if item.type not in {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE}]
        for token_index, current_token in enumerate(significant_tokens):
            tag_name = self._syntax_tag(current_token, significant_tokens, token_index)
            if tag_name:
                start = f"{current_token.start[0]}.{current_token.start[1]}"
                end = f"{current_token.end[0]}.{current_token.end[1]}"
                self.editor.tag_add(tag_name, start, end)

    @staticmethod
    def _syntax_tag(current_token: tokenize.TokenInfo, tokens: list[tokenize.TokenInfo], token_index: int) -> str | None:
        if current_token.type == tokenize.COMMENT:
            return "comment"
        if current_token.type == tokenize.STRING:
            return "string"
        if current_token.type == tokenize.NUMBER:
            return "number"
        if current_token.type == tokenize.OP:
            return "operator"
        if current_token.type == tokenize.NAME:
            previous_value = tokens[token_index - 1].string if token_index else ""
            next_value = tokens[token_index + 1].string if token_index + 1 < len(tokens) else ""
            if previous_value == "def":
                return "function"
            if previous_value == "class":
                return "class"
            if current_token.string in dir(builtins):
                return "builtin"
            if next_value == "(":
                return "function"
            return "variable"
        if current_token.type == tokenize.ERRORTOKEN and current_token.string.strip():
            return "operator"
        return None

    def _run_submission(self) -> None:
        if self.is_running:
            return
        source = self.editor.get("1.0", "end-1c")
        self.is_running = True
        self.run_button.configure(state="disabled", text="Running...")
        self.status.configure(text="Running locally...")
        self._animate_status()
        self._set_output("")
        threading.Thread(target=self._run_in_background, args=(source, self.selected_challenge.tests), daemon=True).start()
        self.after(100, self._poll_result)

    def _run_in_background(self, source: str, tests: str) -> None:
        self.result_queue.put(run_python(source, test_source=tests))

    def _poll_result(self) -> None:
        try:
            result = self.result_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_result)
            return
        self._finish_run(result)

    def _finish_run(self, result: RunResult) -> None:
        self.is_running = False
        self._stop_status_animation()
        self.run_button.configure(state="normal", text="Run tests")
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        self._set_output(output or "No output.")
        self.status.configure(text="Passed" if result.returncode == 0 else "Failed")

    def _set_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")


def main() -> None:
    try:
        app = PracticeApp()
        app.mainloop()
    except tk.TclError as error:
        messagebox.showerror("FAANGTrail", f"Unable to start the desktop app:\n{error}")