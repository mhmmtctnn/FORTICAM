import streamlit as st
from auth_service import AuthService

class UI:
    """UI bilesenlerini ve sayfa duzenini yonetir."""
    
    @staticmethod
    def init_page():
        st.set_page_config(
            page_title="FortiManager Controller",
            page_icon="🛡️",
            layout="wide",
            initial_sidebar_state="expanded" # Sidebar hep acik kalsin
        )
        st.markdown("""
        <style>
            .stButton>button { width: 100%; }
            /* #MainMenu { visibility: hidden; } */
            /* footer { visibility: hidden; } */
            /* header { visibility: hidden; }  <-- ACILDI: Sidebar toggle icin gerekli */
            [data-testid='stSidebar'] { background-color: #f0f2f6; }
            
            /* Sidebar acma butonunu garantiye al (Gorunurluk, Renk, Katman) */
            [data-testid="stSidebarCollapsedControl"] { 
                display: block !important; 
                visibility: visible !important; 
                z-index: 100000 !important;
                color: #31333F !important;
                background-color: rgba(255, 255, 255, 0.5) !important;
            }
        </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def login_screen():
        """Merkezilenmis Login ekrani."""
        # Sidebar'i Gizle
        st.markdown("""
            <style>
                [data-testid="stSidebar"] { display: none; }
            </style>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center;'>🔐 Giriş Paneli</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Kurumsal (LDAP) veya Yerel Hesap ile giriş yapabilirsiniz.</p>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                username = st.text_input("Kullanıcı Adı")
                password = st.text_input("Şifre", type="password")
                submitted = st.form_submit_button("Giriş Yap", type="primary")
                
                if submitted:
                    success, msg = AuthService.login(username, password)
                    if success:
                        st.success("Giriş Başarılı!")
                        st.rerun()
                    else:
                        st.error(msg)

    @staticmethod
    def sidebar_menu():
        """Rol ve Yetki tabanli sol menu (Granüler)."""
        user = AuthService.get_current_user()
        if not user: return None
        
        # Sidebar'i Gorunur Yap (NOT: display:block !important kaldirildi, toggle bozmasin diye)
        
        # Yetkileri Configden Cek
        from config_service import ConfigService
        cfg = ConfigService.load_config()
        profiles = cfg.get("admin_profiles", [])
        
        user_rights = {}
        if user.username == "admin":
            # Admin her seye sahip
            user_rights = {"Dashboard": 2, "FMG_Conn": 2, "Auth": 2, "System": 2, "Logs": 2}
        else:
            target_profile = next((p for p in profiles if p['name'] == user.role), None)
            if target_profile:
                user_rights = target_profile.get("permissions", {})
            else:
                # Default empty perms
                user_rights = {"Dashboard": 0, "FMG_Conn": 0, "Auth": 0, "System": 0, "Logs": 0}

        with st.sidebar:
            st.title("🛡️ FortiCam")
            st.caption(f"👤 {user.username} ({user.role})")
            
            options = []
            
            # Yetki Kontrolü
            can_see_dash = user_rights.get("Dashboard", 0) >= 1
            can_see_fmg = user_rights.get("FMG_Conn", 0) >= 1
            can_see_sys = (user_rights.get("System", 0) >= 1 or user_rights.get("Auth", 0) >= 1)
            can_see_logs = user_rights.get("Logs", 0) >= 1

            if can_see_dash: options.append("Dashboard")
            if can_see_fmg: options.append("FMG Bağlantısı")
            if can_see_sys: options.append("Ayarlar")
            if can_see_logs: options.append("Audit Logs")
            
            # Herkese açık Yardım Menüsü
            if options:
                options.append("Kullanım Kılavuzu")
            
            if not options:
                st.warning("Erişim yetkiniz bulunmuyor.")
                if st.button("Çıkış Yap"):
                    AuthService.logout(); st.rerun()
                return None

            selection = st.radio("Menü", options, label_visibility="collapsed")
            
            st.divider()
            if st.button("Güvenli Çıkış"):
                AuthService.logout(); st.rerun()
                
            return selection