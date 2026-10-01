"""Shared look & feel helpers: colours, ttk table styling, a tiny bar chart."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

LIFECYCLE_COLORS = {
    "Plan": "#6c8ebf", "Phase In": "#4a9fb5", "Active": "#2e8b57",
    "Phase Out": "#e0a030", "End of Life": "#c0392b", "(not set)": "#8a8a8a",
}
SCALE = ["#4a9fb5", "#2e8b57", "#e0a030", "#c0392b", "#7d5ba6", "#8a8a8a"]
LAYER_COLORS = {"Business": "#c47f17", "Data": "#7d5ba6", "Application": "#1f6aa5", "Technology": "#2e8b57"}


def is_dark() -> bool:
    return ctk.get_appearance_mode() == "Dark"


def palette() -> dict:
    if is_dark():
        return dict(bg="#2b2b2b", fg="#dce4ee", muted="#9aa5b1", head="#3a3a3a",
                    card="#333333", grid="#444444")
    return dict(bg="#ffffff", fg="#1a1a1a", muted="#5f6b7a", head="#e5e5e5",
                card="#f0f2f5", grid="#d0d4d9")


def style_tables() -> None:
    p = palette()
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("Treeview", background=p["bg"], foreground=p["fg"], fieldbackground=p["bg"],
                rowheight=27, borderwidth=0, font=("Segoe UI", 10))
    s.map("Treeview", background=[("selected", "#1f6aa5")], foreground=[("selected", "white")])
    s.configure("Treeview.Heading", background=p["head"], foreground=p["fg"], relief="flat",
                font=("Segoe UI", 10, "bold"))
    s.map("Treeview.Heading", background=[("active", p["grid"])])


class BarChart(ctk.CTkFrame):
    """Horizontal bar chart on a canvas; redraws itself when resized or re-themed."""

    def __init__(self, master, title: str, **kw):
        super().__init__(master, **kw)
        self._title = title
        self._items: list[tuple[str, int, str]] = []
        self.canvas = tk.Canvas(self, height=40, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda _e: self.redraw())

    def set_data(self, items: list[tuple[str, int, str]]):
        self._items = items
        self.canvas.configure(height=36 + 26 * max(len(items), 1))
        self.redraw()

    def redraw(self):
        c, p = self.canvas, palette()
        c.delete("all")
        c.configure(bg=self._fg_color_for_canvas())
        w = max(c.winfo_width(), 200)
        c.create_text(4, 12, text=self._title, anchor="w", fill=p["fg"], font=("Segoe UI", 11, "bold"))
        total = sum(v for _, v, _ in self._items)
        if not total:
            c.create_text(4, 40, text="No data yet", anchor="w", fill=p["muted"])
            return
        top = max(v for _, v, _ in self._items)
        label_w, num_w = 150, 34
        bar_max = max(w - label_w - num_w - 16, 40)
        y = 34
        for label, value, color in self._items:
            c.create_text(4, y + 9, text=label, anchor="w", fill=p["fg"], font=("Segoe UI", 9))
            length = 0 if not value else max(3, int(bar_max * value / top))
            c.create_rectangle(label_w, y, label_w + length, y + 18, fill=color, width=0)
            c.create_text(label_w + length + 6, y + 9, text=str(value), anchor="w", fill=p["fg"],
                          font=("Segoe UI", 9, "bold"))
            y += 26

    def _fg_color_for_canvas(self) -> str:
        return palette()["card"]
