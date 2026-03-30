import sqlite3
import csv
import xml.etree.ElementTree as ET
import json
import config
from data_sharing_config import DataSharingOption, Option
from managers.data_owner_manager import DataSharingOwnerManager
from config import Config
import datetime
import argparse
import json
import os
from log_manager import LogManager




class DataSharing:
    def __init__(self):
        
        self.ds_option = DataSharingOption()
        self.dso_manager = DataSharingOwnerManager()   
        self.log = LogManager(Config().log_file)

    def validate_period(self, period, interactive=True):
        while True:
            try:
                # Parse the period as YYYYMM
                period_date = datetime.datetime.strptime(period, "%Y%m")
                # Calculate the maximum allowed date (today minus one month)
                max_date = datetime.datetime.today().replace(day=1) - datetime.timedelta(days=1)
                max_date = max_date.replace(day=1)
                if period_date > max_date:
                    raise ValueError("Il periodo non può essere superiore a oggi meno un mese.")
                return True
            except ValueError as e:
                self.log.error(f"Errore: {e}")
                if not interactive:
                    return False
                period = input("Inserisci nuovamente il periodo (formato: YYYYMM): ")

    def choose_socio(self):
        while True:
            socio = input("Inserisci il codice socio (E per uscire, L per lista dei soci): ")

            if socio.upper() == "E":
                self.log.info("Uscita dal programma.")
                return None

            if socio.upper() == "L":
                soci_list = self.dso_manager.get_soci_list()
                self.log.info("Lista dei soci disponibili:")
                for socio_item in soci_list:
                    self.log.info(f"- {socio_item}")
                continue

            socio_data = self.dso_manager.verify_socio(socio)

            if socio_data is None or socio_data.empty:
                self.log.warning("Il socio non è attivo o non esiste. Riprova.")
                continue

            return socio, socio_data

    def choose_period(self):
        while True:
            periodo = input("Inserisci il periodo (formato: YYYYMM): ")
            if periodo.upper() == "E":
                return None
            if self.validate_period(periodo):
                return periodo

    def choose_data_sharing(self, socio_data):
        active_data_sharing = []
        for option in self.ds_option.options:
            campo_value = socio_data[option.campo].iloc[0] if option.campo in socio_data.columns else 0

            if campo_value == 1:
              active_data_sharing.append(option)                

        if not active_data_sharing:
            self.log.warning("Nessun data sharing attivo per il socio selezionato.")
            return None

        self.log.info("Tipi di data sharing disponibili:")
        for i, option in enumerate(active_data_sharing):
            self.log.info(f"{i + 1}. {option.code}  {option.name} ({option.file_type})")

        while True:
            try:
                tipo_data_sharing_index = int(input("Seleziona il tipo di data sharing: ")) - 1
                if 0 <= tipo_data_sharing_index < len(active_data_sharing):
                    return active_data_sharing[tipo_data_sharing_index]
                else:
                    self.log.warning("Indice non valido. Riprova.")
            except ValueError:
                self.log.warning("Input non valido. Inserisci un numero.")

    def interactive_mode(self):
        socio_data = None
        socio = None

        # Step 1: Choose socio
        result = self.choose_socio()
        if result is None:
            return
        socio, socio_data = result

        # Step 2: Choose period
        periodo = self.choose_period()
        if periodo is None:
            return

        # Step 3: Choose data sharing
        option = self.choose_data_sharing(socio_data)
        if option is None:
            return

        result = self.dso_manager.process_data(socio, periodo, option)

        # Log the operation
        self.log.info(result["message"])

    def command_line_mode(self):
        parser = argparse.ArgumentParser(description="Data Sharing Script")
        parser.add_argument("--auto", action="store_true", help="Legge i job da una tabella di controllo e li esegue automaticamente")
        parser.add_argument("--period", help="Periodo obbligatorio (formato: YYYYMM)")
        parser.add_argument("--datasharing", help="Codice del data sharing")
        parser.add_argument("--socio", help="Codice socio (opzionale)")
        parser.add_argument("--code", help="Codice 'CC001' per configurazioni avanzate")
        args = parser.parse_args()

        if args.auto:
            self.auto_mode()
            return

        if not args.period or not args.datasharing:
            parser.error("--period e --datasharing sono obbligatori se non usi --auto")

        socio_data = None
        socio = args.socio
        periodo = args.period
        datasharing_name = args.datasharing

        # Validate period
        if not self.validate_period(periodo, interactive=False):
            return

        # Filter data sharing options
        config_ds : Option = None
        for option in self.ds_option.options:
            if option.code == datasharing_name:
                config_ds = option
                break

        if not config_ds:
            self.log.error(f"Data sharing '{datasharing_name}' non trovato. Uscita.")
            return

        # If socio is provided, validate it
        if socio:
            socio_data = self.dso_manager.verify_socio(socio)
            if socio_data is None or socio_data.empty:
                self.log.error("Il socio non è attivo o non esiste. Uscita.")
                return


            
            campo_value = socio_data[config_ds.campo].iloc[0] if config_ds.campo in socio_data.columns else 0

            if campo_value == 1:
                result = self.dso_manager.process_data(socio, periodo, config_ds)
                self.log.info(result["message"])
            else:
                self.log.warning(f"Il socio {socio} non è abilitato per il data sharing '{datasharing_name}'. Uscita.")
        else:
            # Process for all enabled soci
            soci_list = self.dso_manager.get_soci_list()
            for socio_item in soci_list:
                socio_data = self.dso_manager.verify_socio(socio_item)
                if socio_data is not None and not socio_data.empty and socio_data[config_ds.campo].iloc[0] == 1:
                    self.dso_manager.process_data(socio_item, periodo, config_ds)
            self.log.info("Elaborazione completata per tutti i soci abilitati.")

    def auto_mode(self):
        processed_jobs = 0
        while True:
            job = self.dso_manager.claim_next_auto_job()
            if not job:
                if processed_jobs == 0:
                    self.log.info("Nessun job in stato INS da elaborare.")
                else:
                    self.log.info(f"Elaborazione automatica completata. Job processati: {processed_jobs}.")
                return

            socio = str(job.get("socio", "")).strip()
            periodo = str(job.get("periodo", "")).strip()
            datasharing_name = str(job.get("datasharing", "")).strip()

            self.log.info(
                f"Avvio job automatico socio={socio}, periodo={periodo}, datasharing={datasharing_name}."
            )

            try:
                config_ds: Option = None
                for option in self.ds_option.options:
                    if option.code == datasharing_name:
                        config_ds = option
                        break

                if not config_ds:
                    raise ValueError(f"Data sharing '{datasharing_name}' non trovato")

                if not self.validate_period(periodo, interactive=False):
                    raise ValueError(f"Periodo non valido: {periodo}")

                socio_data = self.dso_manager.verify_socio(socio)
                if socio_data is None or socio_data.empty:
                    raise ValueError(f"Il socio {socio} non è attivo o non esiste")

                campo_value = socio_data[config_ds.campo].iloc[0] if config_ds.campo in socio_data.columns else 0
                if campo_value != 1:
                    raise ValueError(
                        f"Il socio {socio} non è abilitato per il data sharing '{datasharing_name}'"
                    )

                result = self.dso_manager.process_data(socio, periodo, config_ds)
                self.dso_manager.complete_auto_job(
                    job,
                    result.get("success", False),
                    output_file=result.get("output_file"),
                    message=result.get("message"),
                )
                self.log.info(result.get("message"))
            except Exception as exc:
                self.dso_manager.complete_auto_job(job, False, output_file=None, message=str(exc))
                self.log.error(f"Errore job automatico: {exc}")

            processed_jobs += 1

    def main(self):
        import sys
        if len(sys.argv) > 1:
            if any(arg.lower() in ["?", "/?", "help", "--help", "aiuto"] for arg in sys.argv):
                print("USO:")
                print("--auto: Legge i job da tabella e li elabora automaticamente.")
                print("--period <YYYYMM> (Obbligatorio, primo parametro): Specifica il periodo in formato YYYYMM.")
                print("--datasharing <Codice> (Obbligatorio, secondo parametro): Specifica il codice del data sharing.")
                print("--socio <Codice> (Opzionale, terzo parametro): Specifica il codice socio. Se non fornito, verranno elaborati tutti i soci abilitati.")
                print("--code <Codice> (Obbligatorio, quarto parametro): Specifica il codice \"CC001\" per configurazioni avanzate.")
                print("DATA SHARING DISPONIBILI:")
                for option in self.ds_option.options:
                    print(f"- {option.name} ({option.file_type})")
                print("MODALITÀ:")
                print("- Se vengono forniti parametri da riga di comando, il programma li utilizza automaticamente.")
                print("- Se non vengono forniti parametri, il programma entra in modalità interattiva.")
                print("ESEMPIO DI UTILIZZO:")
                print("--period 202401 --datasharing \"Vendite\" --socio 12345")
                print("Questo comando elabora i dati di vendita per il socio con codice 12345 per il periodo di gennaio 2024.")
                return
            self.command_line_mode()
        else:
            self.interactive_mode()


if __name__ == "__main__":
    f= DataSharing()
    f.main()