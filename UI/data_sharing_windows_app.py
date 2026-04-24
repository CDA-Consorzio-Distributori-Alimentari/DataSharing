import tkinter as tk
from tkinter import ttk, messagebox
import math
import json
from services.data_sharing_runtime import DataSharingRuntime

import threading
from datetime import datetime
from .tool_tip import ToolTip
#from .socio_datasharing_management_window import SocioDataSharingManagementWindow
from .tabella_logging_windows import TabellaLoggingWindows


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
        self.selected_soci = set()
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

        if hasattr(self, "soci_canvas"):
            self.soci_canvas.configure(background=background)

    def _build_ui(self):
        import sys
        from .data_sharing_selector import main_selector_window

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

        def close_and_return():
            self.root.destroy()
            main_selector_window()

        btn_close = ttk.Button(header_right_frame, text="Chiudi", command=close_and_return, style="Red.TButton")
        btn_close.pack(side="right", padx=(8, 0))

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

        action_frame = ttk.Frame(container, padding=(0, 12, 0, 12))
        action_frame.grid(row=2, column=0, sticky="ew")

        self.run_button = ttk.Button(
            action_frame, 
            text="Avvia elaborazione", 
            command=self._run_export
        )
        
        self.run_button.pack(side="left")
        ToolTip(self.run_button, "Si abilita solo quando data sharing, periodo e almeno un socio sono validi.")


        self.manage_relations_button = ttk.Button(
            action_frame,
            text="Gestione abilitazioni",
            command=self._open_socio_datasharing_management,
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
            "Apre la finestra di gestione delle relazioni socio-data sharing per attivare o disattivare le abilitazioni.",
        )
        ToolTip(
            self.tabella_logging_button,
            "Apre la finestra della tabella di logging per visualizzare i dettagli delle elaborazioni.",
        )
       
    def _open_socio_period_datasharing_window(self):
        from .datasharing_socio_management_window import DataSharingSocioManagementWindow
        DataSharingSocioManagementWindow(self)

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
        # Reset selezione soci solo su cambio data sharing o refresh
        self.selected_soci = set()

        if not self.selected_option:
            self.available_soci = []
            self._render_soci_checkboxes()
            self.status_var.set("Seleziona un data sharing.")
            self._update_run_button_state()
            return

        try:
            soci_rows = self._load_enabled_soci(self.selected_option)
        except Exception as exc:
            self._render_soci_checkboxes()
            self.status_var.set(f"Errore caricamento soci: {exc}")
            self._set_output(f"Errore caricamento soci per {self.selected_option.code}: {exc}")
            self._update_run_button_state()
            return

        self.available_soci = soci_rows
        self._render_soci_checkboxes()

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
        # Non azzera la selezione, mantiene self.selected_soci
        self._render_soci_checkboxes()
        self._update_run_button_state()

    def _render_soci_checkboxes(self):
        # Consulta sempre self.selected_soci
        selected_soci = self.selected_soci

        filtered_soci = self._get_filtered_soci()

        for child in self.soci_frame.winfo_children():
            child.destroy()

        self.socio_check_vars = {}

        if not filtered_soci:
            ttk.Label(self.soci_frame, text="Nessun socio disponibile.").grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        column_count = 3
        rows_per_column = max(1, math.ceil(len(filtered_soci) / column_count))

        for column_index in range(column_count):
            self.soci_frame.columnconfigure(column_index, weight=1)

        for index, row in enumerate(filtered_soci):
            socio_code = row["code"]
            socio_label = self._format_socio_label(socio_code, row["name"])
            var = tk.BooleanVar(value=(socio_code in selected_soci))
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
        # Aggiorna solo il socio effettivamente modificato
        if args:
            changed_var_name = args[0]
            for socio_code, var in self.socio_check_vars.items():
                if var._name == changed_var_name:
                    if socio_code in self.selected_soci:
                        self.selected_soci.discard(socio_code)
                    else:
                        self.selected_soci.add(socio_code)
                    break
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
        prev_state = getattr(self, '_prev_run_button_state', None)
        if self.is_processing:
            self.run_button.configure(state="disabled")
            self.run_button.pack_forget()
            self.run_button.pack(side="left")
            self.run_button.configure(style="Red.TButton")
            if prev_state != "processing":
                self.status_var.set("Elaborazione in corso: pulsante disabilitato.")
            self._prev_run_button_state = "processing"
            return

        missing = []
        if not self.selected_option:
            missing.append("data sharing")
        if not self._is_period_ready():
            missing.append("periodo")
        if not self._get_selected_socio_codes():
            missing.append("soci")

        is_ready = not missing
        if is_ready:
            self.run_button.pack_forget()
            self.run_button.pack(side="left")
            self.run_button.configure(state="normal", style="TButton")
            if prev_state != "normal":
                self.status_var.set("Pronto per avviare l'elaborazione.")
            self._prev_run_button_state = "normal"
        else:
            self.run_button.pack_forget()
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
            self._render_soci_checkboxes()

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

        socio_codes = self._get_selected_socio_codes()
        if not socio_codes:
            messagebox.showerror("Validazione", "Selezionare almeno un socio abilitato.", parent=self.root)
            raise ValueError("Selezionare almeno un socio abilitato.")

        period_value = self._build_period_value()
        return socio_codes, period_value

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
        self.socio_filter_entry.configure(state=state)
        for child in self.soci_frame.winfo_children():
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
                    result = self.backend.dso_manager.main_process_data(
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
        try:
            self.root.mainloop()
        except Exception as exc:
            # Protezione: non stampare nulla, solo mostrare errore grafico
            messagebox.showerror("DataSharing", str(exc), parent=self.root)