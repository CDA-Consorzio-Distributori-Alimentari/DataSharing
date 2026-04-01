# Azure Storage Manager

import os
from azure.storage.blob import BlobServiceClient
from datetime import datetime
from ..log_manager import LogManager

class AzureStorageManager:
    def __init__(self, sas_url, log_manager=None):
        self.blob_service_client = BlobServiceClient(account_url=sas_url)
        self.log = log_manager or LogManager()

    def upload_file(self, container_name, file_path, blob_name):
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            self.log.log_info(f"File {file_path} uploaded to {blob_name} in container {container_name}.")
        except Exception as e:
            self.log.log_error(f"Error uploading file: {e}")

    def list_blobs(self, container_name):
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blobs = container_client.list_blobs()
            return [blob.name for blob in blobs]
        except Exception as e:
            self.log.log_error(f"Error listing blobs: {e}")
            return []

    def delete_blob(self, container_name, blob_name):
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_client.delete_blob()
            self.log.log_info(f"Blob {blob_name} deleted from container {container_name}.")
        except Exception as e:
            self.log.log_error(f"Error deleting blob: {e}")

# Example usage
if __name__ == "__main__":
    sas_url = "<your_sas_url_here>"
    manager = AzureStorageManager(sas_url)

    # Example operations
    container = "example-container"
    file_to_upload = "example.txt"
    blob_name = f"example_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"

    manager.upload_file(container, file_to_upload, blob_name)
    manager.log.log_info(f"Blobs in container: {manager.list_blobs(container)}")
    manager.delete_blob(container, blob_name)