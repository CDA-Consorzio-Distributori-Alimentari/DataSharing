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
        for single_period in periods:
            results.append(self.dso_manager.process_data(socio, single_period, config_ds))

        return self.build_aggregated_result(socio, periods, config_ds, results)

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

    def get_enabled_soci(self, option: Option):
        query = f"""
            SELECT
                [TC_Soci_Codice],
                [TC_Soci_Ragione_Sociale]
            FROM [cda].[dbo].[TC_Soci]
            WHERE [TC_Soci_Socio_Attivo] = 1
              AND [{option.campo}] = 1
            ORDER BY [TC_Soci_Codice]
        """
        data = self.dso_manager.db_manager.fetch_all(query)
        soci_rows = []
        for _, row in data.iterrows():
            socio_code = str(row.get("TC_Soci_Codice", "")).strip()
            if not socio_code:
                continue

            soci_rows.append(
                {
                    "code": socio_code,
                    "name": str(row.get("TC_Soci_Ragione_Sociale", "")).strip(),
                }
            )

        return soci_rows