import tkinter as tk
from tkinter import ttk, messagebox

class DataSharingSocioManagementWindow:
    COLUMNS = (
        "socio_code",
        "socio_name",
        "datasharing_code",
        "datasharing_name",
        "wholesaler_id",
        "flag_attivo",
        "flag_usa_nuovo_strumento",
        "updated_at",
    )

    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.backend = parent_app.backend
        self.window = tk.Toplevel(parent_app.root)
        self.window.title("Gestione socio-data sharing")
        self.window.geometry("1040x560")
        self.window.minsize(920, 480)
        self.window.transient(parent_app.root)

        self.socio_filter_var = tk.StringVar()
        self.datasharing_filter_var = tk.StringVar()
        self.quick_filter_var = tk.StringVar()
        self.only_enabled_var = tk.BooleanVar(value=False)
        self.only_disabled_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Caricamento relazioni...")
        self.selected_relation_var = tk.StringVar(value="Nessuna relazione selezionata.")
        self.edit_enabled_var = tk.BooleanVar(value=False)
        self.edit_use_new_tool_var = tk.BooleanVar(value=False)
        self.edit_wholesaler_id_var = tk.StringVar()
        self._cached_relations = []
        self._wholesaler_inline_editor = None
        self._wholesaler_inline_context = None

        self._build_ui()
        self._load_relations()

    def _build_ui(self):
        container = ttk.Frame(self.window, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        filter_frame = ttk.LabelFrame(container, text="Filtri", padding=12)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)
        filter_frame.columnconfigure(5, weight=1)

        ttk.Label(filter_frame, text="Socio").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.socio_filter_combo = ttk.Combobox(filter_frame, textvariable=self.socio_filter_var, state="readonly")
        self.socio_filter_combo.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(filter_frame, text="Data sharing").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.datasharing_filter_combo = ttk.Combobox(filter_frame, textvariable=self.datasharing_filter_var, state="readonly")
        self.datasharing_filter_combo.grid(row=0, column=3, sticky="ew", pady=4)

        ttk.Label(filter_frame, text="Ricerca veloce").grid(row=0, column=4, sticky="w", padx=(12, 8), pady=4)
        quick_filter_entry = ttk.Entry(filter_frame, textvariable=self.quick_filter_var)
        quick_filter_entry.grid(row=0, column=5, sticky="ew", pady=4)

        only_enabled_check = ttk.Checkbutton(
            filter_frame,
            text="Mostra solo attivi",
            variable=self.only_enabled_var,
            command=self._on_enabled_filter_toggled,
        )
        only_enabled_check.grid(row=1, column=0, sticky="w", pady=(8, 0))

        only_disabled_check = ttk.Checkbutton(
            filter_frame,
            text="Mostra solo disattivi",
            variable=self.only_disabled_var,
            command=self._on_disabled_filter_toggled,
        )
        only_disabled_check.grid(row=1, column=1, sticky="w", pady=(8, 0), padx=(12, 0))

        refresh_button = ttk.Button(filter_frame, text="Aggiorna elenco", command=self._load_relations)
        refresh_button.grid(row=1, column=5, sticky="e", pady=(8, 0))

        tree_frame = ttk.Frame(container)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode="browse",
        )
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.heading("socio_code", text="Socio")
        self.tree.heading("socio_name", text="Ragione sociale")
        self.tree.heading("datasharing_code", text="Codice")
        self.tree.heading("datasharing_name", text="Data sharing")
        self.tree.heading("wholesaler_id", text="WholesalerID")
        self.tree.heading("flag_attivo", text="Attivo")
        self.tree.heading("flag_usa_nuovo_strumento", text="Questo strumento")
        self.tree.heading("updated_at", text="Aggiornamento")
        self.tree.column("socio_code", width=110, anchor="w")
        self.tree.column("socio_name", width=240, anchor="w")
        self.tree.column("datasharing_code", width=110, anchor="w")
        self.tree.column("datasharing_name", width=220, anchor="w")
        self.tree.column("wholesaler_id", width=120, anchor="w")
        self.tree.column("flag_attivo", width=80, anchor="center")
        self.tree.column("flag_usa_nuovo_strumento", width=130, anchor="center")
        self.tree.column("updated_at", width=150, anchor="center")
        self.tree.tag_configure("enabled", background="#b9f6ca")
        self.tree.tag_configure("disabled", background="#ffab91")

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        action_frame = ttk.Frame(container)
        action_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        ttk.Button(action_frame, text="Attiva", command=lambda: self._set_selected_relation_status(True)).pack(side="left")
        ttk.Button(action_frame, text="Disattiva", command=lambda: self._set_selected_relation_status(False)).pack(side="left", padx=(8, 0))
        ttk.Button(
            action_frame,
            text="Abilita tutto su questo strumento",
            command=lambda: self._set_bulk_datasharing_tool_mode(True),
        ).pack(side="left", padx=(24, 0))
        ttk.Button(
            action_frame,
            text="Disabilita tutto su questo strumento",
            command=lambda: self._set_bulk_datasharing_tool_mode(False),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            action_frame,
            text="Usa questo strumento",
            command=lambda: self._set_selected_tool_mode(True),
        ).pack(side="left", padx=(24, 0))
        ttk.Button(
            action_frame,
            text="Usa strumento vecchio",
            command=lambda: self._set_selected_tool_mode(False),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(action_frame, text="Chiudi", command=self.window.destroy).pack(side="right")

        editor_frame = ttk.LabelFrame(container, text="Configurazione relazione", padding=12)
        editor_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        editor_frame.columnconfigure(2, weight=1)

        ttk.Label(editor_frame, textvariable=self.selected_relation_var).grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(0, 8),
        )

        self.edit_enabled_check = ttk.Checkbutton(
            editor_frame,
            text="Attiva",
            variable=self.edit_enabled_var,
        )
        self.edit_enabled_check.grid(row=1, column=0, sticky="w", pady=4)

        self.edit_use_new_tool_check = ttk.Checkbutton(
            editor_frame,
            text="Gestito da questo programma",
            variable=self.edit_use_new_tool_var,
        )
        self.edit_use_new_tool_check.grid(row=1, column=1, sticky="w", pady=4, padx=(12, 0))

        ttk.Label(editor_frame, text="WholesalerID").grid(row=2, column=1, sticky="e", padx=(12, 8), pady=4)
        self.edit_wholesaler_id_entry = ttk.Entry(editor_frame, textvariable=self.edit_wholesaler_id_var)
        self.edit_wholesaler_id_entry.grid(row=2, column=2, sticky="ew", pady=4)

        self.save_configuration_button = ttk.Button(
            editor_frame,
            text="Salva configurazione",
            command=self._save_selected_relation_configuration,
        )
        self.save_configuration_button.grid(row=2, column=3, sticky="e", padx=(12, 0), pady=4)

        ttk.Label(
            editor_frame,
            text="WholesalerID modificabile solo per CC001 e CC002.",
        ).grid(row=3, column=1, columnspan=3, sticky="w", pady=(4, 0))

        status_frame = ttk.LabelFrame(container, text="Stato", padding=12)
        status_frame.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor="w")

        self.socio_filter_combo.bind("<<ComboboxSelected>>", lambda event: self._load_relations())
        self.datasharing_filter_combo.bind("<<ComboboxSelected>>", lambda event: self._load_relations())
        quick_filter_entry.bind("<KeyRelease>", self._on_quick_filter_changed)
        self.tree.bind("<<TreeviewSelect>>", self._on_relation_selected)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self._update_editor_state(None)

    @staticmethod
    def _format_boolean_value(value):
        return "SI" if bool(int(value or 0)) else "NO"

    @staticmethod
    def _format_datetime_value(value):
        if value in (None, ""):
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y %H:%M:%S")
        return str(value)

    def _clear_tree(self):
        self._destroy_wholesaler_inline_editor()
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

    def _destroy_wholesaler_inline_editor(self):
        if self._wholesaler_inline_editor is not None and self._wholesaler_inline_editor.winfo_exists():
            self._wholesaler_inline_editor.destroy()
        self._wholesaler_inline_editor = None
        self._wholesaler_inline_context = None

    def _build_relation_item(self, row):
        is_enabled = bool(int(row.get("Flag_Attivo", 0) or 0))
        return {
            "socio_code": str(row.get("TC_Soci_Codice", "") or "").strip(),
            "socio_name": str(row.get("TC_Soci_Ragione_Sociale", "") or "").strip(),
            "datasharing_code": str(row.get("DataSharing_Code", "") or "").strip(),
            "datasharing_name": str(row.get("DataSharing_Nome", "") or "").strip(),
            "wholesaler_id": str(row.get("WholesalerID", "") or "").strip(),
            "flag_attivo": self._format_boolean_value(row.get("Flag_Attivo", 0)),
            "flag_usa_nuovo_strumento": self._format_boolean_value(row.get("Flag_Usa_Nuovo_Strumento", 0)),
            "updated_at": self._format_datetime_value(row.get("DataAggiornamento")),
            "is_enabled": is_enabled,
            "uses_new_tool": bool(int(row.get("Flag_Usa_Nuovo_Strumento", 0) or 0)),
        }

    def _matches_quick_filter(self, relation_item):
        quick_filter = self.quick_filter_var.get().strip().lower()
        if not quick_filter:
            return True

        searchable_values = [
            relation_item["socio_code"],
            relation_item["socio_name"],
            relation_item["datasharing_code"],
            relation_item["datasharing_name"],
            relation_item["wholesaler_id"],
            relation_item["flag_attivo"],
            relation_item["flag_usa_nuovo_strumento"],
            relation_item["updated_at"],
        ]
        combined_text = " ".join(str(value or "").lower() for value in searchable_values)
        return quick_filter in combined_text

    def _render_relations(self):
        self._clear_tree()

        filtered_relations = [item for item in self._cached_relations if self._matches_quick_filter(item)]
        if not filtered_relations:
            if self._cached_relations:
                self.status_var.set("Nessuna relazione trovata per la ricerca veloce corrente.")
            else:
                self.status_var.set("Nessuna relazione trovata con i filtri correnti.")
            return

        for relation_item in filtered_relations:
            row_tag = "enabled" if relation_item["is_enabled"] else "disabled"
            self.tree.insert(
                "",
                tk.END,
                values=(
                    relation_item["socio_code"],
                    relation_item["socio_name"],
                    relation_item["datasharing_code"],
                    relation_item["datasharing_name"],
                    relation_item["wholesaler_id"],
                    relation_item["flag_attivo"],
                    relation_item["flag_usa_nuovo_strumento"],
                    relation_item["updated_at"],
                ),
                tags=(row_tag,),
            )

        if self.quick_filter_var.get().strip():
            self.status_var.set(
                f"Relazioni visualizzate: {len(filtered_relations)} su {len(self._cached_relations)} totali."
            )
        else:
            self.status_var.set(f"Relazioni caricate: {len(filtered_relations)}.")

    def _on_quick_filter_changed(self, event=None):
        self._render_relations()

    def _on_enabled_filter_toggled(self):
        if self.only_enabled_var.get() and self.only_disabled_var.get():
            self.only_disabled_var.set(False)
        self._load_relations()

    def _on_disabled_filter_toggled(self):
        if self.only_disabled_var.get() and self.only_enabled_var.get():
            self.only_enabled_var.set(False)
        self._load_relations()

    def _populate_filter_combos(self, relation_data):
        socio_values = [""]
        datasharing_values = [""]

        for _, row in relation_data.iterrows():
            socio_label = f"{str(row.get('TC_Soci_Codice', '') or '').strip()} - {str(row.get('TC_Soci_Ragione_Sociale', '') or '').strip()}".strip()
            datasharing_label = f"{str(row.get('DataSharing_Code', '') or '').strip()} - {str(row.get('DataSharing_Nome', '') or '').strip()}".strip()

            if socio_label and socio_label not in socio_values:
                socio_values.append(socio_label)
            if datasharing_label and datasharing_label not in datasharing_values:
                datasharing_values.append(datasharing_label)

        self.socio_filter_combo["values"] = socio_values
        self.datasharing_filter_combo["values"] = datasharing_values

        if self.socio_filter_var.get() not in socio_values:
            self.socio_filter_var.set("")
        if self.datasharing_filter_var.get() not in datasharing_values:
            self.datasharing_filter_var.set("")

    @staticmethod
    def _supports_wholesaler_id(datasharing_code):
        return str(datasharing_code or "").strip().upper() in {"CC001", "CC002"}

    def _update_editor_state(self, relation):
        if relation is None:
            self.selected_relation_var.set("Nessuna relazione selezionata.")
            self.edit_enabled_var.set(False)
            self.edit_use_new_tool_var.set(False)
            self.edit_wholesaler_id_var.set("")
            self.edit_enabled_check.configure(state="disabled")
            self.edit_use_new_tool_check.configure(state="disabled")
            self.edit_wholesaler_id_entry.configure(state="disabled")
            self.save_configuration_button.configure(state="disabled")
            return

        self.selected_relation_var.set(
            f"Socio {relation['socio_code']} - {relation['socio_name']} | Data sharing {relation['datasharing_code']} - {relation['datasharing_name']}"
        )
        self.edit_enabled_var.set(bool(relation["is_enabled"]))
        self.edit_use_new_tool_var.set(bool(relation["uses_new_tool"]))
        self.edit_wholesaler_id_var.set(str(relation.get("wholesaler_id", "") or ""))
        self.edit_enabled_check.configure(state="normal")
        self.edit_use_new_tool_check.configure(state="normal")

        if self._supports_wholesaler_id(relation["datasharing_code"]):
            self.edit_wholesaler_id_entry.configure(state="normal")
        else:
            self.edit_wholesaler_id_var.set("")
            self.edit_wholesaler_id_entry.configure(state="disabled")

        self.save_configuration_button.configure(state="normal")

    def _on_relation_selected(self, event=None):
        self._update_editor_state(self._get_selected_relation())

    def _load_relations(self):
        socio_filter_value = self.socio_filter_var.get().strip()
        datasharing_filter_value = self.datasharing_filter_var.get().strip()
        socio_filter = socio_filter_value.split(" - ", 1)[0].strip() if socio_filter_value else None
        datasharing_filter = datasharing_filter_value.split(" - ", 1)[0].strip() if datasharing_filter_value else None
        only_enabled = bool(self.only_enabled_var.get())
        only_disabled = bool(self.only_disabled_var.get())

        try:
            relation_data = self.backend.get_socio_datasharing_relations(
                socio=socio_filter,
                datasharing_code=datasharing_filter,
                only_enabled=only_enabled,
                only_current_tool=False,
            )
        except Exception as exc:
            self._clear_tree()
            self._cached_relations = []
            self._update_editor_state(None)
            self.status_var.set(f"Errore caricamento relazioni: {exc}")
            messagebox.showerror("Gestione socio-data sharing", str(exc), parent=self.window)
            return

        if relation_data.empty:
            self._cached_relations = []
            self._clear_tree()
            self._update_editor_state(None)
            self.socio_filter_combo["values"] = [""]
            self.datasharing_filter_combo["values"] = [""]
            self.status_var.set("Nessuna relazione trovata con i filtri correnti.")
            return

        if only_disabled:
            relation_data = relation_data[relation_data["Flag_Attivo"].fillna(0).astype(int) == 0]

        self._populate_filter_combos(relation_data)
        self._cached_relations = [self._build_relation_item(row) for _, row in relation_data.iterrows()]
        self._render_relations()
        self._update_editor_state(None)

    def _get_selected_relation(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return None

        item_values = self.tree.item(selected_items[0], "values")
        if not item_values:
            return None

        return {
            "socio_code": item_values[0],
            "socio_name": item_values[1],
            "datasharing_code": item_values[2],
            "datasharing_name": item_values[3],
            "wholesaler_id": item_values[4],
            "is_enabled": str(item_values[5]).strip().upper() == "SI",
            "uses_new_tool": str(item_values[6]).strip().upper() == "SI",
        }

    def _set_selected_relation_status(self, is_enabled):
        selected_relation = self._get_selected_relation()
        if selected_relation is None:
            messagebox.showwarning(
                "Gestione socio-data sharing",
                "Seleziona una relazione da aggiornare.",
                parent=self.window,
            )
            return

        self._apply_relation_enabled(selected_relation, is_enabled)

    def _apply_relation_enabled(self, relation, is_enabled):
        if relation["is_enabled"] == bool(is_enabled):
            stato = "attiva" if is_enabled else "disattiva"
            self.status_var.set(
                f"La relazione {relation['socio_code']} / {relation['datasharing_code']} e' gia {stato}."
            )
            self.edit_enabled_var.set(bool(is_enabled))
            return

        try:
            self.backend.set_socio_datasharing_enabled(
                relation["socio_code"],
                relation["datasharing_code"],
                is_enabled,
                socio_name=relation["socio_name"],
                datasharing_name=relation["datasharing_name"],
            )
            action_label = "attivata" if is_enabled else "disattivata"
            self.status_var.set(
                f"Relazione {relation['socio_code']} / {relation['datasharing_code']} {action_label}."
            )
            self.edit_enabled_var.set(bool(is_enabled))
            self._load_relations()
            self.parent_app._refresh_after_relation_change(relation["datasharing_code"])
        except Exception as exc:
            self.status_var.set(f"Errore aggiornamento relazione: {exc}")
            messagebox.showerror("Gestione socio-data sharing", str(exc), parent=self.window)

    def _set_selected_tool_mode(self, use_new_tool):
        selected_relation = self._get_selected_relation()
        if selected_relation is None:
            messagebox.showwarning(
                "Gestione socio-data sharing",
                "Seleziona una relazione da aggiornare.",
                parent=self.window,
            )
            return

        self._apply_relation_tool_mode(selected_relation, use_new_tool)

    def _apply_relation_tool_mode(self, relation, use_new_tool):
        if relation["uses_new_tool"] == bool(use_new_tool):
            stato = "questo strumento" if use_new_tool else "lo strumento vecchio"
            self.status_var.set(
                f"La relazione {relation['socio_code']} / {relation['datasharing_code']} usa gia {stato}."
            )
            return

        try:
            self.backend.set_socio_datasharing_tool_enabled(
                relation["socio_code"],
                relation["datasharing_code"],
                use_new_tool,
                socio_name=relation["socio_name"],
                datasharing_name=relation["datasharing_name"],
            )
            action_label = "usa questo strumento" if use_new_tool else "usa lo strumento vecchio"
            self.status_var.set(
                f"Relazione {relation['socio_code']} / {relation['datasharing_code']} aggiornata: {action_label}."
            )
            self._load_relations()
            self.parent_app._refresh_after_relation_change(relation["datasharing_code"])
        except Exception as exc:
            self.status_var.set(f"Errore aggiornamento strumento: {exc}")
            messagebox.showerror("Gestione socio-data sharing", str(exc), parent=self.window)

    def _set_bulk_datasharing_tool_mode(self, use_new_tool):
        selected_relation = self._get_selected_relation()
        if selected_relation is None:
            messagebox.showwarning(
                "Gestione socio-data sharing",
                "Seleziona una riga del data sharing su cui applicare l'azione massiva.",
                parent=self.window,
            )
            return
        datasharing_code = selected_relation["datasharing_code"]

        action_label = "abilitare" if use_new_tool else "disabilitare"
        confirmed = messagebox.askyesno(
            "Conferma azione massiva",
            f"Confermi di {action_label} il flag 'Questo strumento' per tutte le righe del data sharing {datasharing_code}?",
            parent=self.window,
        )
        if not confirmed:
            self.status_var.set(f"Azione massiva annullata per {datasharing_code}.")
            return

        try:
            relation_data = self.backend.get_socio_datasharing_relations(
                datasharing_code=datasharing_code,
                only_current_tool=False,
            )
            if relation_data.empty:
                self.status_var.set(f"Nessuna relazione trovata per il data sharing {datasharing_code}.")
                return

            updated_count = 0
            for _, row in relation_data.iterrows():
                relation = self._build_relation_item(row)
                if relation["uses_new_tool"] == bool(use_new_tool):
                    continue
                self.backend.set_socio_datasharing_tool_enabled(
                    relation["socio_code"],
                    relation["datasharing_code"],
                    use_new_tool,
                    socio_name=relation["socio_name"],
                    datasharing_name=relation["datasharing_name"],
                )
                updated_count += 1

            result_label = "abilitato" if use_new_tool else "disabilitato"
            self.status_var.set(
                f"Flag 'Questo strumento' {result_label} per {updated_count} righe del data sharing {datasharing_code}."
            )
            self._load_relations()
            self.parent_app._refresh_after_relation_change(datasharing_code)
        except Exception as exc:
            self.status_var.set(f"Errore aggiornamento massivo: {exc}")
            messagebox.showerror("Gestione socio-data sharing", str(exc), parent=self.window)

    def _save_selected_relation_configuration(self):
        selected_relation = self._get_selected_relation()
        if selected_relation is None:
            messagebox.showwarning(
                "Gestione socio-data sharing",
                "Seleziona una relazione da configurare.",
                parent=self.window,
            )
            return

        wholesaler_id = self.edit_wholesaler_id_var.get().strip()
        if not self._supports_wholesaler_id(selected_relation["datasharing_code"]):
            wholesaler_id = ""

        try:
            self.backend.set_socio_datasharing_enabled(
                selected_relation["socio_code"],
                selected_relation["datasharing_code"],
                bool(self.edit_enabled_var.get()),
                socio_name=selected_relation["socio_name"],
                datasharing_name=selected_relation["datasharing_name"],
            )
            self.backend.update_socio_datasharing_configuration(
                selected_relation["socio_code"],
                selected_relation["datasharing_code"],
                bool(self.edit_use_new_tool_var.get()),
                wholesaler_id=wholesaler_id,
                socio_name=selected_relation["socio_name"],
                datasharing_name=selected_relation["datasharing_name"],
            )
            self.status_var.set(
                f"Configurazione salvata per {selected_relation['socio_code']} / {selected_relation['datasharing_code']}."
            )
            self._load_relations()
            self.parent_app._refresh_after_relation_change(selected_relation["datasharing_code"])
        except Exception as exc:
            self.status_var.set(f"Errore salvataggio configurazione: {exc}")
            messagebox.showerror("Gestione socio-data sharing", str(exc), parent=self.window)

    def _on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        if not item_id or not column_id:
            return

        self.tree.selection_set(item_id)
        relation = self._get_selected_relation()
        if relation is None:
            return

        if column_id == "#6":
            self._apply_relation_enabled(relation, not relation["is_enabled"])
            return

        if column_id == "#7":
            self._apply_relation_tool_mode(relation, not relation["uses_new_tool"])
            return

        if column_id == "#5" and self._supports_wholesaler_id(relation["datasharing_code"]):
            self._open_inline_wholesaler_editor(item_id, column_id, relation)

    def _open_inline_wholesaler_editor(self, item_id, column_id, relation):
        self._destroy_wholesaler_inline_editor()
        cell_box = self.tree.bbox(item_id, column_id)
        if not cell_box:
            return

        x_pos, y_pos, width, height = cell_box
        self._wholesaler_inline_context = relation
        self._wholesaler_inline_editor = ttk.Entry(self.tree)
        self._wholesaler_inline_editor.insert(0, relation.get("wholesaler_id", ""))
        self._wholesaler_inline_editor.place(x=x_pos, y=y_pos, width=width, height=height)
        self._wholesaler_inline_editor.focus_set()
        self._wholesaler_inline_editor.selection_range(0, tk.END)
        self._wholesaler_inline_editor.bind("<Return>", self._save_inline_wholesaler_editor)
        self._wholesaler_inline_editor.bind("<Escape>", lambda event: self._destroy_wholesaler_inline_editor())
        self._wholesaler_inline_editor.bind("<FocusOut>", self._save_inline_wholesaler_editor)

    def _save_inline_wholesaler_editor(self, event=None):
        if self._wholesaler_inline_editor is None or self._wholesaler_inline_context is None:
            return

        relation = self._wholesaler_inline_context
        wholesaler_id = self._wholesaler_inline_editor.get().strip()
        self._destroy_wholesaler_inline_editor()

        try:
            self.backend.update_socio_datasharing_configuration(
                relation["socio_code"],
                relation["datasharing_code"],
                bool(relation["uses_new_tool"]),
                wholesaler_id=wholesaler_id,
                socio_name=relation["socio_name"],
                datasharing_name=relation["datasharing_name"],
            )
            self.status_var.set(
                f"WholesalerID aggiornato per {relation['socio_code']} / {relation['datasharing_code']}."
            )
            self._load_relations()
            self.parent_app._refresh_after_relation_change(relation["datasharing_code"])
        except Exception as exc:
            self.status_var.set(f"Errore aggiornamento WholesalerID: {exc}")
            messagebox.showerror("Gestione socio-data sharing", str(exc), parent=self.window)

