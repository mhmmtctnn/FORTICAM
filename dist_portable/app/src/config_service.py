import json
import os
import streamlit as st

CONFIG_FILE = "fmg_config.json"

class ConfigService:
    """Uygulama ayarlarını yöneten servis."""
    
    @staticmethod
    def load_config():
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            except:
                pass
        
        # --- Default Values Init ---
        if "ldap_settings" not in config:
            config["ldap_settings"] = {
                "enabled": False,
                "servers": ["192.168.1.10"],
                "port": 636,
                "use_ssl": True,
                "base_dn": "dc=example,dc=com",
                "mappings": [] # [{"group_dn": "...", "profile": "Super_User"}]
            }
            
        if "admin_profiles" not in config:
            config["admin_profiles"] = [
                {
                    "name": "Super_User", 
                    "permissions": {
                        "Dashboard": 2, "System": 2, "Logs": 2
                    }
                },
                {
                    "name": "Standard_User", 
                    "permissions": {
                        "Dashboard": 2, "System": 0, "Logs": 1
                    }
                },
                {
                    "name": "Read_Only", 
                    "permissions": {
                        "Dashboard": 1, "System": 0, "Logs": 1
                    }
                }
            ]
            
        if "local_accounts" not in config:
            config["local_accounts"] = [
                {"user": "admin", "profile": "Super_User"},
                {"user": "operator", "profile": "Standard_User"}
            ]

        if "email_settings" not in config:
            config["email_settings"] = {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "receiver_emails": []
            }
            
        return config

    @staticmethod
    def save_config(data: dict):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            st.error(f"Config Save Error: {e}")
