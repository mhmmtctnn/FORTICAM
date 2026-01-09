import csv
import os
import datetime
import pytz
import streamlit as st
import pandas as pd
from email_service import EmailService

LOG_FILE = "audit_logs.csv"

class LogService:
    """Merkezi loglama servisi."""
    
    @staticmethod
    def log_action(user_name: str, action: str, device: str, details: str):
        """Kullanıcı işlemini loglar ve e-posta bildirimi gönderir."""
        tz_name = st.session_state.get('user_timezone', 'Europe/Istanbul')
        try:
            tz = pytz.timezone(tz_name)
        except:
            tz = pytz.utc
            
        timestamp = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        file_exists = os.path.exists(LOG_FILE)
        
        try:
            with open(LOG_FILE, "a", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "User", "Action", "Device", "Details"])
                
                writer.writerow([timestamp, user_name, action, device, str(details)])
                f.flush()
                os.fsync(f.fileno())
                
            # --- E-posta Bildirimi ---
            # Sadece 'operator' kullanıcısı veya kritik işlemler için filtre eklenebilir.
            # Şimdilik tüm loglanan işlemler için gönderiyoruz.
            try:
                subject = f"⚠️ FortiManager İşlem Bildirimi: {action}"
                body = (
                    f"Bir işlem gerçekleştirildi.\n\n"
                    f"Zaman: {timestamp}\n"
                    f"Kullanıcı: {user_name}\n"
                    f"İşlem: {action}\n"
                    f"Cihaz: {device}\n"
                    f"Detaylar: {details}\n\n"
                    f"Bu mesaj FortiManager Controller uygulamasından otomatik olarak gönderilmiştir."
                )
                EmailService.send_notification(subject, body)
            except Exception as email_err:
                print(f"Email Notification Error: {email_err}")

        except Exception as e:
            print(f"Log Error: {e}")

    @staticmethod
    def get_logs() -> pd.DataFrame:
        """Logları okur."""
        if not os.path.exists(LOG_FILE):
            return pd.DataFrame(columns=["Timestamp", "User", "Action", "Device", "Details"])
        
        try:
            return pd.read_csv(LOG_FILE, on_bad_lines='skip')
        except Exception:
            return pd.DataFrame(columns=["Timestamp", "User", "Action", "Device", "Details"])
