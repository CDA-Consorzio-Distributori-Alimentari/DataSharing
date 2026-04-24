import tkinter as tk
from tkinter import ttk
from .data_sharing_windows_app import DataSharingWindowsApp
from .data_sharing_windowsstrategy_app import DataSharingWindowsStrategyApp


def main_selector_window():
    root = tk.Tk()
    root.title("Seleziona modalità DataSharing")
    root.geometry("520x520")
    root.resizable(False, False)

    style = ttk.Style()
    style.theme_use("clam")

    frame = ttk.Frame(root, padding=16, style="Selector.TFrame")
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
        try:
            app.run()
        finally:
            main_selector_window()

    def open_socio_period_ds():
        root.destroy()
        from .datasharing_socio_management_window import DataSharingSocioManagementWindow
        # Crea una finestra temporanea solo per la maschera, poi riapre il selettore
        class DummyApp:
            def __init__(self):
                self.root = tk.Tk()
                self.backend = DataSharingWindowsApp().backend
        dummy = DummyApp()
        DataSharingSocioManagementWindow(dummy)
        dummy.root.mainloop()
        main_selector_window()

    def open_strategy():
        root.destroy()
        app = DataSharingWindowsStrategyApp()
        try:
            app.run()
        finally:
            main_selector_window()

    # Migliora visibilità pulsanti
    style.configure("Selector.TButton", font=("Segoe UI", 12, "bold"), padding=10, relief="raised", background="#e6f2ff")
    style.map("Selector.TButton",
              background=[("active", "#cce0ff")],
              relief=[("pressed", "sunken"), ("!pressed", "raised")])


    def open_help():
        help_win = tk.Toplevel(root)
        help_win.title("Manuale Utente DataSharing")
        help_win.geometry("800x800")
        help_win.minsize(600, 400)
        text = tk.Text(help_win, wrap="word", font=("Segoe UI", 11))
        text.pack(expand=True, fill="both")
        scroll = ttk.Scrollbar(help_win, orient="vertical", command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)
        try:
            with open("GUIDA_UTENTE_DATASHARING.md", "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            content = f"Errore apertura manuale: {exc}"
        text.insert("1.0", content)
        text.configure(state="disabled")


    btn_standard = ttk.Button(frame, text="DataSharing Standard Datasharing → Soci", command=open_standard, width=38, style="Selector.TButton")
    btn_standard.pack(pady=(0, 14), fill="x")

    btn_socio_period_ds = ttk.Button(frame, text="DataSharing Standard Soci → Datasharing", command=open_socio_period_ds, width=38, style="Selector.TButton")
    btn_socio_period_ds.pack(pady=(0, 14), fill="x")

    btn_strategy = ttk.Button(frame, text="DataSharing Strategy", command=open_strategy, width=38, style="Selector.TButton")
    btn_strategy.pack(pady=(0, 8), fill="x")

    btn_help = ttk.Button(frame, text="Help / Manuale Utente", command=open_help, width=38, style="Selector.TButton")
    btn_help.pack(pady=(0, 8), fill="x")

    btn_close = ttk.Button(frame, text="Chiudi", command=root.destroy, width=38, style="Selector.TButton")
    btn_close.pack(pady=(8, 0), fill="x")

    root.mainloop()

if __name__ == "__main__":
    main_selector_window()
