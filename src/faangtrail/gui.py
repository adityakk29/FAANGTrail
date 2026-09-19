"""Desktop interface for practicing roadmap challenges locally."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .roadmap import Challenge, load_challenges
from .runner import RunResult, run_python


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
        self.geometry("1180x760")
        self.minsize(900, 600)
        self.configure(bg="#111827")

        self.challenges = load_challenges()
        self.selected_challenge: Challenge | None = None
        self.result_queue: queue.Queue[RunResult] = queue.Queue()
        self.is_running = False

        self._configure_styles()
        self._build_layout()
        self._load_challenge(0)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#111827")
        style.configure("Panel.TFrame", background="#1f2937")
        style.configure("Title.TLabel", background="#111827", foreground="#f9fafb", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background="#111827", foreground="#9ca3af", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background="#1f2937", foreground="#f9fafb", font=("Segoe UI", 11))
        style.configure("Muted.TLabel", background="#1f2937", foreground="#9ca3af", font=("Segoe UI", 10))
        style.configure("Accent.TButton", background="#f59e0b", foreground="#111827", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.map("Accent.TButton", background=[("active", "#fbbf24"), ("disabled", "#6b7280")])
        style.configure("Secondary.TButton", background="#374151", foreground="#f9fafb", padding=(10, 7))
        style.map("Secondary.TButton", background=[("active", "#4b5563")])

    def _build_layout(self) -> None:
        shell = ttk.Frame(self, style="App.TFrame", padding=24)
        shell.pack(fill="both", expand=True)

        header = ttk.Frame(shell, style="App.TFrame")
        header.pack(fill="x", pady=(0, 20))
        ttk.Label(header, text="FAANGTrail", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Practice the roadmap locally. Your code stays on this machine.", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        body = ttk.PanedWindow(shell, orient="horizontal")
        body.pack(fill="both", expand=True)

        navigator = ttk.Frame(body, style="Panel.TFrame", padding=16)
        body.add(navigator, weight=1)
        ttk.Label(navigator, text="ROADMAP", style="Muted.TLabel").pack(anchor="w")
        self.challenge_list = tk.Listbox(
            navigator,
            activestyle="none",
            bg="#1f2937",
            fg="#e5e7eb",
            selectbackground="#f59e0b",
            selectforeground="#111827",
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 11),
            exportselection=False,
        )
        self.challenge_list.pack(fill="both", expand=True, pady=(10, 0))
        for challenge in self.challenges:
            self.challenge_list.insert("end", f"{challenge.title}  ·  {challenge.difficulty}")
        self.challenge_list.bind("<<ListboxSelect>>", self._on_challenge_selected)

        workspace = ttk.Frame(body, style="App.TFrame", padding=(18, 0, 0, 0))
        body.add(workspace, weight=4)

        details = ttk.Frame(workspace, style="Panel.TFrame", padding=16)
        details.pack(fill="x", pady=(0, 14))
        self.challenge_title = ttk.Label(details, style="Panel.TLabel")
        self.challenge_title.pack(anchor="w")
        self.challenge_meta = ttk.Label(details, style="Muted.TLabel")
        self.challenge_meta.pack(anchor="w", pady=(5, 0))
        self.challenge_prompt = ttk.Label(details, style="Panel.TLabel", wraplength=700, justify="left")
        self.challenge_prompt.pack(anchor="w", pady=(12, 0))

        editor_header = ttk.Frame(workspace, style="App.TFrame")
        editor_header.pack(fill="x")
        ttk.Label(editor_header, text="YOUR PYTHON SOLUTION", style="Subtitle.TLabel").pack(side="left")
        self.run_button = ttk.Button(editor_header, text="Run tests", style="Accent.TButton", command=self._run_submission)
        self.run_button.pack(side="right")
        self.reset_button = ttk.Button(editor_header, text="Reset", style="Secondary.TButton", command=self._reset_code)
        self.reset_button.pack(side="right", padx=(0, 8))

        self.editor = ScrolledText(workspace, undo=True, wrap="none", height=15, bg="#0b1220", fg="#e5e7eb", insertbackground="#f59e0b", relief="flat", padx=14, pady=12, font=("Cascadia Mono", 11))
        self.editor.pack(fill="both", expand=True, pady=(8, 14))

        output_header = ttk.Frame(workspace, style="App.TFrame")
        output_header.pack(fill="x")
        ttk.Label(output_header, text="OUTPUT", style="Subtitle.TLabel").pack(side="left")
        self.status = ttk.Label(output_header, text="Ready", style="Subtitle.TLabel")
        self.status.pack(side="right")
        self.output = ScrolledText(workspace, height=8, state="disabled", wrap="word", bg="#0b1220", fg="#d1d5db", relief="flat", padx=14, pady=12, font=("Cascadia Mono", 10))
        self.output.pack(fill="both", expand=True, pady=(8, 0))

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
        self.challenge_prompt.configure(text=challenge.prompt)
        self._reset_code()
        self._set_output("")
        self.status.configure(text="Ready")

    def _reset_code(self) -> None:
        self.editor.delete("1.0", "end")
        starter = self.selected_challenge.starter if self.selected_challenge else STARTER_CODE
        self.editor.insert("1.0", starter)

    def _run_submission(self) -> None:
        if self.is_running:
            return
        source = self.editor.get("1.0", "end-1c")
        self.is_running = True
        self.run_button.configure(state="disabled", text="Running...")
        self.status.configure(text="Running locally...")
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