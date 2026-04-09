import datetime

from managers.data_owner_manager import DataSharingOwnerManager
from managers.log_manager import LogManager
from services.config import Config
from services.data_sharing_config import DataSharingOption, Option


class DataSharingRuntime:
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

    def expand_periods(self, period):
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

    def process_periods_for_socio(self, socio, periods, config_ds: Option):
        results = []
        send_summary_mail = len(periods) == 1
        for single_period in periods:
            results.append(self.dso_manager.process_data(socio, single_period, config_ds, send_summary_mail=send_summary_mail))

        aggregated_result = self.build_aggregated_result(socio, periods, config_ds, results)
        if len(periods) > 1:
            socio_data = self.dso_manager.verify_socio(socio, config_ds.code)
            self.dso_manager.send_aggregated_summary_mail(socio, periods, config_ds, socio_data, aggregated_result, results)

        return aggregated_result

    def build_aggregated_result(self, socio, periods, config_ds: Option, results):
        if not results:
            return {
                "success": False,
                "message": f"Nessun risultato disponibile per socio {socio}, data sharing {config_ds.code}.",
                "output_file": None,
            }

        if len(results) == 1:
            return results[0]

        successful_results = [result for result in results if result.get("success")]
        output_files = [result.get("output_file") for result in successful_results if result.get("output_file")]
        success = len(successful_results) == len(results)
        message = (
            f"Elaborazione annuale completata per socio {socio}, data sharing {config_ds.code}. "
            f"Periodi elaborati: {len(successful_results)}/{len(results)}."
        )
        return {
            "success": success,
            "message": message,
            "output_file": ";".join(output_files) if output_files else None,
        }

    def get_sorted_options(self):
        return sorted(self.ds_option.options, key=lambda item: (item.code or "", item.name or ""))

    def get_sorted_options_for_current_tool(self):
        allowed_codes = set(self.dso_manager.db_manager.get_datasharing_codes_for_current_tool())
        return [option for option in self.get_sorted_options() if option.code in allowed_codes]

    def get_enabled_soci(self, option: Option):
        return self.dso_manager.db_manager.get_enabled_soci_for_datasharing(option.code)
    
   
    def get_logging_dataframe(self, cod_socio=None, cod_datasharing=None, num_periodo=None, cod_stato=None, tms_invio=None):
        """Restituisce un DataFrame pandas filtrato per i parametri forniti.
        """
        return self.dso_manager.db_manager.get_logging_dataframe(
            cod_socio=cod_socio,
            cod_datasharing=cod_datasharing,
            num_periodo=num_periodo,
            cod_stato=cod_stato,
            tms_invio=tms_invio,
        )


    def get_socio_datasharing_relations(self, socio=None, datasharing_code=None, only_enabled=False, only_current_tool=False):
        return self.dso_manager.db_manager.get_socio_datasharing_relations(
            socio=socio,
            datasharing_code=datasharing_code,
            only_enabled=only_enabled,
            only_current_tool=only_current_tool,
        )

    def set_socio_datasharing_enabled(self, socio, datasharing_code, is_enabled, socio_name=None, datasharing_name=None):
        return self.dso_manager.db_manager.set_socio_datasharing_enabled(
            socio,
            datasharing_code,
            is_enabled,
            socio_name=socio_name,
            datasharing_name=datasharing_name,
        )

    def set_socio_datasharing_tool_enabled(self, socio, datasharing_code, use_new_tool, socio_name=None, datasharing_name=None):
        return self.dso_manager.db_manager.set_socio_datasharing_tool_enabled(
            socio,
            datasharing_code,
            use_new_tool,
            socio_name=socio_name,
            datasharing_name=datasharing_name,
        )

    def update_socio_datasharing_configuration(
        self,
        socio,
        datasharing_code,
        use_new_tool,
        wholesaler_id=None,
        socio_name=None,
        datasharing_name=None,
    ):
        return self.dso_manager.db_manager.update_socio_datasharing_configuration(
            socio,
            datasharing_code,
            use_new_tool,
            wholesaler_id=wholesaler_id,
            socio_name=socio_name,
            datasharing_name=datasharing_name,
        )