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
        
        # Normalize Ports: List for Global, Dict for Device-Specific
        self.global_allowed_ports = global_allowed_ports if isinstance(global_allowed_ports, list) else []
        self.device_allowed_ports = device_allowed_ports if isinstance(device_allowed_ports, dict) else {}
        
        self.login_time = datetime.datetime.now()

    def has_access_to_port(self, device_name, port_name):
        """
        Check if user has access to a specific port on a device.
        Order: Admin > Global Whitelist > Device Whitelist
        """
        # 1. Super User / Admin check
        if self.username == "admin" or self.role == "Super_User":
            return True
            
        # 2. Global Port Check
        if port_name in self.global_allowed_ports:
            return True
            
        # 3. Device Specific Port Check
        device_ports = self.device_allowed_ports.get(device_name, [])
        if port_name in device_ports:
            return True
            
        return False

class AuthService:
    
    @staticmethod
    def _get_profile_by_ldap_groups(user_groups, mappings):
        """
        Matches user's LDAP groups against configured mappings.
        Returns: (profile_name, global_ports, device_ports) or (None, None, None)
        """
        if not user_groups or not mappings:
            return None, None, None
        
        # Optimize: Pre-calculate lowercase user groups for faster matching
        user_groups_lower = {g.lower().strip() for g in user_groups}
        
        for mapping in mappings:
            map_dn = mapping.get('group_dn', '').lower().strip()
            if not map_dn: continue
            
            # Check if mapped group exists in user's groups
            # Using simple string check since map_dn might be a partial string or full DN
            # If map_dn is a substring of any user group (flexible matching)
            # OR exact match if desired. Here we keep the existing logic: if map_dn is in group string.
            
            # Optimization: Check if any user group contains the map_dn
            match = False
            for grp in user_groups_lower:
                if map_dn == grp or map_dn in grp:
                    match = True
                    break
            
            if match:
                logger.info(f"LDAP Group Match: {map_dn} -> {mapping.get('profile')}")
                
                # Standardize config keys (backward compatibility)
                g_ports = mapping.get('global_allowed_ports', mapping.get('allowed_ports', []))
                d_ports = mapping.get('device_allowed_ports', {})
                return mapping.get('profile'), g_ports, d_ports
                
        return None, None, None

    @staticmethod
    def login(username, password):
        cfg = ConfigService.load_config()
        
        # 1. LOCAL USER CHECK
        if username == "admin" and password == "admin":
            st.session_state['current_user'] = User("admin", "Super_User")
            return True, "Başarılı"
            
        local_accounts = cfg.get("local_accounts", [])
        # Optimization: Use a generator/next to find user quickly
        acc = next((a for a in local_accounts if a['user'] == username and a.get('password') == password), None)
        
        if acc:
            role = acc.get('profile', 'Standard_User')
            g_ports = acc.get("global_allowed_ports", [])
            d_ports = acc.get("device_allowed_ports", acc.get("allowed_ports", {}))
            
            st.session_state['current_user'] = User(username, role, global_allowed_ports=g_ports, device_allowed_ports=d_ports)
            return True, "Başarılı"

        # 2. LDAP CHECK
        ldap_cfg = cfg.get("ldap_settings", {})
        if ldap_cfg.get("enabled"):
            return AuthService._check_ldap_credentials(username, password, ldap_cfg, cfg)
                
        return False, "Kullanıcı bulunamadı veya LDAP kapalı."

    @staticmethod
    def _check_ldap_credentials(username, password, ldap_config, full_config):
        # Format Username for Bind
        if chr(92) not in username and "@" not in username: # chr(92) is backslash
            bind_user = f"MFA{chr(92)}{username}"
        else:
            bind_user = username
        
        servers_list = ldap_config.get('servers', [])
        if not servers_list: return False, "Sunucu tanımlı değil."

        port = ldap_config.get('port', 636)
        use_ssl = ldap_config.get('use_ssl', True)
        base_dn = ldap_config.get('base_dn', '')
        tls_config = Tls(validate=ssl.CERT_NONE) if use_ssl else None

        for server_host in servers_list:
            if not server_host: continue
            
            # Clean Host URL
            server_host = str(server_host).strip()
            for prefix in ["ldaps://", "ldap://", "http://", "https://"]:
                if server_host.startswith(prefix):
                    server_host = server_host.replace(prefix, "")
            
            try:
                # Connection Setup
                server = Server(server_host, port=port, use_ssl=use_ssl, tls=tls_config, get_info=ALL, connect_timeout=4)
                
                # Determine possible Bind DNs
                possible_dns = [bind_user]
                if chr(92) not in username and "@" not in username and base_dn:
                    # Construct UPN if base_dn provided (e.g., user@domain.com)
                    domain_parts = [p.split('=')[1] for p in base_dn.lower().split(',') if p.strip().startswith('dc=')]
                    if domain_parts:
                        possible_dns.append(f"{username}@{'.'.join(domain_parts)}")

                # Attempt Bind
                conn = None
                for test_dn in possible_dns:
                    try:
                        c = Connection(server, user=test_dn, password=password, auto_bind=True)
                        if c.bound: 
                            conn = c
                            break
                    except: continue
                
                if conn and conn.bound:
                    logger.info(f"LDAP Bind Successful: {username}")
                    
                    # Fetch User Groups
                    user_groups = []
                    short_user = username.split('\\')[-1].split('@')[0]
                    # Robust search filter
                    search_filter = f"(|(sAMAccountName={short_user})(uid={short_user})(cn={short_user}))"
                    
                    conn.search(base_dn, search_filter, attributes=['memberOf'])
                    if len(conn.entries) > 0:
                        entry = conn.entries[0]
                        if 'memberOf' in entry:
                            user_groups = [str(g) for g in entry['memberOf'].values]
                    
                    conn.unbind()
                    
                    # Map Groups to Profile
                    mappings = ldap_config.get("mappings", [])
                    profile_name, g_ports, d_ports = AuthService._get_profile_by_ldap_groups(user_groups, mappings)
                    
                    if not profile_name:
                        group_list_str = ", ".join([g.split(',')[0].replace('CN=', '') for g in user_groups])
                        return False, f"Yetki grubu bulunamadı. AD Gruplarınız: {group_list_str if group_list_str else 'Yok'}"
                    
                    # Create Session
                    st.session_state['current_user'] = User(username, profile_name, global_allowed_ports=g_ports, device_allowed_ports=d_ports)
                    return True, "Başarılı"
                    
            except Exception as e:
                logger.error(f"LDAP Connection Error ({server_host}): {e}")
                continue
                
        return False, "LDAP Bağlantı Hatası veya Kimlik Bilgileri Yanlış."

    @staticmethod
    def is_ldap_reachable(server_host, port, timeout=2):
        import socket
        try:
            server_host = str(server_host).strip()
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
            server_host = str(server_host).strip()
            for prefix in ["ldaps://", "ldap://", "http://", "https://"]:
                if server_host.startswith(prefix):
                    server_host = server_host.replace(prefix, "")
            
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
            try:
                if st.session_state.api:
                    st.session_state.api.logout()
            except: pass
            st.session_state.api = None
            st.session_state.fmg_connected = False

    @staticmethod
    def get_current_user():
        return st.session_state.get('current_user')

    @staticmethod
    def is_authenticated():
        return 'current_user' in st.session_state
