import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from database.repositories import tabella_logging_repository

class TabellaLoggingWindows:
    COLUMNS = [
        ("cod_socio", "Socio"),
        ("cod_datasharing", "DataSharing"),
        ("num_periodo", "Periodo"),
        ("tms_invio", "Invio"),
        ("nom_file", "Nome File"),
        ("cod_stato", "Stato"),
        ("des_errore", "Errore"),
        ("tms_update", "Aggiornamento"),
        ("nom_utente_operazione", "Utente"),
        ("nom_host_operazione", "Host"),
    ]

    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.backend = parent_app.backend
        
       
        self.window = tk.Toplevel(parent_app.root)
        self.window.title("Log DataSharing - TX_DATASHARING_SOCIO")
        self.window.geometry("1200x600")
        self.window.minsize(900, 400)
        self.window.transient(parent_app.root)

        self.socio_filter_var = tk.StringVar()
        self.datasharing_filter_var = tk.StringVar()
        self.anno_filter_var = tk.StringVar()
        self.mese_filter_var = tk.StringVar()
        self.cod_stato_filter_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Caricamento log...")

        try:

            self._build_ui()
            self._load_filters()
            self._load_data()
        except Exception as exc:
            
            messagebox.showerror("Errore", f"Errore durante l'inizializzazione:\n{exc}", parent=parent_app.root)
            self.window.destroy()
            raise

    def _build_ui(self):
        filter_frame = ttk.LabelFrame(self.window, text="Filtri", padding=10)
        filter_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(filter_frame, text="Socio").grid(row=0, column=0, sticky="w", padx=5)
        self.socio_combo = ttk.Combobox(filter_frame, textvariable=self.socio_filter_var, state="readonly")
        self.socio_combo.grid(row=0, column=1, padx=5)
        self.socio_combo.bind("<<ComboboxSelected>>", lambda e: self._load_data())

        ttk.Label(filter_frame, text="DataSharing").grid(row=0, column=2, sticky="w", padx=5)
        self.datasharing_combo = ttk.Combobox(filter_frame, textvariable=self.datasharing_filter_var, state="readonly")
        self.datasharing_combo.grid(row=0, column=3, padx=5)
        self.datasharing_combo.bind("<<ComboboxSelected>>", lambda e: self._load_data())

        ttk.Label(filter_frame, text="Anno").grid(row=0, column=4, sticky="w", padx=5)
        self.anno_entry = ttk.Entry(filter_frame, textvariable=self.anno_filter_var, width=6)
        self.anno_entry.grid(row=0, column=5, padx=5)
        self.anno_entry.bind("<KeyRelease>", lambda e: self._load_data())

        ttk.Label(filter_frame, text="Mese").grid(row=0, column=6, sticky="w", padx=5)
        self.mese_combo = ttk.Combobox(filter_frame, textvariable=self.mese_filter_var, state="readonly", width=4)
        self.mese_combo['values'] = ["", *(f"{i:02d}" for i in range(1, 13))]
        self.mese_combo.grid(row=0, column=7, padx=5)
        self.mese_combo.bind("<<ComboboxSelected>>", lambda e: self._load_data())

        ttk.Label(filter_frame, text="Stato").grid(row=0, column=8, sticky="w", padx=5)
        self.cod_stato_combo = ttk.Combobox(filter_frame, textvariable=self.cod_stato_filter_var, state="readonly")
        self.cod_stato_combo.grid(row=0, column=9, padx=5)
        self.cod_stato_combo.bind("<<ComboboxSelected>>", lambda e: self._load_data())

        self.status_label = ttk.Label(self.window, textvariable=self.status_var)
        self.status_label.pack(anchor="w", padx=10, pady=(0, 5))

        self.tree = ttk.Treeview(self.window, columns=[c[0] for c in self.COLUMNS], show="headings")
        for col, label in self.COLUMNS:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree_scroll = ttk.Scrollbar(self.window, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.pack(side="right", fill="y")

    def _load_filters(self):
        # Recupera tutti i valori unici per i filtri tramite TabellaLoggingRepository
        df = self.backend.get_logging_dataframe()
        if df is not None and not df.empty:
            soci = sorted(set(df["COD_SOCIO"].dropna().astype(str)))
            datasharings = sorted(set(df["COD_DATASHARING"].dropna().astype(str)))
            stati = sorted(set(df["COD_STATO"].dropna().astype(str)))
        else:
            soci = []
            datasharings = []
            stati = []
        self.socio_combo['values'] = ["", *soci]
        self.datasharing_combo['values'] = ["", *datasharings]
        self.cod_stato_combo['values'] = ["", *stati]

    def _load_data(self):
        # Costruisci i filtri
        cod_socio = self.socio_filter_var.get() or None
        cod_datasharing = self.datasharing_filter_var.get() or None
        num_periodo = None
        if self.anno_filter_var.get():
            anno = self.anno_filter_var.get()
            if self.mese_filter_var.get():
                num_periodo = f"{anno}{self.mese_filter_var.get()}"
        cod_stato = self.cod_stato_filter_var.get() or None

        # Recupera il DataFrame filtrato tramite TabellaLoggingRepository
        df = self.backend.get_logging_dataframe(
            cod_socio=cod_socio,
            cod_datasharing=cod_datasharing,
            num_periodo=num_periodo,
            cod_stato=cod_stato
        )

        self.tree.delete(*self.tree.get_children())
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                values = [row.get(col.upper(), "") for col, _ in self.COLUMNS]
                self.tree.insert("", "end", values=values)
            self.status_var.set(f"Righe trovate: {len(df)}")
        else:
            self.status_var.set("Nessun dato trovato")
