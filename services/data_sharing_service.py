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

    def get_active_options(self, socio_data):
        active_data_sharing = []
        for option in self.ds_option.options:
            if socio_data.get(f"TC_Soci_{option.name.replace(' ', '_')}_Attivo", 0):
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

        socio_data = self.dso_manager.verify_socio(socio)
        if socio_data is None or socio_data.empty:
            return {
                "success": False,
                "message": "Il socio non è attivo o non esiste.",
                "output_file": None,
            }

        campo_value = socio_data[option.campo].iloc[0] if option.campo in socio_data.columns else 0
        if campo_value != 1:
            return {
                "success": False,
                "message": f"Il socio {socio} non è abilitato per il data sharing '{datasharing_code}'.",
                "output_file": None,
            }

        return self.dso_manager.process_data(socio, periodo, option)