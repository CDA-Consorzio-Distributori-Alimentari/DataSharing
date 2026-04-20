import tkinter as tk
from tkinter import ttk, messagebox
import math
import json
from services.data_sharing_runtime import DataSharingRuntime

import threading
from datetime import datetime
from .tool_tip import ToolTip

from .tabella_logging_windows import TabellaLoggingWindows
from managers.data_sharing_strategy_manager import DataSharingStrategyManager
from services.data_sharing_runtime import DataSharingRuntime
from database.repositories.sottoscrizioni_rpt_repository import SottoscrizioniRptRepository
from database.repositories.td_rpt_socio_periodo_repository import TdRptSocioPeriodoRepository
import time
from services.mstr_jobs import list_jobs, JobType
from managers.data_sharing_strategy_manager import SubscriptionType, SubscriptionStage, SubscriptionState

class DataSharingWindowsStrategyApp:
        
    def __init__(self, strategy_env=None):
        try:
            self.root = tk.Tk()  # Deve essere creato PRIMA di ogni StringVar
            self.backend_runtime = DataSharingRuntime()
            self.strategy_env_var = tk.StringVar(value=strategy_env or "Produzione")
            # Usa solo DataSharingStrategyManager come orchestratore
            self.strategy_manager = DataSharingStrategyManager(
                db_utils=self.backend_runtime.dso_manager.db_manager,
                myLogger=self.backend_runtime.dso_manager.log,
                strategy_env=self.strategy_env_var.get()
            )
            self.root.title(f"DataSharing {self.backend_runtime.config.version} [{self.strategy_env_var.get()}]")
            self.root.geometry("1120x760")
            self.root.minsize(960, 680)
            self.style = ttk.Style()
            self.normal_background = self.style.lookup("TFrame", "background") or "#f0f0f0"
            self.debug_background = "#fff7cc"

            self.selected_option = None
            self.is_processing = False

            self.datasharing_var = tk.StringVar()
            self.period_type_var = tk.StringVar(value="year")
            self.period_value_var = tk.StringVar()
            self.status_var = tk.StringVar(value="Seleziona un data sharing per iniziare.")
            self.release_var = tk.StringVar(value=f"Release {self.backend_runtime.config.version}")
            self.debug_var = tk.BooleanVar(value=bool(self.backend_runtime.config.debug))
            self.summary_mail_var = tk.BooleanVar(value=bool(self.backend_runtime.config.summary_mail_enabled))
            self.progress_var = tk.DoubleVar(value=0)
            self.progress_text_var = tk.StringVar(value="0%")
            self._period_validation_in_progress = False
            self._last_period_error = ""
            self._last_run_started_at = None
            self.management_window = None

            self._configure_styles()
            self._build_ui()
            self._load_datasharing_options()
            self._apply_debug_theme()
        except Exception as exc:
            messagebox.showerror("Errore all'avvio", f"Si è verificato un errore durante l'avvio dell'applicazione: {exc}")
            self.root.destroy()
            raise

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(5, weight=1)

        # Combo per ambiente strategy
        env_frame = ttk.Frame(container)
        env_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(env_frame, text="Ambiente Strategy:", font=("Segoe UI", 11)).pack(side="left", padx=(0, 8))
        env_combo = ttk.Combobox(env_frame, textvariable=self.strategy_env_var, state="readonly", width=14)
        env_combo['values'] = ("Produzione", "Sviluppo")
        env_combo.pack(side="left")
        env_combo.bind("<<ComboboxSelected>>", self._on_strategy_env_changed)

        header_frame = ttk.Frame(container)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header_frame.columnconfigure(0, weight=1)

        header = ttk.Label(
            header_frame,
            text="SottoScrizione DataSharing - CDA",
            font=("Segoe UI", 16, "bold"),
        )
        header.grid(row=0, column=0, sticky="w")

        header_right_frame = ttk.Frame(header_frame)
        header_right_frame.grid(row=0, column=1, sticky="e")

        self.debug_checkbutton = ttk.Checkbutton(
            header_right_frame,
            text="DEBUG",
            variable=self.debug_var,
            command=self._on_debug_toggled,
        )
        self.debug_checkbutton.pack(side="right")
        ToolTip(self.debug_checkbutton, "Aggiorna il flag DEBUG nel config.json e colora la finestra in giallino quando attivo.")

        self.summary_mail_checkbutton = ttk.Checkbutton(
            header_right_frame,
            text="MAIL RECAP",
            variable=self.summary_mail_var,
            command=self._on_summary_mail_toggled,
        )
        self.summary_mail_checkbutton.pack(side="right", padx=(0, 12))
        ToolTip(
            self.summary_mail_checkbutton,
            "Abilita o disabilita la mail di ricapitolazione verso dwh@cdaweb.it. Di default resta disattiva.",
        )

        release_label = ttk.Label(
            header_right_frame,
            textvariable=self.release_var,
            font=("Segoe UI", 10, "italic"),
        )
        release_label.pack(side="right", padx=(0, 12))

        selection_frame = ttk.LabelFrame(container, text="Parametri elaborazione", padding=12)
        selection_frame.grid(row=1, column=0, sticky="nsew")
        selection_frame.columnconfigure(1, weight=1)

        ttk.Label(selection_frame, text="Data sharing").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        self.datasharing_combo = ttk.Combobox(
            selection_frame,
            textvariable=self.datasharing_var,
            state="readonly",
        )
        self.datasharing_combo.grid(row=0, column=1, sticky="ew", pady=6)
        self.datasharing_combo.bind("<<ComboboxSelected>>", self._on_datasharing_changed)
        ToolTip(self.datasharing_combo, "Scegli il data sharing. I Datasharing abilitati vengono caricati automaticamente.")

        ttk.Label(selection_frame, text="Tipo periodo").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        period_type_frame = ttk.Frame(selection_frame)
        period_type_frame.grid(row=1, column=1, sticky="w", pady=6)

        ttk.Radiobutton(
            period_type_frame,
            text="Anno (YYYY)",
            variable=self.period_type_var,
            value="year",
            command=self._on_period_type_changed,
        ).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(
            period_type_frame,
            text="Periodo (YYYYMM)",
            variable=self.period_type_var,
            value="month",
            command=self._on_period_type_changed,
        ).pack(side="left")
        ToolTip(period_type_frame, "Scegli se elaborare un anno intero oppure un singolo periodo mensile.")

        ttk.Label(selection_frame, text="Valore periodo").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=6)
        self.period_entry = ttk.Entry(selection_frame, textvariable=self.period_value_var)
        self.period_entry.grid(row=2, column=1, sticky="ew", pady=6)
        period_validate_command = (self.root.register(self._validate_period_on_focus_out), "%P")
        period_invalid_command = (self.root.register(self._handle_invalid_period_focus_out),)
        self.period_entry.configure(
            validate="focusout",
            validatecommand=period_validate_command,
            invalidcommand=period_invalid_command,
        )
        self.period_entry.bind("<KeyRelease>", self._on_period_value_changed)
        ToolTip(self.period_entry, "Inserisci YYYY per un anno oppure YYYYMM per un mese, in base alla selezione sopra.")

        self.period_hint_label = ttk.Label(selection_frame, text="Inserisci un anno nel formato YYYY")
        self.period_hint_label.grid(row=3, column=1, sticky="w", pady=(0, 6))

        action_frame = ttk.Frame(container, padding=(0, 12, 0, 12))
        action_frame.grid(row=2, column=0, sticky="ew")

        self.run_button = ttk.Button(
            action_frame, 
            text="Esegui Sottoscrizione", 
            #command=self._run_export
            command=self._execute_sottoscrizione_button_handler
        )
        self.run_button.pack(side="left")
        ToolTip(self.run_button, "Si abilita solo quando data sharing, periodo e almeno un Datasharingo sono validi.")

        # Pulsante per salvare in TD_RPT_SOCIO_PERIODO con cod_stato='INS'
        self.save_tdrpt_button = ttk.Button(
            action_frame,
            text="Salva TD_RPT_SOCIO_PERIODO (INS)",
            command=self._save_tdrpt_socio_periodo_ins
        )
        self.save_tdrpt_button.pack(side="left", padx=(8, 0))
        ToolTip(self.save_tdrpt_button, "Salva una riga in TD_RPT_SOCIO_PERIODO con stato INS per il periodo e data sharing selezionati.")

        self.manage_relations_button = ttk.Button(
            action_frame,
            text="Gestione abilitazioni",
            command=self._open_Datasharing_datasharing_management,
        )
        self.tabella_logging_button = ttk.Button(
            action_frame,
            text="Visualizza Tabella Logging",
            command=self._open_tabella_logging_window,
        )
        self.tabella_logging_button.configure(state="disabled")
        self.manage_relations_button.configure(state="disabled")
        self.manage_relations_button.pack(side="left", padx=(8, 0))
        self.tabella_logging_button.pack(side="left", padx=(8, 0))
        ToolTip(
            self.manage_relations_button,
            "Apre la finestra di gestione delle relazioni Datasharing-data sharing per attivare o disattivare le abilitazioni.",
        )
        ToolTip(
            self.tabella_logging_button,
            "Apre la finestra della tabella di logging per visualizzare i dettagli delle elaborazioni.",
        )

        # Pulsante per eseguire execute_sottoscrizione
        # self.execute_sottoscrizione_button = ttk.Button(
        #     action_frame,
        #     text="Esegui Sottoscrizione",
        #     command=self._execute_sottoscrizione_button_handler
        # )
        # self.execute_sottoscrizione_button.pack(side="left", padx=(8, 0))
        # ToolTip(self.execute_sottoscrizione_button, "Esegue la sottoscrizione per i parametri selezionati.")
        # self.execute_sottoscrizione_button.configure(state="disabled")
   
        status_frame = ttk.LabelFrame(container, text="Stato", padding=12)
        status_frame.grid(row=3, column=0, sticky="ew")
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor="w")

        progress_frame = ttk.Frame(container)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=(4, 8))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            variable=self.progress_var,
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_text_var, width=8, anchor="e")
        self.progress_label.grid(row=0, column=1, padx=(8, 0))

        output_frame = ttk.LabelFrame(container, text="Esito elaborazione", padding=12)
        output_frame.grid(row=5, column=0, sticky="nsew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(output_frame, wrap="word", height=10, state="disabled")
        self.output_text.grid(row=0, column=0, sticky="nsew")

        output_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        output_scroll.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=output_scroll.set)

        # Add a Listbox for MSTR job status output
        mstr_status_frame = ttk.LabelFrame(container, text="Stato coda MSTR", padding=12)
        mstr_status_frame.grid(row=6, column=0, sticky="nsew")
        mstr_status_frame.columnconfigure(0, weight=1)
        mstr_status_frame.rowconfigure(0, weight=1)

        self.mstr_status_listbox = tk.Listbox(mstr_status_frame, height=8)
        self.mstr_status_listbox.grid(row=0, column=0, sticky="nsew")
        mstr_status_scroll = ttk.Scrollbar(mstr_status_frame, orient="vertical", command=self.mstr_status_listbox.yview)
        mstr_status_scroll.grid(row=0, column=1, sticky="ns")
        self.mstr_status_listbox.configure(yscrollcommand=mstr_status_scroll.set)

        self._on_period_type_changed()
        self._render_entity_checkboxes([])
        self._update_run_button_state()

    # Remove duplicate/erroneous code after _save_tdrpt_socio_periodo_ins
        # Aggiorna il manager e il titolo finestra
        self.strategy_manager.strategy_env = self.strategy_env_var.get()
        self.root.title(f"DataSharing {self.backend_runtime.config.version} [{self.strategy_env_var.get()}]")
        self.root = tk.Tk()
        self.root.title(f"DataSharing {self.backend_runtime.config.version}")
        self.root.geometry("1120x760")
        self.root.minsize(960, 680)
        self.style = ttk.Style()
        self.normal_background = self.style.lookup("TFrame", "background") or "#f0f0f0"
        self.debug_background = "#fff7cc"

        self.selected_option = None
        self.is_processing = False

        self.datasharing_var = tk.StringVar()
        self.period_type_var = tk.StringVar(value="year")
        self.period_value_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Seleziona un data sharing per iniziare.")
        self.release_var = tk.StringVar(value=f"Release {self.backend_runtime.config.version}")
        self.debug_var = tk.BooleanVar(value=bool(self.backend_runtime.config.debug))
        self.summary_mail_var = tk.BooleanVar(value=bool(self.backend_runtime.config.summary_mail_enabled))
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text_var = tk.StringVar(value="0%")
        self._period_validation_in_progress = False
        self._last_period_error = ""
        self._last_run_started_at = None
        self.management_window = None

        self._configure_styles()
        self._build_ui()
        self._load_datasharing_options()
        self._apply_debug_theme()

    def _configure_styles(self):
        self.style.configure("TFrame", background=self.normal_background)
        self.style.configure("TLabelframe", background=self.normal_background)
        self.style.configure("TLabelframe.Label", background=self.normal_background)
        self.style.configure("TLabel", background=self.normal_background)
        self.style.configure("TCheckbutton", background=self.normal_background)
        self.style.configure("TRadiobutton", background=self.normal_background)
        self.style.configure("Red.TButton", background="#ff4d4d", foreground="white")
    

    def _apply_debug_theme(self):
        background = self.debug_background if self.debug_var.get() else self.normal_background
        self.root.configure(bg=background)
        self.style.configure("TFrame", background=background)
        self.style.configure("TLabelframe", background=background)
        self.style.configure("TLabelframe.Label", background=background)
        self.style.configure("TLabel", background=background)
        self.style.configure("TCheckbutton", background=background)
        self.style.configure("TRadiobutton", background=background)

        # if hasattr(self, "soci_canvas"):
        #     self.soci_canvas.configure(background=background)

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(5, weight=1)

        header_frame = ttk.Frame(container)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header_frame.columnconfigure(0, weight=1)

        header = ttk.Label(
            header_frame,
            text="SottoScrizione DataSharing - CDA",
            font=("Segoe UI", 16, "bold"),
        )
        header.grid(row=0, column=0, sticky="w")

        header_right_frame = ttk.Frame(header_frame)
        header_right_frame.grid(row=0, column=1, sticky="e")

        self.debug_checkbutton = ttk.Checkbutton(
            header_right_frame,
            text="DEBUG",
            variable=self.debug_var,
            command=self._on_debug_toggled,
        )
        self.debug_checkbutton.pack(side="right")
        ToolTip(self.debug_checkbutton, "Aggiorna il flag DEBUG nel config.json e colora la finestra in giallino quando attivo.")

        self.summary_mail_checkbutton = ttk.Checkbutton(
            header_right_frame,
            text="MAIL RECAP",
            variable=self.summary_mail_var,
            command=self._on_summary_mail_toggled,
        )
        self.summary_mail_checkbutton.pack(side="right", padx=(0, 12))
        ToolTip(
            self.summary_mail_checkbutton,
            "Abilita o disabilita la mail di ricapitolazione verso dwh@cdaweb.it. Di default resta disattiva.",
        )

        release_label = ttk.Label(
            header_right_frame,
            textvariable=self.release_var,
            font=("Segoe UI", 10, "italic"),
        )
        release_label.pack(side="right", padx=(0, 12))

        selection_frame = ttk.LabelFrame(container, text="Parametri elaborazione", padding=12)
        selection_frame.grid(row=1, column=0, sticky="nsew")
        selection_frame.columnconfigure(1, weight=1)

        ttk.Label(selection_frame, text="Data sharing").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        self.datasharing_combo = ttk.Combobox(
            selection_frame,
            textvariable=self.datasharing_var,
            state="readonly",
        )
        self.datasharing_combo.grid(row=0, column=1, sticky="ew", pady=6)
        self.datasharing_combo.bind("<<ComboboxSelected>>", self._on_datasharing_changed)
        ToolTip(self.datasharing_combo, "Scegli il data sharing. I Datasharing abilitati vengono caricati automaticamente.")

        ttk.Label(selection_frame, text="Tipo periodo").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        period_type_frame = ttk.Frame(selection_frame)
        period_type_frame.grid(row=1, column=1, sticky="w", pady=6)

        ttk.Radiobutton(
            period_type_frame,
            text="Anno (YYYY)",
            variable=self.period_type_var,
            value="year",
            command=self._on_period_type_changed,
        ).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(
            period_type_frame,
            text="Periodo (YYYYMM)",
            variable=self.period_type_var,
            value="month",
            command=self._on_period_type_changed,
        ).pack(side="left")
        ToolTip(period_type_frame, "Scegli se elaborare un anno intero oppure un singolo periodo mensile.")

        ttk.Label(selection_frame, text="Valore periodo").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=6)
        self.period_entry = ttk.Entry(selection_frame, textvariable=self.period_value_var)
        self.period_entry.grid(row=2, column=1, sticky="ew", pady=6)
        period_validate_command = (self.root.register(self._validate_period_on_focus_out), "%P")
        period_invalid_command = (self.root.register(self._handle_invalid_period_focus_out),)
        self.period_entry.configure(
            validate="focusout",
            validatecommand=period_validate_command,
            invalidcommand=period_invalid_command,
        )
        self.period_entry.bind("<KeyRelease>", self._on_period_value_changed)
        ToolTip(self.period_entry, "Inserisci YYYY per un anno oppure YYYYMM per un mese, in base alla selezione sopra.")

        self.period_hint_label = ttk.Label(selection_frame, text="Inserisci un anno nel formato YYYY")
        self.period_hint_label.grid(row=3, column=1, sticky="w", pady=(0, 6))



        action_frame = ttk.Frame(container, padding=(0, 12, 0, 12))
        action_frame.grid(row=2, column=0, sticky="ew")


        self.run_button = ttk.Button(
            action_frame, 
            text="Esegui sottoscrizione", 
            command=self._execute_sottoscrizione_button_handler
        )
        self.run_button.pack(side="left")
        ToolTip(self.run_button, "Si abilita solo quando data sharing, periodo e almeno un Datasharingo sono validi.")

        # Pulsante per salvare in TD_RPT_SOCIO_PERIODO con cod_stato='INS'
        self.save_tdrpt_button = ttk.Button(
            action_frame,
            text="Salva TD_RPT_SOCIO_PERIODO (INS)",
            command=self._save_tdrpt_socio_periodo_ins
        )
        self.save_tdrpt_button.pack(side="left", padx=(8, 0))
        ToolTip(self.save_tdrpt_button, "Salva una riga in TD_RPT_SOCIO_PERIODO con stato INS per il periodo e data sharing selezionati.")
    
 
        self.manage_relations_button = ttk.Button(
            action_frame,
            text="Gestione abilitazioni",
            command=self._open_Datasharing_datasharing_management,
        )
        self.tabella_logging_button = ttk.Button(
            action_frame,
            text="Visualizza Tabella Logging",
            command=self._open_tabella_logging_window,
        )


        self.manage_relations_button.pack(side="left", padx=(8, 0))
        self.tabella_logging_button.pack(side="left", padx=(8, 0))
        
        ToolTip(
            self.manage_relations_button,
            "Apre la finestra di gestione delle relazioni Datasharing-data sharing per attivare o disattivare le abilitazioni.",
        )
        ToolTip(
            self.tabella_logging_button,
            "Apre la finestra della tabella di logging per visualizzare i dettagli delle elaborazioni.",
        )


        status_frame = ttk.LabelFrame(container, text="Stato", padding=12)
        status_frame.grid(row=3, column=0, sticky="ew")
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor="w")

        progress_frame = ttk.Frame(container)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=(4, 8))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            variable=self.progress_var,
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_text_var, width=8, anchor="e")
        self.progress_label.grid(row=0, column=1, padx=(8, 0))


        output_frame = ttk.LabelFrame(container, text="Esito elaborazione", padding=12)
        output_frame.grid(row=5, column=0, sticky="nsew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(output_frame, wrap="word", height=10, state="disabled")
        self.output_text.grid(row=0, column=0, sticky="nsew")

        output_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        output_scroll.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=output_scroll.set)

        # Add a Listbox for MSTR job status output
        mstr_status_frame = ttk.LabelFrame(container, text="Stato coda MSTR", padding=12)
        mstr_status_frame.grid(row=6, column=0, sticky="nsew")
        mstr_status_frame.columnconfigure(0, weight=1)
        mstr_status_frame.rowconfigure(0, weight=1)

        self.mstr_status_listbox = tk.Listbox(mstr_status_frame, height=8)
        self.mstr_status_listbox.grid(row=0, column=0, sticky="nsew")
        mstr_status_scroll = ttk.Scrollbar(mstr_status_frame, orient="vertical", command=self.mstr_status_listbox.yview)
        mstr_status_scroll.grid(row=0, column=1, sticky="ns")
        self.mstr_status_listbox.configure(yscrollcommand=mstr_status_scroll.set)

        self._on_period_type_changed()
        self._render_entity_checkboxes([])
        self._update_run_button_state()

    def _load_datasharing_options(self):
        # Carica solo i data sharing generali (is_general=1) attivi
        try:
            repo = SottoscrizioniRptRepository(self.backend_runtime.dso_manager.db_manager)
            df = repo.get_dataframe(is_general=1)
            options = []
            for _, row in df.iterrows():
                option = type('Option', (), {})()
                option.code = row['COD_SOTTOSCRIZIONE']
                option.name = row['NOM_SOTTOSCRIZIONE']
                option.file_type = row.get('COD_TIPO', '')
                options.append(option)
            self.option_map = {
                self._format_option_label(option): option
                for option in options
            }
            labels = list(self.option_map.keys())
            self.datasharing_combo["values"] = labels
            self.datasharing_var.set("")
            self.selected_option = None
            self.status_var.set("Seleziona un data sharing per iniziare.")
        except Exception as exc:
            messagebox.showerror("Errore", f"Impossibile caricare le opzioni di data sharing: {exc}", parent=self.root) 
        

    def _save_root_config_flag(self, flag_name, flag_value):
        config_path = self.backend_runtime.config.configs_file
        with open(config_path, "r", encoding="utf-8") as file:
            config_data = json.load(file)

        config_data[flag_name] = bool(flag_value)

        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(config_data, file, indent=4, ensure_ascii=False)
            file.write("\n")

    def _save_debug_flag(self, is_debug_enabled):
        self._save_root_config_flag("DEBUG", is_debug_enabled)

    def _save_summary_mail_flag(self, is_summary_mail_enabled):
        self._save_root_config_flag("SUMMARY_MAIL_ENABLED", is_summary_mail_enabled)

    def _sync_runtime_debug(self, is_debug_enabled):
        self.backend_runtime.config._debug = bool(is_debug_enabled)
        self.backend_runtime.dso_manager.config._debug = bool(is_debug_enabled)

        if getattr(self.backend_runtime.dso_manager, "_coca_cola_tracking_manager", None) is not None:
            self.backend_runtime.dso_manager._coca_cola_tracking_manager.debug_enabled = bool(is_debug_enabled)

    def _sync_runtime_summary_mail(self, is_summary_mail_enabled):
        self.backend_runtime.config._summary_mail_enabled = bool(is_summary_mail_enabled)
        self.backend_runtime.dso_manager.config._summary_mail_enabled = bool(is_summary_mail_enabled)

    def _on_debug_toggled(self):
        requested_value = bool(self.debug_var.get())
        try:
            self._save_debug_flag(requested_value)
            self._sync_runtime_debug(requested_value)
            self._apply_debug_theme()
            self.status_var.set(f"Modalità DEBUG {'attiva' if requested_value else 'disattiva'}." )
        except Exception as exc:
            self.debug_var.set(not requested_value)
            self._apply_debug_theme()
            messagebox.showerror("DEBUG", f"Impossibile aggiornare il flag DEBUG: {exc}", parent=self.root)

    def _on_summary_mail_toggled(self):
        requested_value = bool(self.summary_mail_var.get())
        try:
            self._save_summary_mail_flag(requested_value)
            self._sync_runtime_summary_mail(requested_value)
            self.status_var.set(f"Mail di recap {'attiva' if requested_value else 'disattiva'}." )
        except Exception as exc:
            self.summary_mail_var.set(not requested_value)
            messagebox.showerror(
                "Mail recap",
                f"Impossibile aggiornare il flag mail di recap: {exc}",
                parent=self.root,
            )

    @staticmethod
    def _format_option_label(option):
        return f"{option.code} - {option.name} ({option.file_type})"

    @staticmethod
    def _format_entity_label(entity_code, entity_name):
        cleaned_name = str(entity_name or "").strip()
        if cleaned_name:
            return f"{entity_code} - {cleaned_name}"
        return str(entity_code)

    def _on_entity_frame_configure(self, event=None):
        self.entity_canvas.configure(scrollregion=self.entity_canvas.bbox("all"))

    def _on_entity_canvas_configure(self, event):
        self.entity_canvas.itemconfigure(self.entity_window, width=event.width)

    def _set_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, text)
        self.output_text.configure(state="disabled")

    def _wait_for_mstr_jobs(self, db_job_run, conn, mysubscription_type, catalogo_rpt_ids, on_queue_empty=None):
        # Avvia il controllo in un thread autonomo, chiama on_queue_empty quando la coda è vuota
        def job_checker():
            while True:
                stra_jobs_run = list_jobs(connection=conn, type=JobType.SUBSCRIPTION, subscription_type=mysubscription_type)
                if stra_jobs_run is None or len(stra_jobs_run) == 0:
                    def notify_and_continue():
                        self._set_output("Nessun job MSTR in esecuzione. Avvio elaborazione...")
                        self._append_mstr_status("Nessun job MSTR in esecuzione. Avvio elaborazione...")
                        if on_queue_empty:
                            on_queue_empty()
                    self.root.after(0, notify_and_continue)
                    break

                job_obj_ids = set(db_job_run['COD_OBJ'].values) if db_job_run is not None else set()
                stra_obj_ids = set([job.object_id for job in stra_jobs_run if hasattr(job, 'object_id')])
                stra_obj_ids = stra_obj_ids & catalogo_rpt_ids
                common_obj_ids = job_obj_ids & stra_obj_ids
                only_db = job_obj_ids - stra_obj_ids
                only_stra = stra_obj_ids - job_obj_ids

                status_lines = [
                    "Job MSTR attivi:",
                    f"  In comune: {common_obj_ids}",
                    f"  Solo DB: {only_db}",
                    f"  Solo MSTR: {only_stra}",
                    "Attendo che la coda si svuoti..."
                ]
                self.root.after(0, lambda lines=status_lines: self._set_mstr_status(lines))
                time.sleep(5)

        t = threading.Thread(target=job_checker, daemon=True)
        t.start()

    def _set_mstr_status(self, lines):
        self.mstr_status_listbox.delete(0, tk.END)
        for line in lines:
            self.mstr_status_listbox.insert(tk.END, line)

    def _append_mstr_status(self, line):
        self.mstr_status_listbox.insert(tk.END, line)
        self.mstr_status_listbox.see(tk.END)

    def _update_progress(self, current_step, total_steps, label_text=None):
        if total_steps <= 0:
            percentage = 0
        else:
            percentage = min(100, max(0, round((current_step / total_steps) * 100)))

        self.progress_var.set(percentage)
        self.progress_text_var.set(f"{percentage}%")
        if label_text:
            self.status_var.set(label_text)

    def _append_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.configure(state="disabled")

    def _on_period_type_changed(self):
        if self.period_type_var.get() == "year":
            self.period_hint_label.configure(text="Inserisci un anno nel formato YYYY")
        else:
            self.period_hint_label.configure(text="Inserisci un periodo nel formato YYYYMM")
        self._update_run_button_state()

    def _on_period_value_changed(self, event=None):
        self._update_run_button_state()

    def _on_datasharing_changed(self, event=None):
        selected_label = self.datasharing_var.get()
        self.selected_option = self.option_map.get(selected_label)
        self._refresh_entities()
        self._update_run_button_state()



















    def _is_period_ready(self):
        value = self.period_value_var.get().strip()
        expected_length = 4 if self.period_type_var.get() == "year" else 6

        if not value:
            return False

        if not value.isdigit() or len(value) != expected_length:
            return False

        try:
            self.backend_runtime.expand_periods(value)
            return True
        except ValueError:
            return False

    def _update_run_button_state(self):
        prev_state = getattr(self, '_prev_run_button_state', None)
        if self.is_processing:
            self.run_button.configure(state="disabled")
            self.run_button.pack_forget()
            self.run_button.pack(side="left")
            self.run_button.configure(style="Red.TButton")
            #self.execute_sottoscrizione_button.configure(state="disabled")
            if prev_state != "processing":
                self.status_var.set("Elaborazione in corso: pulsante disabilitato.")
            self._prev_run_button_state = "processing"
            return

        missing = []
        if not self.selected_option:
            missing.append("data sharing")
        if not self._is_period_ready():
            missing.append("periodo")

        is_ready = not missing
        if is_ready:
            self.run_button.pack_forget()
            self.run_button.pack(side="left")
            self.run_button.configure(state="normal", style="TButton")
            #self.execute_sottoscrizione_button.configure(state="normal")
            if prev_state != "normal":
                self.status_var.set("Pronto per avviare l'elaborazione.")
            self._prev_run_button_state = "normal"
        else:
            self.run_button.pack_forget()
            #self.execute_sottoscrizione_button.configure(state="disabled")
            self._prev_run_button_state = "hidden"
            if len(missing) == 1:
                msg = f"Seleziona {missing[0]} per abilitare l'elaborazione."
            else:
                msg = "Compila: " + ", ".join(missing) + "."
            self.status_var.set(msg)

    # Stile rosso per il pulsante in elaborazione
    def _configure_styles(self):
        self.style.configure("TFrame", background=self.normal_background)
        self.style.configure("TLabelframe", background=self.normal_background)
        self.style.configure("TLabelframe.Label", background=self.normal_background)
        self.style.configure("TLabel", background=self.normal_background)
        self.style.configure("TCheckbutton", background=self.normal_background)
        self.style.configure("TRadiobutton", background=self.normal_background)
        self.style.configure("Red.TButton", background="#ff4d4d", foreground="white")
    

    def _open_tabella_logging_window(self):
        try:
            if self.management_window is not None and self.management_window.window.winfo_exists():
                self.management_window.window.lift()
                self.management_window.window.focus_force()
                return

            # Istanzia il repository            
            self.management_window = TabellaLoggingWindows(self)
            self.management_window.window.protocol("WM_DELETE_WINDOW", self._close_tabella_logging_window)
        except Exception as exc:
            messagebox.showerror("Errore apertura log", f"Errore durante l'apertura della tabella logging:\n{exc}", parent=self.root)
    
    def _close_tabella_logging_window(self):
        if self.management_window is None:
            return

        if self.management_window.window.winfo_exists():
            self.management_window.window.destroy()
        self.management_window = None


    def _open_Datasharing_datasharing_management(self):
        if self.management_window is not None and self.management_window.window.winfo_exists():
            self.management_window.window.lift()
            self.management_window.window.focus_force()
            return

        #####self.management_window = SocioDataSharingManagementWindow(self)
        self.management_window.window.protocol("WM_DELETE_WINDOW", self._close_Datasharing_datasharing_management)

    def _close_Datasharing_datasharing_management(self):
        if self.management_window is None:
            return

        if self.management_window.window.winfo_exists():
            self.management_window.window.destroy()
        self.management_window = None

    def _refresh_after_relation_change(self, datasharing_code):
        current_label = self.datasharing_var.get()
        self._load_datasharing_options()

        if current_label in self.option_map:
            self.datasharing_var.set(current_label)
            self.selected_option = self.option_map.get(current_label)
        else:
            self.datasharing_var.set("")
            self.selected_option = None

        if self.selected_option and self.selected_option.code == str(datasharing_code).strip():
            self._refresh_entities()
        elif self.selected_option is None:
            self.available_entities = []
            self._render_entity_checkboxes([])

        self._update_run_button_state()

    def _build_period_value(self):
        value = self.period_value_var.get().strip()
        expected_length = 4 if self.period_type_var.get() == "year" else 6

        if not value:
            messagebox.showerror("Validazione", "Inserire il periodo.", parent=self.root)
            raise ValueError("Inserire il periodo.")

        if not value.isdigit() or len(value) != expected_length:
            format_label = "YYYY" if expected_length == 4 else "YYYYMM"
            messagebox.showerror("Validazione", f"Il periodo deve essere nel formato {format_label}.", parent=self.root)
            raise ValueError(f"Il periodo deve essere nel formato {format_label}.")

        self.backend_runtime.expand_periods(value)
        return value

    def _validate_period_on_focus_out(self, proposed_value):
        if self._period_validation_in_progress:
            return True

        value = str(proposed_value or "").strip()
        self._last_period_error = ""

        if not value:
            self._update_run_button_state()
            return True

        try:
            expected_length = 4 if self.period_type_var.get() == "year" else 6

            if not value.isdigit() or len(value) != expected_length:
                format_label = "YYYY" if expected_length == 4 else "YYYYMM"
                raise ValueError(f"Il periodo deve essere nel formato {format_label}.")

            self.backend_runtime.expand_periods(value)
            self.status_var.set("Periodo valido.")
            self._update_run_button_state()
            return True
        except ValueError as exc:
            self._last_period_error = str(exc)
            self.status_var.set(self._last_period_error)
            self._update_run_button_state()
            return False

    def _handle_invalid_period_focus_out(self):
        if not self._last_period_error:
            return
        self.root.after_idle(self._show_period_validation_alert)

    def _show_period_validation_alert(self):
        if self._period_validation_in_progress or not self._last_period_error:
            return

        try:
            self._period_validation_in_progress = True
            value = self.period_value_var.get().strip()
            expected_length = 4 if self.period_type_var.get() == "year" else 6
            # Se l'utente ha inserito un periodo invece di un anno o viceversa, proponi il cambio
            if value.isdigit():
                if self.period_type_var.get() == "year" and len(value) == 6:
                    res = messagebox.askyesno(
                        "Tipo periodo non coerente",
                        "Hai inserito un periodo (YYYYMM) ma la selezione è su 'Anno'. Vuoi passare a 'Periodo mensile'?",
                        parent=self.root
                    )
                    if res:
                        self.period_type_var.set("month")
                        self.period_entry.icursor(tk.END)
                        self._update_run_button_state()
                        return
                elif self.period_type_var.get() == "month" and len(value) == 4:
                    res = messagebox.askyesno(
                        "Tipo periodo non coerente",
                        "Hai inserito un anno (YYYY) ma la selezione è su 'Periodo mensile'. Vuoi passare a 'Anno'?",
                        parent=self.root
                    )
                    if res:
                        self.period_type_var.set("year")
                        self.period_entry.icursor(tk.END)
                        self._update_run_button_state()
                        return
            messagebox.showwarning("Validazione periodo", self._last_period_error, parent=self.root)
            self._focus_period_entry()
        finally:
            self._period_validation_in_progress = False

    def _focus_period_entry(self):
        self.period_entry.focus_set()
        self.period_entry.selection_range(0, tk.END)
        self.period_entry.icursor(tk.END)

    def _validate_selection(self):
        if not self.selected_option:
            messagebox.showerror("Validazione", "Selezionare un data sharing.", parent=self.root)
            raise ValueError("Selezionare un data sharing.")

        datasharing_codes = self._get_selected_datasharing_codes()
        if not datasharing_codes:
            messagebox.showerror("Validazione", "Selezionare almeno un Datasharing abilitato.", parent=self.root)
            raise ValueError("Selezionare almeno un Datasharing abilitato.")

        period_value = self._build_period_value()
        return datasharing_codes, period_value

    def _set_running_state(self, is_running):
        self.is_processing = is_running
        state = "disabled" if is_running else "normal"
        combo_state = "disabled" if is_running else "readonly"

        # Disabilita tutti i widget tranne l'output
        self.datasharing_combo.configure(state=combo_state)
        self.period_entry.configure(state=state)
        self.debug_checkbutton.configure(state=state)
        self.summary_mail_checkbutton.configure(state=state)
        self.manage_relations_button.configure(state=state)
        self.tabella_logging_button.configure(state=state)
        self.datasharing_filter_entry.configure(state=state)
        for child in self.datasharing_frame.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass
        # Output sempre abilitato
        self.output_text.configure(state="normal")
        if not is_running and self.progress_var.get() < 100:
            self.progress_var.set(0)
            self.progress_text_var.set("0%")

        self._update_run_button_state()

    def _run_export(self):
        try:
            datasharing_codes, period_value = self._validate_selection()
        except ValueError as exc:
            messagebox.showerror("Validazione", str(exc), parent=self.root)
            return

        option = self.selected_option
        self._last_run_started_at = datetime.now()
        self._set_running_state(True)
        self.progress_var.set(0)
        self.progress_text_var.set("0%")
        self.status_var.set(
            f"Elaborazione in corso per {option.code}, Datasharing selezionati: {len(datasharing_codes)}, periodo {period_value}."
        )
        self._set_output(
            "ESECUZIONE STEP BY STEP\n"
            + "=" * 60
            + f"\nData sharing: {option.code} - {option.name}"
            + f"\nPeriodo richiesto: {period_value}"
            + f"\nDatasharing selezionati: {len(datasharing_codes)}\n\n"
        )

        worker = threading.Thread(
            target=self._run_export_worker,
            args=(datasharing_codes, period_value, option),
            daemon=True,
        )
        worker.start()

    def _run_export_worker(self, datasharing_codes, period_value, option):
        try:
            periods = self.backend_runtime.expand_periods(period_value)
            send_summary_mail = len(periods) == 1
            total_steps = max(1, len(datasharing_codes) * max(1, len(periods)))
            completed_steps = 0
            self.root.after(
                0,
                lambda: self._append_output(
                    f"Periodi da elaborare: {', '.join(periods)}\n" if periods else "Nessun periodo da elaborare.\n"
                ),
            )
            results = []
            for datasharing_index, datasharing_code in enumerate(datasharing_codes, start=1):
                self.root.after(
                    0,
                    lambda s=datasharing_code, idx=datasharing_index, total=len(datasharing_codes): self._append_output(
                        f"\n[{idx}/{total}] Avvio Datasharing {s}\n"
                    ),
                )

                datasharing_period_results = []
                for period_index, single_period in enumerate(periods, start=1):
                    self.root.after(
                        0,
                        lambda s=datasharing_code, p=single_period, idx=period_index, total=len(periods): self._append_output(
                            f"  - Periodo {idx}/{total}: {p} in elaborazione...\n"
                        ),
                    )
                    result = self.backend_runtime.dso_manager.main_process_data(
                        datasharing_code,
                        single_period,
                        option,
                        send_summary_mail=send_summary_mail,
                    )
                    datasharing_period_results.append(result)
                    completed_steps += 1
                    self.root.after(
                        0,
                        lambda s=datasharing_code, p=single_period, r=result, done=completed_steps, total=total_steps: self._on_period_step_completed(
                            s,
                            p,
                            r,
                            done,
                            total,
                        ),
                    )

                aggregated_result = self.backend_runtime.build_aggregated_result(datasharing_code, periods, option, datasharing_period_results)
                if len(periods) > 1:
                    Datasharing_data = self.backend_runtime.dso_manager.verify_Datasharing(datasharing_code, option.code)
                    self.backend_runtime.dso_manager.send_aggregated_summary_mail(
                        datasharing_code,
                        periods,
                        option,
                        Datasharing_data,
                        aggregated_result,
                        datasharing_period_results,
                    )
                results.append((datasharing_code, aggregated_result))
                self.root.after(
                    0,
                    lambda s=datasharing_code, r=aggregated_result: self._append_output(
                        f"  Completato datasharing {s}: {'OK' if r.get('success') else 'KO'}"
                        + (f" | Output: {r.get('output_file')}" if r.get('output_file') else "")
                        + "\n"
                    ),
                )
            self.root.after(0, lambda: self._handle_result(results, period_value, option))
        except Exception as exc:
            self.root.after(0, lambda: self._handle_error(exc))

    def _on_period_step_completed(self, datasharing_code, single_period, result, completed_steps, total_steps):
        self._append_output(
            f"    Esito periodo {single_period}: {'OK' if result.get('success') else 'KO'}"
            + (f" | File: {result.get('output_file')}" if result.get('output_file') else "")
            + "\n"
        )
        self._update_progress(
            completed_steps,
            total_steps,
            f"Avanzamento {completed_steps}/{total_steps} - datasharing {datasharing_code}, periodo {single_period}",
        )

    def _handle_result(self, results, period_value, option):
        self._set_running_state(False)

        success = all(bool(result.get("success")) for _, result in results)
        processed_count = len(results)
        success_count = sum(1 for _, result in results if result.get("success"))
        failure_count = processed_count - success_count
        run_finished_at = datetime.now()
        duration_text = ""
        if self._last_run_started_at is not None:
            duration = run_finished_at - self._last_run_started_at
            duration_text = str(duration).split(".")[0]

        status_text = "Elaborazione completata con successo." if success else "Elaborazione completata con errori."
        self.status_var.set(status_text)
        self.progress_var.set(100)
        self.progress_text_var.set("100%")

        requested_period_type = "Anno" if self.period_type_var.get() == "year" else "Periodo mensile"
        lines = [
            "RIEPILOGO ELABORAZIONE",
            "=" * 60,
            f"Data sharing: {option.code} - {option.name}",
            f"Tipo file: {option.file_type}",
            f"Tipo periodo richiesto: {requested_period_type}",
            f"Periodo richiesto: {period_value}",
            f"Esito: {'OK' if success else 'KO'}",
            f"Entità elaborate: {processed_count}",
            f"Entità con esito OK: {success_count}",
            f"Entità con esito KO: {failure_count}",
            f"Avvio elaborazione: {self._last_run_started_at.strftime('%d/%m/%Y %H:%M:%S') if self._last_run_started_at else ''}",
            f"Fine elaborazione: {run_finished_at.strftime('%d/%m/%Y %H:%M:%S')}",
        ]

        if duration_text:
            lines.append(f"Durata: {duration_text}")

        lines.append("")
        lines.append("DETTAGLIO ELABORAZIONE")
        lines.append("-" * 60)

        for ds_code, result in results:
            lines.append("")
            lines.append(f"Data sharing: {ds_code}")
            lines.append(f"Esito: {'OK' if result.get('success') else 'KO'}")
            lines.append(f"Messaggio: {result.get('message', '')}")

            output_file = result.get("output_file")
            if output_file:
                lines.append(f"File: {output_file}")
                file_count = len([item for item in str(output_file).split(';') if str(item).strip()])
                lines.append(f"Numero file: {file_count}")
            else:
                lines.append("File: nessun file prodotto")

        self._set_output("\n".join(lines))
        self._last_run_started_at = None

        if success:
            messagebox.showinfo("DataSharing", "Elaborazione completata.", parent=self.root)
        else:
            messagebox.showwarning("DataSharing", "Elaborazione terminata con errori. Controllare il dettaglio.", parent=self.root)

    def _handle_error(self, exc):
        self._set_running_state(False)
        self.progress_text_var.set("0%")
        self.status_var.set("Errore durante l'elaborazione.")
        self._set_output(f"Errore: {exc}")
        messagebox.showerror("DataSharing", str(exc), parent=self.root)

    def run(self):
        try:
            self.root.mainloop()
        except Exception as exc:
            # Protezione: non stampare nulla, solo mostrare errore grafico
            messagebox.showerror("DataSharing", str(exc), parent=self.root)
    

    def _render_entity_checkboxes(self, entity_rows):
        previous_selection = getattr(self, 'entity_check_vars', {})
        previous_selection = {entity_code: var.get() for entity_code, var in previous_selection.items()}

        if not hasattr(self, 'entity_frame'):
            self.entity_frame = ttk.Frame(self.root)
            self.entity_frame.pack()

        for child in self.entity_frame.winfo_children():
            child.destroy()

        self.entity_check_vars = {}

        if not entity_rows:
            ttk.Label(self.entity_frame, text="Nessuna entità disponibile.").grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        column_count = 3
        import math
        rows_per_column = max(1, math.ceil(len(entity_rows) / column_count))

        for column_index in range(column_count):
            self.entity_frame.columnconfigure(column_index, weight=1)

        for index, row in enumerate(entity_rows):
            entity_code = row["code"]
            entity_label = self._format_entity_label(entity_code, row["name"])
            var = tk.BooleanVar(value=previous_selection.get(entity_code, False))
            var.trace_add("write", self._on_entity_selection_changed)
            self.entity_check_vars[entity_code] = var

            row_index = index % rows_per_column
            column_index = index // rows_per_column
            ttk.Checkbutton(self.entity_frame, text=entity_label, variable=var).grid(
                row=row_index,
                column=column_index,
                sticky="w",
                padx=8,
                pady=2
            )
    def _refresh_entities(self):
        if not self.selected_option:
            self.available_entities = []
            self._render_entity_checkboxes([])
            self.status_var.set("Seleziona un data sharing.")
            self._update_run_button_state()
            return

        try:
            entity_rows = self._load_enabled_entities(self.selected_option)
        except Exception as exc:
            self._render_entity_checkboxes([])
            self.status_var.set(f"Errore caricamento entità: {exc}")
            self._set_output(f"Errore caricamento entità per {self.selected_option.code}: {exc}")
            self._update_run_button_state()
            return

        self.available_entities = entity_rows
        self._render_entity_checkboxes(entity_rows)

        if entity_rows:
            self.status_var.set(f"Trovate {len(entity_rows)} entità abilitate per {self.selected_option.code}.")
        else:
            self.status_var.set(f"Nessuna entità abilitata per {self.selected_option.code}.")
        self._update_run_button_state()

    def _load_enabled_entities(self, option):
        return self.strategy_manager.get_enabled_entities(option)
    
    def _save_tdrpt_socio_periodo_ins(self):
        try:
            # Recupera parametri da UI
            selected_label = self.datasharing_var.get()
            selected_option = self.option_map.get(selected_label)
            if not selected_option:
                messagebox.showerror("Errore", "Seleziona un data sharing valido.", parent=self.root)
                return
            periodo = self.period_value_var.get().strip()
            if not periodo.isdigit():
                messagebox.showerror("Errore", "Inserisci un periodo valido.", parent=self.root)
                return
            # Parametri fittizi per esempio: id_socio=999, cod_report=selected_option.code
            # In produzione, recuperare id_socio e cod_report reali secondo la logica applicativa
            id_socio = 999
            cod_report = selected_option.code
            cod_sottoscrizione = selected_option.code
            
            repo = TdRptSocioPeriodoRepository(self.backend_runtime.dso_manager.db_manager)
            repo.inserisci_TD_RPT_SOCIO_PERIODO(
                id_socio=id_socio,
                num_periodo=int(periodo),
                cod_sottoscrizione=cod_sottoscrizione,
                cod_report=cod_report,
                cod_stato='INS'
            )
            messagebox.showinfo("Salvataggio", "Riga salvata in TD_RPT_SOCIO_PERIODO con stato INS.", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Errore salvataggio", f"Errore durante il salvataggio: {exc}", parent=self.root)
    
    def _execute_sottoscrizione_button_handler(self):
        """
        Callback per il pulsante Esegui Sottoscrizione: raccoglie i parametri dalla UI e chiama execute_sottoscrizione.
        """
        try:
            # Recupera parametri dalla UI
           # Recupera parametri da UI
            selected_label = self.datasharing_var.get()
            selected_option = self.option_map.get(selected_label)
            if not selected_option:
                messagebox.showerror("Errore", "Seleziona un data sharing valido.", parent=self.root)
                return
            periodo = self.period_value_var.get().strip()
            if not periodo.isdigit():
                messagebox.showerror("Errore", "Inserisci un periodo valido.", parent=self.root)
                return
            # Parametri fittizi per esempio: id_socio=999, cod_report=selected_option.code
            # In produzione, recuperare id_socio e cod_report reali secondo la logica applicativa
            id_socio = 999
            
            cod_report = selected_option.code
            cod_sottoscrizione = selected_option.code
            
            mysubscription_type = SubscriptionType.EMAIL
            # Esegui
            self.strategy_manager.execute_sottoscrizione(
                cod_sottoscrizione=cod_sottoscrizione,
                cod_rpt=cod_report,
                cod_socio=id_socio,
                periodo=periodo,
                mysubscription_type=mysubscription_type
            )
            messagebox.showinfo("Esecuzione sottoscrizione", f"Sottoscrizione avviata per socio {cod_socio}, periodo {periodo}.", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Errore esecuzione sottoscrizione", str(exc), parent=self.root)

