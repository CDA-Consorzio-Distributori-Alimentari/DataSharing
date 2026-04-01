import smtplib
from email.mime.text import MIMEText

from services.config import Config

class MailManager:
    def __init__(self):
        config = Config()
        self.smtp_server = config.mail_config.get("smtp_server", "smtp.example.com")
        self.smtp_port = config.mail_config.get("port", 587)
        
        self.username = config.mail_config.get("user", "email_user")
        self.password = config.mail_config.get("password", "email_password")

    def send_mail(self, to_address, subject, body):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = to_address

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, to_address, msg.as_string())