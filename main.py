from services.data_sharing_config import DataSharingOption, Option
from managers.active_directory_authorization_manager import (
    ActiveDirectoryAuthorizationManager,
    AuthorizationError,
    show_authorization_error_and_exit,
)
from managers.data_owner_manager import DataSharingOwnerManager
from services.config import Config
import datetime
import argparse
from managers.log_manager import LogManager




class DataSharing:
    def __init__(self):
        self.config = Config()
        self.ds_option = DataSharingOption()
        self.dso_manager = DataSharingOwnerManager()   
        self.log = LogManager(self.config.log_file, self.config.log_level)

    @staticmethod
    def _max_allowed_period_date():
        max_date = datetime.datetime.today().replace(day=1) - datetime.timedelta(days=1)
        return max_date.replace(day=1)

    @staticmethod
    def _max_available_month_for_yearly_request(current_date):
        if current_date.day >= 20:
            return current_date.month - 1
        return current_date.month - 2

    def _expand_periods(self, period):
        period_value = str(period).strip()
        max_period_date = self._max_allowed_period_date()

        if len(period_value) == 6:
            period_date = datetime.datetime.strptime(period_value, "%Y%m")
            if period_date > max_period_date:
                raise ValueError("Il periodo non può essere superiore a oggi meno un mese.")
            return [period_value]

        if len(period_value) == 4:
            year_value = int(period_value)
            if year_value > max_period_date.year:
                raise ValueError("L'anno non può essere superiore all'anno corrente disponibile.")

            max_month = 12
            if year_value == max_period_date.year:
                current_date = datetime.datetime.today()
                max_month = self._max_available_month_for_yearly_request(current_date)
                if max_month < 1:
                    raise ValueError(
                        f"Per l'anno corrente {year_value} non esistono ancora mesi elaborabili."
                    )

            return [f"{year_value}{month:02d}" for month in range(1, max_month + 1)]

        raise ValueError("Il periodo deve essere nel formato YYYYMM oppure YYYY.")

    def _process_periods_for_socio(self, socio, periods, config_ds: Option):
        results = []
        send_summary_mail = len(periods) == 1
        for single_period in periods:
            results.append(self.dso_manager.process_data(socio, single_period, config_ds, send_summary_mail=send_summary_mail))

        if len(results) == 1:
            return results[0]

        successful_results = [result for result in results if result.get("success")]
        output_files = [result.get("output_file") for result in successful_results if result.get("output_file")]
        success = len(successful_results) == len(results)
        message = (
            f"Elaborazione annuale completata per socio {socio}, data sharing {config_ds.code}. "
            f"Periodi elaborati: {len(successful_results)}/{len(results)}."
        )
        aggregated_result = {
            "success": success,
            "message": message,
            "output_file": ";".join(output_files) if output_files else None,
        }
        socio_data = self.dso_manager.verify_socio(socio, config_ds.code)
        self.dso_manager.send_aggregated_summary_mail(socio, periods, config_ds, socio_data, aggregated_result, results)
        return aggregated_result

    def _process_periods_for_all_soci(self, periods, config_ds: Option):
        processed_count = 0
        send_summary_mail = len(periods) == 1
        for socio_row in self.dso_manager.db_manager.get_enabled_soci_for_datasharing(config_ds.code):
            socio_item = socio_row["code"]
            socio_data = self.dso_manager.verify_socio(socio_item)
            if socio_data is None or socio_data.empty:
                continue

            socio_results = []
            for single_period in periods:
                socio_results.append(
                    self.dso_manager.process_data(
                        socio_item,
                        single_period,
                        config_ds,
                        send_summary_mail=send_summary_mail,
                    )
                )
                processed_count += 1

            if len(periods) > 1 and socio_results:
                successful_results = [result for result in socio_results if result.get("success")]
                output_files = [result.get("output_file") for result in successful_results if result.get("output_file")]
                aggregated_result = {
                    "success": len(successful_results) == len(socio_results),
                    "message": (
                        f"Elaborazione annuale completata per socio {socio_item}, data sharing {config_ds.code}. "
                        f"Periodi elaborati: {len(successful_results)}/{len(socio_results)}."
                    ),
                    "output_file": ";".join(output_files) if output_files else None,
                }
                self.dso_manager.send_aggregated_summary_mail(
                    socio_item,
                    periods,
                    config_ds,
                    socio_data,
                    aggregated_result,
                    socio_results,
                )

        return processed_count

    def validate_period(self, period, interactive=True):
        while True:
            try:
                self._expand_periods(period)
                return True
            except ValueError as e:
                self.log.error(f"Errore: {e}")
                if not interactive:
                    return False
                period = input("Inserisci nuovamente il periodo (formato: YYYYMM oppure YYYY): ")

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
            periodo = input("Inserisci il periodo (formato: YYYYMM oppure YYYY): ")
            if periodo.upper() == "E":
                return None
            if self.validate_period(periodo):
                return periodo

    def choose_data_sharing(self, socio_data):
        socio_row = self.dso_manager._get_socio_row(socio_data)
        socio_code = str(socio_row.get("TC_Soci_Codice", "") or "").strip()
        enabled_codes = set(self.dso_manager.db_manager.get_enabled_datasharing_codes_for_socio(socio_code))
        active_data_sharing = []
        for option in self.ds_option.options:
            if option.code in enabled_codes:
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

        periods = self._expand_periods(periodo)
        result = self._process_periods_for_socio(socio, periods, option)

        # Log the operation
        self.log.info(result["message"])

    def print_data_sharing_list(self):
        print("DATA SHARING DISPONIBILI:")
        managed_codes = set(self.dso_manager.db_manager.get_datasharing_codes_for_current_tool())
        for option in sorted(self.ds_option.options, key=lambda item: (item.code or "", item.name or "")):
            if option.code not in managed_codes:
                continue
            print(f"- {option.code} | {option.name} | {option.file_type}")

    def command_line_mode(self):
        parser = argparse.ArgumentParser(description="Data Sharing Script")
        parser.add_argument("--version", action="version", version=f"DataSharing {self.config.version}")
        parser.add_argument("--period", help="Periodo obbligatorio (formato: YYYYMM oppure YYYY)")
        parser.add_argument("--datasharing", help="Codice del data sharing")
        parser.add_argument("--socio", help="Codice socio (opzionale)")
        parser.add_argument("--code", help="Codice 'CC001' per configurazioni avanzate")
        parser.add_argument("--list-datasharing", action="store_true", help="Mostra l'elenco dei data sharing disponibili")
        args = parser.parse_args()

        if args.list_datasharing:
            self.print_data_sharing_list()
            return

        if not args.period or not args.datasharing:
            parser.error("--period e --datasharing sono obbligatori")

        socio_data = None
        socio = args.socio
        periodo = args.period
        datasharing_name = args.datasharing

        # Validate period
        if not self.validate_period(periodo, interactive=False):
            return
        periods = self._expand_periods(periodo)

        # Filter data sharing options
        config_ds : Option = None
        for option in self.ds_option.options:
            if option.code == datasharing_name:
                config_ds = option
                break

        if not config_ds:
            self.log.error(f"Data sharing '{datasharing_name}' non trovato. Uscita.")
            return

        if config_ds.code not in set(self.dso_manager.db_manager.get_datasharing_codes_for_current_tool()):
            self.log.warning(f"Il data sharing '{datasharing_name}' non e' gestito da questo programma. Uscita.")
            return

        # If socio is provided, validate it
        if socio:
            socio_data = self.dso_manager.verify_socio(socio)
            if socio_data is None or socio_data.empty:
                self.log.error("Il socio non è attivo o non esiste. Uscita.")
                return

            if self.dso_manager.db_manager.is_socio_enabled_for_datasharing(socio, config_ds.code):
                result = self._process_periods_for_socio(socio, periods, config_ds)
                self.log.info(result["message"])
            else:
                if not self.dso_manager.db_manager.uses_current_tool_for_datasharing(socio, config_ds.code):
                    self.log.warning(
                        f"Il socio {socio} per il data sharing '{datasharing_name}' deve usare lo strumento vecchio. Uscita."
                    )
                else:
                    self.log.warning(f"Il socio {socio} non è abilitato per il data sharing '{datasharing_name}'. Uscita.")
        else:
            # Process for all enabled soci
            processed_count = self._process_periods_for_all_soci(periods, config_ds)
            self.log.info(f"Elaborazione completata per tutti i soci abilitati. Esportazioni eseguite: {processed_count}.")

    def main(self):
        import sys
        if len(sys.argv) > 1:
            if any(arg.lower() in ["?", "/?", "help", "--help", "aiuto"] for arg in sys.argv):
                print("USO:")
                print(f"Versione: {self.config.version}")
                print("--period <YYYYMM|YYYY> (Obbligatorio, primo parametro):")
                print("  - YYYYMM genera solo il mese specificato, anche se richiesto esplicitamente prima del giorno 20.")
                print("  - YYYY genera l'anno completo se è un anno chiuso.")
                print("  - Se YYYY è l'anno corrente, fino al giorno 19 genera fino a mese corrente meno 2.")
                print("  - Dal giorno 20 in poi, per YYYY genera fino a mese corrente meno 1.")
                print("--datasharing <Codice> (Obbligatorio, secondo parametro): Specifica il codice del data sharing.")
                print("--socio <Codice> (Opzionale, terzo parametro): Specifica il codice socio. Se non fornito, verranno elaborati tutti i soci abilitati.")
                print("--code <Codice> (Obbligatorio, quarto parametro): Specifica il codice \"CC001\" per configurazioni avanzate.")
                print("--list-datasharing: Mostra l'elenco dei data sharing disponibili.")
                self.print_data_sharing_list()
                print("MODALITÀ:")
                print("- Se vengono forniti parametri da riga di comando, il programma li utilizza automaticamente.")
                print("- Se non vengono forniti parametri, il programma entra in modalità interattiva.")
                print("ESEMPIO DI UTILIZZO:")
                print("--list-datasharing")
                print("Questo comando mostra l'elenco dei data sharing disponibili.")
                print("--period 202401 --datasharing CC001 --socio 12345")
                print("Questo comando elabora gennaio 2024 per il socio 12345.")
                print("--period 2024 --datasharing CC001 --socio 12345")
                print("Questo comando elabora tutto il 2024 per il socio 12345.")
                print("Se l'anno indicato è quello corrente, il ciclo include il mese precedente solo dal giorno 20 del mese attuale.")
                return
            self.command_line_mode()
        else:
            self.interactive_mode()


def main():
    try:
        ActiveDirectoryAuthorizationManager().ensure_current_user_is_authorized()
    except AuthorizationError as exc:
        show_authorization_error_and_exit(str(exc))

    app = DataSharing()
    app.main()


if __name__ == "__main__":
    main()