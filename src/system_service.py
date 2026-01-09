import os
import base64
from OpenSSL import crypto

class SystemService:
    """Uygulamanın (Docker) sistem ayarlarını yönetir."""

    @staticmethod
    def check_dns_status(test_host="google.com"):
        """DNS cozumlemesi calisiyor mu kontrol eder."""
        import socket
        try:
            socket.gethostbyname(test_host)
            return True
        except:
            return False

    @staticmethod
    def update_dns(primary: str, secondary: str):
        """Konteynerin DNS ayarlarını (/etc/resolv.conf) günceller."""
        try:
            # Docker konteynerlerinde /etc/resolv.conf yazılabilir durumdadır (genellikle)
            content = f"nameserver {primary}\n"
            if secondary:
                content += f"nameserver {secondary}\n"
            
            # Not: Windows tabanlı docker desktop'ta bu dosya kilitli olabilir.
            # Ancak Linux tabanlı gerçek bir docker hostunda çalışır.
            if os.name != 'nt': # Sadece Linux/Docker ortamında
                with open('/etc/resolv.conf', 'w') as f:
                    f.write(content)
                return True, "Konteyner DNS ayarları güncellendi."
            else:
                return False, "Windows ortamında DNS manuel değiştirilmelidir."
        except Exception as e:
            return False, f"DNS güncelleme hatası: {e}"

    @staticmethod
    def apply_pfx_certificate(pfx_base64: str, password: str):
        """PFX dosyasından sertifika ve key çıkarıp diske kaydeder."""
        try:
            pfx_data = base64.b64decode(pfx_base64)
            pfx = crypto.load_pkcs12(pfx_data, password.encode())
            
            cert = crypto.dump_certificate(crypto.FILETYPE_PEM, pfx.get_certificate())
            key = crypto.dump_privatekey(crypto.FILETYPE_PEM, pfx.get_privatekey())
            
            # Sertifikaları .streamlit klasörüne veya belirlenen bir yere kaydet
            cert_path = "cert.pem"
            key_path = "key.pem"
            
            with open(cert_path, "wb") as f: f.write(cert)
            with open(key_path, "wb") as f: f.write(key)
            
            return True, f"Sertifika başarıyla çıkarıldı: {cert_path}, {key_path}. Uygulamanın HTTPS ile açılması için restart gerekebilir."
        except Exception as e:
            return False, f"Sertifika işleme hatası: {e}"
