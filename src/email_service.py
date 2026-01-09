import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from config_service import ConfigService

class EmailService:
    """E-posta bildirimlerini yöneten servis."""

    @staticmethod
    def send_notification(subject: str, message_body: str):
        """
        Yapılandırılmış ayarlara göre e-posta gönderir.
        """
        config = ConfigService.load_config()
        email_cfg = config.get("email_settings", {})

        if not email_cfg.get("enabled", False):
            return False, "E-posta bildirimleri kapalı."

        smtp_server = email_cfg.get("smtp_server")
        smtp_port = email_cfg.get("smtp_port", 587)
        sender_email = email_cfg.get("sender_email")
        sender_password = email_cfg.get("sender_password")
        receivers = email_cfg.get("receiver_emails", [])

        if not (smtp_server and sender_email and receivers):
            return False, "E-posta yapılandırması eksik."

        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ", ".join(receivers)
            msg['Subject'] = subject

            msg.attach(MIMEText(message_body, 'plain', 'utf-8'))

            # SMTP Bağlantısı
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Güvenli bağlantı
                if sender_password:
                    server.login(sender_email, sender_password)
                server.send_message(msg)
            
            return True, "E-posta başarıyla gönderildi."

        except Exception as e:
            return False, f"E-posta gönderme hatası: {str(e)}"
