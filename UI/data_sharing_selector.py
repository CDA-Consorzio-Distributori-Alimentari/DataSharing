import tkinter as tk
from tkinter import ttk
from .data_sharing_windows_app import DataSharingWindowsApp
from .data_sharing_windowsstrategy_app import DataSharingWindowsStrategyApp


def main_selector_window():
    root = tk.Tk()
    root.title("Seleziona modalità DataSharing")
    root.geometry("400x360")
    root.resizable(False, False)

    style = ttk.Style()
    style.theme_use("clam")

    frame = ttk.Frame(root, padding=32, style="Selector.TFrame")
    frame.pack(expand=True, fill="both")

    label = ttk.Label(frame, text="Scegli la modalità di avvio:", font=("Segoe UI", 14, "bold"), style="Selector.TLabel")
    label.pack(pady=(0, 28))

    # Selettore ambiente
    env_var = tk.StringVar(value="Produzione")
    env_frame = ttk.Frame(frame)
    env_frame.pack(pady=(0, 18))
    ttk.Label(env_frame, text="Ambiente:", font=("Segoe UI", 11)).pack(side="left", padx=(0, 8))
    env_combo = ttk.Combobox(env_frame, textvariable=env_var, state="readonly", width=14)
    env_combo['values'] = ("Produzione", "Sviluppo")
    env_combo.pack(side="left")

    def open_standard():
        root.destroy()
        app = DataSharingWindowsApp()
        app.run()

    def open_strategy():
        root.destroy()
        app = DataSharingWindowsStrategyApp()
        app.run()

    # Migliora visibilità pulsanti
    style.configure("Selector.TButton", font=("Segoe UI", 12, "bold"), padding=10, relief="raised", background="#e6f2ff")
    style.map("Selector.TButton",
              background=[("active", "#cce0ff")],
              relief=[("pressed", "sunken"), ("!pressed", "raised")])

    btn_standard = ttk.Button(frame, text="DataSharing Standard", command=open_standard, width=28, style="Selector.TButton")
    btn_standard.pack(pady=(0, 14))

    btn_strategy = ttk.Button(frame, text="DataSharing Strategy", command=open_strategy, width=28, style="Selector.TButton")
    btn_strategy.pack(pady=(0, 8))

    root.mainloop()

if __name__ == "__main__":
    main_selector_window()
