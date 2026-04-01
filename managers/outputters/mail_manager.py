import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class MailManager:
    def __init__(
        self,
        smtp_server="spamfight.mdsnet.it",
        port=26,
        user="email_user",
        password="email_password",
        sender_email="dwh@cdaweb.it",
        summary_sender_email="norepy@cdaweb.it",
        summary_recipient="dwh@cdaweb.it",
    ):
        self.smtp_server = smtp_server
        self.smtp_port = port
        self.username = user
        self.password = password
        self.sender_email = sender_email
        self.summary_sender_email = summary_sender_email
        self.summary_recipient = summary_recipient

    def send_mail(self, to_address, subject, body, from_address=None):
        sender_address = from_address or self.sender_email or self.username

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender_address
        msg['To'] = to_address
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.sendmail(sender_address, to_address, msg.as_string())

    def send_summary_mail(self, subject, body):
        self.send_mail(
            self.summary_recipient,
            subject,
            body,
            from_address=self.summary_sender_email,
        )