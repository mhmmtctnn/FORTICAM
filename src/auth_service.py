import streamlit as st
import datetime
import ssl
import logging
from ldap3 import Server, Connection, ALL, Tls
from config_service import ConfigService

# Logger Yapilandirmasi
logger = logging.getLogger(__name__)

class User:
    def __init__(self, username, role, permissions=None, global_allowed_ports=None, device_allowed_ports=None):
        self.username = username
        self.role = role
        self.permissions = permissions or {}
        self.global_allowed_ports = global_allowed_ports or []
        # Standardize: device_allowed_ports
        self.device_allowed_ports = device_allowed_ports or {}
        # Alias for backward compatibility if needed elsewhere
        self.allowed_ports = self.device_allowed_ports
        self.login_time = datetime.datetime.now()

    def has_access_to_port(self, device_name, port_name):
        """
        Check if user has access to a specific port on a device.
        """
        # 1. Super User check
        if self.username == "admin" or self.role == "Super_User":
            return True
            
        # 2. Strict Whitelist Logic
        # If no permissions defined at all? Strict mode -> Deny.
        
        # Check Global Ports
        if port_name in self.global_allowed_ports:
            return True
            
        # Check Device Specific Ports
        if device_name in self.device_allowed_ports:
            if port_name in self.device_allowed_ports[device_name]:
                return True
                
        return False

class AuthService:
    
    @staticmethod
    def _get_profile_by_ldap_groups(user_groups, mappings):
        if not user_groups or not mappings:
            return None, None, None
        
        logger.info(f"Comparing user groups with {len(mappings)} mappings.")
        for grp in user_groups:
            grp_lower = grp.lower().strip()
            for mapping in mappings:
                map_dn = mapping.get('group_dn', '').lower().strip()
                if not map_dn: continue
                
                if map_dn == grp_lower or map_dn in grp_lower:
                    logger.info(f"Match found: {grp} -> {mapping.get('profile')}")
                    # STANDARDIZATION: Prefer new keys, fallback to old keys
                    g_ports = mapping.get('global_allowed_ports', mapping.get('allowed_ports', []))
                    d_ports = mapping.get('device_allowed_ports', {})
                    return mapping.get('profile'), g_ports, d_ports
        return None, None, None

    @staticmethod
    def login(username, password):
        cfg = ConfigService.load_config()
        
        # 1. YEREL KULLANICI KONTROLU
        if username == "admin" and password == "admin":
            st.session_state['current_user'] = User("admin", "Super_User")
            return True, "Başarılı"
            
        local_accounts = cfg.get("local_accounts", [])
        for acc in local_accounts:
            if acc['user'] == username and acc.get('password') == password:
                role = acc.get('profile', 'Standard_User')
                # Yerel kullanicilar icin izinleri yukle
                g_ports = acc.get("global_allowed_ports", [])
                
                # Cihaz izinleri: once yeni key, yoksa eski key
                d_ports = acc.get("device_allowed_ports", acc.get("allowed_ports", {}))
                
                st.session_state['current_user'] = User(username, role, global_allowed_ports=g_ports, device_allowed_ports=d_ports)
                return True, "Başarılı"

        # 2. LDAP KONTROLU
        ldap_cfg = cfg.get("ldap_settings", {})
        if ldap_cfg.get("enabled"):
            return AuthService._check_ldap_credentials(username, password, ldap_cfg, cfg)
                
        return False, "Kullanıcı bulunamadı veya LDAP kapalı."

    @staticmethod
    def _check_ldap_credentials(username, password, ldap_config, full_config):
        # Otomatik MFA\ ekle - Dogru Escape Yapildi
        if chr(92) not in username and "@" not in username:
            auth_username = f"MFA{chr(92)}{username}"
        else:
            auth_username = username
        
        servers_list = ldap_config.get('servers', [])
        if not servers_list: return False, "Sunucu tanımlı değil."

        port = ldap_config.get('port', 636)
        use_ssl = ldap_config.get('use_ssl', True)
        base_dn = ldap_config.get('base_dn', '')
        tls_config = Tls(validate=ssl.CERT_NONE) if use_ssl else None

        for server_host in servers_list:
            if not server_host: continue
            
            # Adresi temizle
            server_host = str(server_host).strip()
            for prefix in ["ldaps://", "ldap://", "http://", "https://"]:
                if server_host.startswith(prefix):
                    server_host = server_host.replace(prefix, "")
            
            try:
                server = Server(server_host, port=port, use_ssl=use_ssl, tls=tls_config, get_info=ALL, connect_timeout=5)
                
                possible_dns = [auth_username]
                # Dogru Escape Yapildi
                if chr(92) not in username and "@" not in username and base_dn:
                    domain_parts = [p.split('=')[1] for p in base_dn.lower().split(',') if p.strip().startswith('dc=')]
                    if domain_parts:
                        possible_dns.append(f"{username}@{'.'.join(domain_parts)}")

                conn = None
                for test_dn in possible_dns:
                    try:
                        c = Connection(server, user=test_dn, password=password, auto_bind=True)
                        if c.bound: 
                            conn = c
                            break
                    except: continue
                
                if conn and conn.bound:
                    logger.info(f"Bind OK: {username}")
                    user_groups = []
                    short_user = username.split('\\')[-1].split('@')[0]
                    search_filter = f"( |(sAMAccountName={short_user})(uid={short_user})(cn={short_user}))"
                    
                    conn.search(base_dn, search_filter, attributes=['memberOf'])
                    if len(conn.entries) > 0:
                        entry = conn.entries[0]
                        if 'memberOf' in entry:
                            user_groups = [str(g) for g in entry['memberOf'].values]
                    
                    mappings = ldap_config.get("mappings", [])
                    profile_name, g_ports, d_ports = AuthService._get_profile_by_ldap_groups(user_groups, mappings)
                    
                    if not profile_name:
                        conn.unbind()
                        group_list = ", ".join([g.split(',')[0].replace('CN=', '') for g in user_groups])
                        return False, f"LDAP Girişi Başarılı ancak yetki grubunuz eşleşmedi. AD Gruplarınız: {group_list if group_list else 'Grup Bulunamadı'}"
                    
                    # LDAP Mapping'den gelen portlari yukle
                    st.session_state['current_user'] = User(username, profile_name, global_allowed_ports=g_ports, device_allowed_ports=d_ports)
                    conn.unbind()
                    return True, "Başarılı"
                    
            except Exception as e:
                logger.error(f"LDAP Error ({server_host}): {e}")
                continue
                
        return False, "LDAP Bağlantı Hatası veya Kimlik Bilgileri Yanlış."

    @staticmethod
    def is_ldap_reachable(server_host, port, timeout=2):
        """Sunucuya TCP seviesinde ulasilabiliyor mu kontrol eder."""
        import socket
        try:
            server_host = str(server_host).strip()
            # Protokolleri temizle
            for prefix in ["ldaps://", "ldap://"]:
                if server_host.startswith(prefix):
                    server_host = server_host.replace(prefix, "")
            
            socket.setdefaulttimeout(timeout)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((server_host, int(port)))
            return True
        except:
            return False

    @staticmethod
    def test_connection(server_host, port, use_ssl, username, password):
        try:
            # Kesin Temizlik: Bosluklari sil ve protokolleri temizle
            server_host = str(server_host).strip()
            for prefix in ["ldaps://", "ldap://", "http://", "https://"]:
                if server_host.startswith(prefix):
                    server_host = server_host.replace(prefix, "")
            
            # Dogru Escape Yapildi
            if chr(92) not in username and "@" not in username:
                username = f"MFA{chr(92)}{username}"
            tls = Tls(validate=ssl.CERT_NONE) if use_ssl else None
            server = Server(server_host, port=port, use_ssl=use_ssl, tls=tls, get_info=ALL, connect_timeout=5)
            conn = Connection(server, user=username, password=password, auto_bind=True)
            if conn.bound:
                conn.unbind()
                return True, f"Bağlantı Başarılı! ({username})"
            return False, "Bind Başarısız."
        except Exception as e:
            return False, f"Hata ({server_host}): {str(e)}"

    @staticmethod
    def logout():
        if 'current_user' in st.session_state:
            del st.session_state['current_user']
        if 'api' in st.session_state:
            st.session_state.api = None
            st.session_state.fmg_connected = False

    @staticmethod
    def get_current_user():
        return st.session_state.get('current_user')

    @staticmethod
    def is_authenticated():
        return 'current_user' in st.session_state