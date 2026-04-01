import json
from enum import StrEnum


def _load_supported_values(key, defaults):
    try:
        config_data = _load_config_data()
        values = config_data.get(key, defaults)
    except Exception:
        values = defaults

    normalized_values = []
    for value in values:
        normalized_value = str(value).strip().lower()
        if normalized_value and normalized_value not in normalized_values:
            normalized_values.append(normalized_value)

    return normalized_values or defaults


def _enum_member_name(value):
    return str(value).strip().upper().replace(" ", "_")


def _load_config_data(config_file="config.json"):
    with open(config_file, "r") as file:
        return json.load(file)


FileType = StrEnum(
    "FileType",
    {member_name: value for value in _load_supported_values("supported_file_types", ["xml", "csv", "excel"])
     for member_name in [_enum_member_name(value)]},
)


DeliveryMethod = StrEnum(
    "DeliveryMethod",
    {
        member_name: value
        for value in _load_supported_values(
            "supported_delivery_methods",
            ["ftp", "azure_storage", "nasshare", "mail", "piccione_viaggiatore"],
        )
        for member_name in [_enum_member_name(value)]
    },
)



class DataSharingOption:
    def __init__(self):
        self.options = set()  # Initialize options as a set
        config_file = "config.json"
        config_data = _load_config_data(config_file)
        items = config_data.get("data_sharing_options", [])

        for item in items:
            self.options.add(Option(item))


class Option:
    def __init__(self, option_data):
        self.name = option_data.get("name")
        self.file_type = FileType(option_data.get("file_type"))
        self.code = option_data.get("code")
        self.campo = option_data.get("Campo")
        self.delivery_method = DeliveryMethod(option_data.get("delivery_method"))
        self.naming_convention = option_data.get("naming_convention")
        self.naming_variables = option_data.get("naming_variables", {})
        self.query_file = option_data.get("query_file")
        self.xslt_template = option_data.get("xslt_template")
        self.xml_mapping = option_data.get("xml_mapping", {})
        self.xml_grouping = option_data.get("xml_grouping", {})
        self.xml_structure = option_data.get("xml_structure", {})
        if self.file_type == FileType.XML:
            self.parameters = Parameters(option_data)
        # Initialize specific configuration based on delivery_method
        if self.delivery_method == DeliveryMethod.FTP:
            self.config = FTPDataSharingOption(option_data)
        elif self.delivery_method == DeliveryMethod.AZURE_STORAGE:
            self.config = AzureStorageDataSharingOption(option_data)
        elif self.delivery_method == DeliveryMethod.NASSHARE:
            self.config = NASShareDataSharingOption(option_data)
        elif self.delivery_method in {DeliveryMethod.MAIL, DeliveryMethod.PICCIONE_VIAGGIATORE}:
            self.config = GenericDataSharingOption(option_data)
        else:
            self.config = GenericDataSharingOption(option_data)


class Parameters:
    def __init__(self, config_data):
        # Change parameters to a dictionary for easier access and assignment
        self.parameters = {}
        for param_name, param_value in config_data.get("parameters", {}).items():
            self.add(Parameter(param_name))

    def add(self, parameter):
        # Use the parameter name as the key in the dictionary
        self.parameters[parameter.name] = parameter

    def get(self, name):
        # Retrieve a parameter by name
        return self.parameters.get(name)

    def set(self, name, value):
        # Set the value of a parameter by name
        if name in self.parameters:
            self.parameters[name].value = value
        else:
            # Optionally, add a new parameter if it doesn't exist
            self.add(Parameter(name))
            self.parameters[name].value = value


class Parameter:
    def __init__(self, name):
        self.name = name
        self.value = None


class FTPDataSharingOption:
    def __init__(self, option_data):
        ftp_config = option_data.get("ftp_config", {})
        self.host = ftp_config.get("host")
        self.user = ftp_config.get("user")
        self.password = ftp_config.get("password")
        self.port = ftp_config.get("port")
        self.create_ok_file = ftp_config.get("create_ok_file", False)


class AzureStorageDataSharingOption:
    def __init__(self, option_data):
        azure_storage_config = option_data.get("azure_storage_config", {})
        self.sas_url = azure_storage_config.get("sas_url")
        self.expiration_date = azure_storage_config.get("expiration_date")
        self.permissions = azure_storage_config.get("permissions")


class NASShareDataSharingOption:
    def __init__(self, option_data):
        nasshare_config = option_data.get("nasshare_config", {})
        self.deposit_address = nasshare_config.get("deposit_address")


class GenericDataSharingOption:
    def __init__(self, option_data):
        self.config = option_data