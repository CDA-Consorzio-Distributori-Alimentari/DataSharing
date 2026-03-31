import json
from os import name



class DataSharingOption:
    def __init__(self):
        self.options = set()  # Initialize options as a set
        config_file = "config.json"
        with open(config_file, "r") as file:
            config_data = json.load(file)
        items = config_data.get("data_sharing_options", [])

        for item in items:
            self.options.add(Option(item))


class Option:
    def __init__(self, option_data):
        self.name = option_data.get("name")
        self.file_type = option_data.get("file_type")
        self.code = option_data.get("code")
        self.campo = option_data.get("Campo")
        self.delivery_method = option_data.get("delivery_method")
        self.naming_convention = option_data.get("naming_convention")
        self.query_file = option_data.get("query_file")
        self.xslt_template = option_data.get("xslt_template")
        self.xml_mapping = option_data.get("xml_mapping", {})
        self.xml_grouping = option_data.get("xml_grouping", {})
        self.xml_structure = option_data.get("xml_structure", {})
        if self.file_type == "xml":
            self.parameters = Parameters(option_data)
        # Initialize specific configuration based on delivery_method
        if self.delivery_method == "ftp":
            self.config = FTPDataSharingOption(option_data)
        elif self.delivery_method == "azure_storage":
            self.config = AzureStorageDataSharingOption(option_data)
        elif self.delivery_method == "nasshare":
            self.config = NASShareDataSharingOption(option_data)
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