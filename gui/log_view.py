import time
import tkinter as tk
from tkinter import scrolledtext, ttk


def time_text():
    return time.strftime("%H:%M:%S")


class LogView:
    def __init__(self, parent):
        self.log_text = scrolledtext.ScrolledText(parent, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)
        ttk.Button(parent, text="Clear", command=self.clear).pack(
            anchor="e", pady=(8, 0)
        )

    def append(self, message):
        stamp = time_text()
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{stamp} {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
