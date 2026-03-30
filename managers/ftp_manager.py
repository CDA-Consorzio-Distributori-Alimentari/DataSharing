from ftplib import FTP

class FTPManager:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password

    def upload_file(self, file_path, remote_path):
        with FTP(self.host) as ftp:
            ftp.login(self.username, self.password)
            with open(file_path, 'rb') as file:
                ftp.storbinary(f'STOR {remote_path}', file)