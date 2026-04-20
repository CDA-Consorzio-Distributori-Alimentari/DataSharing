from services.data_sharing_config import DataSharingOption, Option
from managers.data_owner_manager import DataSharingOwnerManager


class DataSharingService:
    def __init__(self, manager=None):
        self.dso_manager = manager or DataSharingOwnerManager()
        self.ds_option = DataSharingOption()

    def get_option_by_code(self, code) -> Option | None:
        for option in self.ds_option.options:
            if option.code == code:
                return option
        return None

    def is_option_managed_by_current_tool(self, code):
        allowed_codes = set(self.dso_manager.db_manager.get_datasharing_codes_for_current_tool())
        return str(code or "").strip() in allowed_codes

    def get_active_options(self, socio_data):
        socio_code = ""
        if hasattr(socio_data, "empty") and not socio_data.empty:
            socio_code = str(socio_data.iloc[0].get("TC_Soci_Codice", "") or "").strip()
        elif hasattr(socio_data, "get"):
            socio_code = str(socio_data.get("TC_Soci_Codice", "") or "").strip()

        enabled_codes = set(self.dso_manager.db_manager.get_enabled_datasharing_codes_for_socio(socio_code))
        active_data_sharing = []
        for option in self.ds_option.options:
            if option.code in enabled_codes:
                active_data_sharing.append(option)
        return active_data_sharing

    def run_export(self, socio, periodo, datasharing_code):
        option = self.get_option_by_code(datasharing_code)
        if not option:
            return {
                "success": False,
                "message": f"Data sharing '{datasharing_code}' non trovato.",
                "output_file": None,
            }

        if not self.is_option_managed_by_current_tool(datasharing_code):
            return {
                "success": False,
                "message": f"Il data sharing '{datasharing_code}' non e' gestito da questo programma.",
                "output_file": None,
            }

        socio_data = self.dso_manager.verify_socio(socio)
        if socio_data is None or socio_data.empty:
            return {
                "success": False,
                "message": "Il socio non è attivo o non esiste.",
                "output_file": None,
            }

        if not self.dso_manager.db_manager.is_socio_enabled_for_datasharing(socio, option.code):
            if not self.dso_manager.db_manager.uses_current_tool_for_datasharing(socio, option.code):
                return {
                    "success": False,
                    "message": f"Il socio {socio} per il data sharing '{datasharing_code}' deve usare lo strumento vecchio.",
                    "output_file": None,
                }
            return {
                "success": False,
                "message": f"Il socio {socio} non è abilitato per il data sharing '{datasharing_code}'.",
                "output_file": None,
            }

        return self.dso_manager.main_process_data(socio, periodo, option)