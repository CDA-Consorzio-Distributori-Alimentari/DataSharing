import tkinter as tk




class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None

        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tip_window or not self.text:
            return

        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

        self.tip_window = tip_window = tk.Toplevel(self.widget)
        tip_window.wm_overrideredirect(True)
        tip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tip_window,
            text=self.text,
            justify="left",
            background="#fff8dc",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=4,
        )
        label.pack()

    def _hide(self, event=None):
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None

