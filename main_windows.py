import threading
import tkinter as tk
from tkinter import messagebox, ttk
import math
from datetime import datetime
import json

from managers.active_directory_authorization_manager import ActiveDirectoryAuthorizationManager, AuthorizationError
from services.data_sharing_runtime import DataSharingRuntime


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


class SocioDataSharingManagementWindow:
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


class DataSharingWindowsApp:
    def __init__(self):
        self.backend = DataSharingRuntime()
        self.root = tk.Tk()
        self.root.title(f"DataSharing {self.backend.config.version}")
        self.root.geometry("1120x760")
        self.root.minsize(960, 680)
        self.style = ttk.Style()
        self.normal_background = self.style.lookup("TFrame", "background") or "#f0f0f0"
        self.debug_background = "#fff7cc"

        self.selected_option = None
        self.available_soci = []
        self.socio_check_vars = {}
        self.is_processing = False

        self.datasharing_var = tk.StringVar()
        self.period_type_var = tk.StringVar(value="year")
        self.period_value_var = tk.StringVar()
        self.socio_filter_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Seleziona un data sharing per iniziare.")
        self.release_var = tk.StringVar(value=f"Release {self.backend.config.version}")
        self.debug_var = tk.BooleanVar(value=bool(self.backend.config.debug))
        self.summary_mail_var = tk.BooleanVar(value=bool(self.backend.config.summary_mail_enabled))
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

    def _apply_debug_theme(self):
        background = self.debug_background if self.debug_var.get() else self.normal_background
        self.root.configure(bg=background)
        self.style.configure("TFrame", background=background)
        self.style.configure("TLabelframe", background=background)
        self.style.configure("TLabelframe.Label", background=background)
        self.style.configure("TLabel", background=background)
        self.style.configure("TCheckbutton", background=background)
        self.style.configure("TRadiobutton", background=background)

        if hasattr(self, "soci_canvas"):
            self.soci_canvas.configure(background=background)

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
            text="DataSharing - CDA",
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
        ToolTip(self.datasharing_combo, "Scegli il data sharing. I soci abilitati vengono caricati automaticamente.")

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

        soci_label_frame = ttk.LabelFrame(selection_frame, text="Soci abilitati")
        soci_label_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=8)
        soci_label_frame.columnconfigure(0, weight=1)
        soci_label_frame.rowconfigure(1, weight=1)
        selection_frame.rowconfigure(4, weight=1)

        soci_actions_frame = ttk.Frame(soci_label_frame)
        soci_actions_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        select_all_button = ttk.Button(soci_actions_frame, text="Seleziona tutti", command=self._select_all_soci)
        select_all_button.pack(side="left")
        clear_all_button = ttk.Button(soci_actions_frame, text="Deseleziona tutti", command=self._clear_soci_selection)
        clear_all_button.pack(side="left", padx=(8, 0))
        ttk.Label(soci_actions_frame, text="Filtro soci").pack(side="left", padx=(16, 6))
        self.socio_filter_entry = ttk.Entry(soci_actions_frame, textvariable=self.socio_filter_var, width=32)
        self.socio_filter_entry.pack(side="left", fill="x", expand=True)
        self.socio_filter_entry.bind("<KeyRelease>", self._on_socio_filter_changed)
        ToolTip(select_all_button, "Seleziona tutti i soci attualmente visibili.")
        ToolTip(clear_all_button, "Rimuove la selezione da tutti i soci.")
        ToolTip(self.socio_filter_entry, "Filtra i soci per codice o ragione sociale.")

        self.soci_canvas = tk.Canvas(soci_label_frame, height=150, highlightthickness=0)
        self.soci_canvas.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        ToolTip(self.soci_canvas, "Seleziona uno o più soci abilitati per il data sharing scelto.")

        soci_scrollbar = ttk.Scrollbar(soci_label_frame, orient="vertical", command=self.soci_canvas.yview)
        soci_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))
        self.soci_canvas.configure(yscrollcommand=soci_scrollbar.set)

        self.soci_frame = ttk.Frame(self.soci_canvas)
        self.soci_window = self.soci_canvas.create_window((0, 0), window=self.soci_frame, anchor="nw")
        self.soci_frame.bind("<Configure>", self._on_soci_frame_configure)
        self.soci_canvas.bind("<Configure>", self._on_soci_canvas_configure)

        action_frame = ttk.Frame(container, padding=(0, 12, 0, 12))
        action_frame.grid(row=2, column=0, sticky="ew")

        self.run_button = ttk.Button(action_frame, text="Avvia elaborazione", command=self._run_export)
        self.run_button.pack(side="left")
        ToolTip(self.run_button, "Si abilita solo quando data sharing, periodo e almeno un socio sono validi.")

        self.manage_relations_button = ttk.Button(
            action_frame,
            text="Gestione abilitazioni",
            command=self._open_socio_datasharing_management,
        )
        self.manage_relations_button.pack(side="left", padx=(8, 0))
        ToolTip(
            self.manage_relations_button,
            "Apre la finestra di gestione delle relazioni socio-data sharing per attivare o disattivare le abilitazioni.",
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

        self.output_text = tk.Text(output_frame, wrap="word", height=14, state="disabled")
        self.output_text.grid(row=0, column=0, sticky="nsew")

        output_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        output_scroll.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=output_scroll.set)

        self._on_period_type_changed()
        self._render_soci_checkboxes([])
        self._update_run_button_state()

    def _load_datasharing_options(self):
        options = self.backend.get_sorted_options_for_current_tool()
        self.option_map = {
            self._format_option_label(option): option
            for option in options
        }
        labels = list(self.option_map.keys())
        self.datasharing_combo["values"] = labels
        self.datasharing_var.set("")
        self.selected_option = None
        self.status_var.set("Seleziona un data sharing per iniziare.")

    def _save_root_config_flag(self, flag_name, flag_value):
        config_path = self.backend.config.configs_file
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
        self.backend.config._debug = bool(is_debug_enabled)
        self.backend.dso_manager.config._debug = bool(is_debug_enabled)

        if getattr(self.backend.dso_manager, "_coca_cola_tracking_manager", None) is not None:
            self.backend.dso_manager._coca_cola_tracking_manager.debug_enabled = bool(is_debug_enabled)

    def _sync_runtime_summary_mail(self, is_summary_mail_enabled):
        self.backend.config._summary_mail_enabled = bool(is_summary_mail_enabled)
        self.backend.dso_manager.config._summary_mail_enabled = bool(is_summary_mail_enabled)

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
    def _format_socio_label(socio_code, socio_name):
        cleaned_name = str(socio_name or "").strip()
        if cleaned_name:
            return f"{socio_code} - {cleaned_name}"
        return str(socio_code)

    def _on_soci_frame_configure(self, event=None):
        self.soci_canvas.configure(scrollregion=self.soci_canvas.bbox("all"))

    def _on_soci_canvas_configure(self, event):
        self.soci_canvas.itemconfigure(self.soci_window, width=event.width)

    def _set_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, text)
        self.output_text.configure(state="disabled")

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
        self._refresh_soci()
        self._update_run_button_state()

    def _refresh_soci(self):
        if not self.selected_option:
            self.available_soci = []
            self._render_soci_checkboxes([])
            self.status_var.set("Seleziona un data sharing.")
            self._update_run_button_state()
            return

        try:
            soci_rows = self._load_enabled_soci(self.selected_option)
        except Exception as exc:
            self._render_soci_checkboxes([])
            self.status_var.set(f"Errore caricamento soci: {exc}")
            self._set_output(f"Errore caricamento soci per {self.selected_option.code}: {exc}")
            self._update_run_button_state()
            return

        self.available_soci = soci_rows
        self._render_soci_checkboxes(soci_rows)

        if soci_rows:
            self.status_var.set(f"Trovati {len(soci_rows)} soci abilitati per {self.selected_option.code}.")
        else:
            self.status_var.set(f"Nessun socio abilitato per {self.selected_option.code}.")
        self._update_run_button_state()

    def _load_enabled_soci(self, option):
        return self.backend.get_enabled_soci(option)

    def _get_filtered_soci(self):
        filter_value = self.socio_filter_var.get().strip().lower()
        if not filter_value:
            return self.available_soci

        filtered_rows = []
        for row in self.available_soci:
            socio_code = str(row.get("code", "")).strip().lower()
            socio_name = str(row.get("name", "")).strip().lower()
            if filter_value in socio_code or filter_value in socio_name:
                filtered_rows.append(row)

        return filtered_rows

    def _on_socio_filter_changed(self, event=None):
        self._render_soci_checkboxes(self._get_filtered_soci())
        self._update_run_button_state()

    def _render_soci_checkboxes(self, soci_rows):
        previous_selection = {
            socio_code: var.get()
            for socio_code, var in self.socio_check_vars.items()
        }

        for child in self.soci_frame.winfo_children():
            child.destroy()

        self.socio_check_vars = {}

        if not soci_rows:
            ttk.Label(self.soci_frame, text="Nessun socio disponibile.").grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        column_count = 3
        rows_per_column = max(1, math.ceil(len(soci_rows) / column_count))

        for column_index in range(column_count):
            self.soci_frame.columnconfigure(column_index, weight=1)

        for index, row in enumerate(soci_rows):
            socio_code = row["code"]
            socio_label = self._format_socio_label(socio_code, row["name"])
            var = tk.BooleanVar(value=previous_selection.get(socio_code, False))
            var.trace_add("write", self._on_socio_selection_changed)
            self.socio_check_vars[socio_code] = var

            row_index = index % rows_per_column
            column_index = index // rows_per_column
            ttk.Checkbutton(self.soci_frame, text=socio_label, variable=var).grid(
                row=row_index,
                column=column_index,
                sticky="w",
                padx=8,
                pady=2,
            )

    def _on_socio_selection_changed(self, *args):
        self._update_run_button_state()

    def _get_selected_socio_codes(self):
        return [socio_code for socio_code, var in self.socio_check_vars.items() if var.get()]

    def _select_all_soci(self):
        for var in self.socio_check_vars.values():
            var.set(True)
        self._update_run_button_state()

    def _clear_soci_selection(self):
        for var in self.socio_check_vars.values():
            var.set(False)
        self._update_run_button_state()

    def _is_period_ready(self):
        value = self.period_value_var.get().strip()
        expected_length = 4 if self.period_type_var.get() == "year" else 6

        if not value:
            return False

        if not value.isdigit() or len(value) != expected_length:
            return False

        try:
            self.backend.expand_periods(value)
            return True
        except ValueError:
            return False

    def _update_run_button_state(self):
        if self.is_processing:
            self.run_button.configure(state="disabled")
            return

        is_ready = bool(self.selected_option) and self._is_period_ready() and bool(self._get_selected_socio_codes())
        self.run_button.configure(state="normal" if is_ready else "disabled")

    def _open_socio_datasharing_management(self):
        if self.management_window is not None and self.management_window.window.winfo_exists():
            self.management_window.window.lift()
            self.management_window.window.focus_force()
            return

        self.management_window = SocioDataSharingManagementWindow(self)
        self.management_window.window.protocol("WM_DELETE_WINDOW", self._close_socio_datasharing_management)

    def _close_socio_datasharing_management(self):
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
            self._refresh_soci()
        elif self.selected_option is None:
            self.available_soci = []
            self._render_soci_checkboxes([])

        self._update_run_button_state()

    def _build_period_value(self):
        value = self.period_value_var.get().strip()
        expected_length = 4 if self.period_type_var.get() == "year" else 6

        if not value:
            raise ValueError("Inserire il periodo.")

        if not value.isdigit() or len(value) != expected_length:
            format_label = "YYYY" if expected_length == 4 else "YYYYMM"
            raise ValueError(f"Il periodo deve essere nel formato {format_label}.")

        self.backend.expand_periods(value)
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

            self.backend.expand_periods(value)
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
            raise ValueError("Selezionare un data sharing.")

        socio_codes = self._get_selected_socio_codes()
        if not socio_codes:
            raise ValueError("Selezionare almeno un socio abilitato.")

        period_value = self._build_period_value()
        return socio_codes, period_value

    def _set_running_state(self, is_running):
        self.is_processing = is_running
        state = "disabled" if is_running else "normal"
        combo_state = "disabled" if is_running else "readonly"

        self.datasharing_combo.configure(state=combo_state)
        self.period_entry.configure(state=state)
        self.debug_checkbutton.configure(state=state)
        for child in self.soci_frame.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass

        if not is_running and self.progress_var.get() < 100:
            self.progress_var.set(0)
            self.progress_text_var.set("0%")

        self._update_run_button_state()

    def _run_export(self):
        try:
            socio_codes, period_value = self._validate_selection()
        except ValueError as exc:
            messagebox.showerror("Validazione", str(exc), parent=self.root)
            return

        option = self.selected_option
        self._last_run_started_at = datetime.now()
        self._set_running_state(True)
        self.progress_var.set(0)
        self.progress_text_var.set("0%")
        self.status_var.set(
            f"Elaborazione in corso per {option.code}, soci selezionati: {len(socio_codes)}, periodo {period_value}."
        )
        self._set_output(
            "ESECUZIONE STEP BY STEP\n"
            + "=" * 60
            + f"\nData sharing: {option.code} - {option.name}"
            + f"\nPeriodo richiesto: {period_value}"
            + f"\nSoci selezionati: {len(socio_codes)}\n\n"
        )

        worker = threading.Thread(
            target=self._run_export_worker,
            args=(socio_codes, period_value, option),
            daemon=True,
        )
        worker.start()

    def _run_export_worker(self, socio_codes, period_value, option):
        try:
            periods = self.backend.expand_periods(period_value)
            send_summary_mail = len(periods) == 1
            total_steps = max(1, len(socio_codes) * max(1, len(periods)))
            completed_steps = 0
            self.root.after(
                0,
                lambda: self._append_output(
                    f"Periodi da elaborare: {', '.join(periods)}\n" if periods else "Nessun periodo da elaborare.\n"
                ),
            )
            results = []
            for socio_index, socio_code in enumerate(socio_codes, start=1):
                self.root.after(
                    0,
                    lambda s=socio_code, idx=socio_index, total=len(socio_codes): self._append_output(
                        f"\n[{idx}/{total}] Avvio socio {s}\n"
                    ),
                )

                socio_period_results = []
                for period_index, single_period in enumerate(periods, start=1):
                    self.root.after(
                        0,
                        lambda s=socio_code, p=single_period, idx=period_index, total=len(periods): self._append_output(
                            f"  - Periodo {idx}/{total}: {p} in elaborazione...\n"
                        ),
                    )
                    result = self.backend.dso_manager.process_data(
                        socio_code,
                        single_period,
                        option,
                        send_summary_mail=send_summary_mail,
                    )
                    socio_period_results.append(result)
                    completed_steps += 1
                    self.root.after(
                        0,
                        lambda s=socio_code, p=single_period, r=result, done=completed_steps, total=total_steps: self._on_period_step_completed(
                            s,
                            p,
                            r,
                            done,
                            total,
                        ),
                    )

                aggregated_result = self.backend.build_aggregated_result(socio_code, periods, option, socio_period_results)
                if len(periods) > 1:
                    socio_data = self.backend.dso_manager.verify_socio(socio_code, option.code)
                    self.backend.dso_manager.send_aggregated_summary_mail(
                        socio_code,
                        periods,
                        option,
                        socio_data,
                        aggregated_result,
                        socio_period_results,
                    )
                results.append((socio_code, aggregated_result))
                self.root.after(
                    0,
                    lambda s=socio_code, r=aggregated_result: self._append_output(
                        f"  Completato socio {s}: {'OK' if r.get('success') else 'KO'}"
                        + (f" | Output: {r.get('output_file')}" if r.get('output_file') else "")
                        + "\n"
                    ),
                )
            self.root.after(0, lambda: self._handle_result(results, period_value, option))
        except Exception as exc:
            self.root.after(0, lambda: self._handle_error(exc))

    def _on_period_step_completed(self, socio_code, single_period, result, completed_steps, total_steps):
        self._append_output(
            f"    Esito periodo {single_period}: {'OK' if result.get('success') else 'KO'}"
            + (f" | File: {result.get('output_file')}" if result.get('output_file') else "")
            + "\n"
        )
        self._update_progress(
            completed_steps,
            total_steps,
            f"Avanzamento {completed_steps}/{total_steps} - socio {socio_code}, periodo {single_period}",
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
            f"Soci elaborati: {processed_count}",
            f"Soci con esito OK: {success_count}",
            f"Soci con esito KO: {failure_count}",
            f"Avvio elaborazione: {self._last_run_started_at.strftime('%d/%m/%Y %H:%M:%S') if self._last_run_started_at else ''}",
            f"Fine elaborazione: {run_finished_at.strftime('%d/%m/%Y %H:%M:%S')}",
        ]

        if duration_text:
            lines.append(f"Durata: {duration_text}")

        lines.append("")
        lines.append("DETTAGLIO PER SOCIO")
        lines.append("-" * 60)

        for socio_code, result in results:
            lines.append("")
            lines.append(f"Socio: {socio_code}")
            lines.append(f"Esito socio: {'OK' if result.get('success') else 'KO'}")
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
        self.root.mainloop()


def _show_startup_error(message):
    dialog_root = tk.Tk()
    dialog_root.withdraw()
    try:
        messagebox.showerror("DataSharing", message, parent=dialog_root)
    finally:
        dialog_root.destroy()


def main():
    try:
        ActiveDirectoryAuthorizationManager().ensure_current_user_is_authorized()
    except AuthorizationError as exc:
        _show_startup_error(str(exc))
        return

    app = DataSharingWindowsApp()
    app.run()


if __name__ == "__main__":
    main()