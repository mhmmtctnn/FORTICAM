import streamlit as st
import os
import base64
from auth_service import AuthService

@st.cache_data(show_spinner=False)
def get_base64_image(image_path):
    """Görüntüyü base64 olarak önbelleğe alıp döndürür."""
    if not image_path: return None
    
    # Normalize path
    image_path = image_path.replace("\\", os.sep).replace("/", os.sep)
    
    if not os.path.exists(image_path):
        # Farklı çalışma dizinleri için bir üst dizini kontrol et
        parent_path = os.path.join("..", image_path)
        if os.path.exists(parent_path):
            image_path = parent_path
        else:
            return None
            
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

class UI:
    """UI bilesenlerini ve sayfa duzenini yonetir."""
    
    @staticmethod
    def set_bg_image(image_path):
        """Arka plan resmini ayarlar."""
        bin_str = get_base64_image(image_path)
        if not bin_str:
            return

        ext = os.path.splitext(image_path)[1].lower().replace(".", "")
        if ext == "jpg": ext = "jpeg"
        
        page_bg_img = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        .stApp {{
            background-image: url("data:image/{ext};base64,{bin_str}") !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}
        
        /* Glassmorphism Container for Main App */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 16px;
            margin-top: 2rem;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            max-width: 95% !important;
        }}
        </style>
        """
        st.markdown(page_bg_img, unsafe_allow_html=True)

    @staticmethod
    def init_page():
        st.set_page_config(
            page_title="FortiManager Controller",
            page_icon="🛡️",
            layout="centered",
            initial_sidebar_state="expanded"
        )
        # Global Styles
        st.markdown("""
        <style>
            /* Hide Streamlit Default Elements */
            #MainMenu { visibility: hidden; }
            footer { visibility: hidden; }
            header { visibility: hidden; }
            [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
            
            /* Button Styles */
            .stButton > button {
                border-radius: 8px;
                font-weight: 500;
                border: none;
                transition: all 0.2s;
            }
            .stButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }
        </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def login_screen():
        """Modern Card Login Screen (Exact replica of login_page.png)."""
        
        logo_path = "MFA Logo/yeni_Bakanlık Logo.png"
        logo_data = get_base64_image(logo_path)
        
        # Logo handling
        logo_html = ""
        if logo_data:
            logo_html = f'<img src="data:image/png;base64,{logo_data}" style="height: 50px; width: auto; margin-right: 15px;">'
        else:
            # Fallback icon if logo missing
            logo_html = '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="#007bff" stroke="none"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>'

        # --- LOGIN SPECIFIC CSS ---
        st.markdown("""
            <style>
                /* 1. HIDE SIDEBAR & DEFAULT ELEMENTS */
                [data-testid="stSidebar"], 
                [data-testid="collapsedControl"],
                #MainMenu, 
                footer, 
                header { 
                    display: none !important; 
                }
                
                /* 2. PAGE BACKGROUND */
                .stApp {
                    background-color: #EEF2F6 !important; /* Light Gray/Blueish */
                    background-image: none !important;
                }
                
                /* 3. CARD CONTAINER (Styling .block-container in 'centered' layout) */
                .block-container {
                    background-color: #FFFFFF;
                    max-width: 450px !important;
                    padding: 0 !important;
                    margin-top: 5vh !important; 
                    border-radius: 12px;
                    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
                    border: 1px solid #eef2f6;
                    overflow: hidden; /* For footer rounding */
                }
                
                /* 4. FORM BODY PADDING */
                [data-testid="stForm"] {
                    padding: 20px 40px 30px 40px !important;
                    border: none !important;
                }
                
                /* 5. INPUTS */
                .stTextInput > div > div > input {
                    background-color: #f8f9fa !important;
                    border: 1px solid #e9ecef !important;
                    color: #495057 !important;
                    border-radius: 6px !important;
                    padding-left: 40px !important; /* Space for icon */
                    height: 48px !important;
                    font-size: 15px !important;
                }
                .stTextInput > div > div > input:focus {
                    border-color: #5D5FEF !important;
                    box-shadow: 0 0 0 3px rgba(93, 95, 239, 0.15) !important;
                }
                
                /* Input Icons using aria-label selector (More robust than :has) */
                /* Username */
                input[aria-label="USERNAME"] {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 448 512' fill='%236c757d'%3E%3Cpath d='M224 256c70.7 0 128-57.3 128-128S294.7 0 224 0 96 57.3 96 128s57.3 128 128 128zm89.6 32h-16.7c-22.2 10.2-46.9 16-72.9 16s-50.6-5.8-72.9-16h-16.7C60.2 288 0 348.2 0 422.4V464c0 26.5 21.5 48 48 48h352c26.5 0 48-21.5 48-48v-41.6c0-74.2-60.2-134.4-134.4-134.4z'/%3E%3C/svg%3E");
                    background-repeat: no-repeat;
                    background-position: 12px center;
                    background-size: 16px;
                }
                /* Password */
                input[aria-label="PASSWORD"] {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 448 512' fill='%236c757d'%3E%3Cpath d='M400 224h-24v-72C376 68.2 307.8 0 224 0S72 68.2 72 152v72H48c-26.5 0-48 21.5-48 48v192c0 26.5 21.5 48 48 48h352c26.5 0 48-21.5 48-48V272c0-26.5-21.5-48-48-48zm-104 0H152v-72c0-39.7 32.3-72 72-72s72 32.3 72 72v72z'/%3E%3C/svg%3E");
                    background-repeat: no-repeat;
                    background-position: 12px center;
                    background-size: 14px;
                }

                /* Labels */
                .stTextInput label {
                    color: #64748b !important;
                    font-size: 0.75rem !important;
                    font-weight: 600 !important;
                    letter-spacing: 0.5px !important;
                    margin-bottom: 6px !important;
                    text-transform: uppercase;
                }
                
                /* 6. BUTTON */
                .stButton > button {
                    width: 100% !important;
                    background-color: #5D5FEF !important; /* Purple */
                    color: white !important;
                    border-radius: 6px !important;
                    height: 48px !important;
                    font-weight: 600 !important;
                    border: none !important;
                    margin-top: 15px !important;
                }
                .stButton > button:hover {
                    background-color: #4b4dcb !important;
                    box-shadow: 0 4px 12px rgba(93, 95, 239, 0.3) !important;
                }
                
                /* Markdown Spacing */
                div[data-testid="stMarkdownContainer"] p { margin-bottom: 0; }
                
            </style>
        """, unsafe_allow_html=True)

        # HEADER SECTION
        st.markdown(f"""
        <div style="background-color: white; border-bottom: 1px solid #f1f5f9;">
            <div style="padding: 32px 32px 24px 32px; display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    {logo_html}
                    <div>
                        <div style="font-weight: 700; font-size: 1.1rem; color: #0f172a; line-height: 1.2;">FortiCam</div>
                        <div style="font-weight: 500; font-size: 0.9rem; color: #64748b;">Access</div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.65rem; color: #94a3b8; font-weight: 500;">SECURE LOGIN</div>
                    <div style="font-size: 0.75rem; color: #475569; font-weight: 700;">v1.10</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # FORM SECTION
        st.markdown('<div style="background-color: white; padding: 24px 0 0 0;">', unsafe_allow_html=True)
        with st.form("login_form", border=False):
            # Using specific labels to match CSS
            username = st.text_input("USERNAME", placeholder="Enter your username")
            password = st.text_input("PASSWORD", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In  ➜")
            
            if submitted:
                if not username or not password:
                    st.warning("Please enter username and password.")
                else:
                    success, msg = AuthService.login(username, password)
                    if success:
                        st.toast("Giriş Başarılı!", icon="✅")
                        st.rerun()
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # FOOTER SECTION
        st.markdown("""
        <div style="background-color: #f8fafc; padding: 16px; text-align: center; border-top: 1px solid #f1f5f9;">
            <span style="font-size: 0.75rem; color: #94a3b8;">LDAP or Local DB authentication enabled.</span>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def sidebar_menu():
        """Rol ve Yetki tabanli sol menu."""
        user = AuthService.get_current_user()
        if not user: return None
        
        # Load Config for Permissions
        from config_service import ConfigService
        cfg = ConfigService.load_config()
        profiles = cfg.get("admin_profiles", [])
        
        user_rights = {}
        if user.username == "admin":
            user_rights = {"Dashboard": 2, "FMG_Conn": 2, "Auth": 2, "System": 2, "Logs": 2}
        else:
            target_profile = next((p for p in profiles if p['name'] == user.role), None)
            if target_profile:
                user_rights = target_profile.get("permissions", {})
            else:
                user_rights = {"Dashboard": 0, "FMG_Conn": 0, "Auth": 0, "System": 0, "Logs": 0}

        with st.sidebar:
            logo_path = "MFA Logo/yeni_Bakanlık Logo.png"
            logo_data = get_base64_image(logo_path)
            if logo_data:
                 st.markdown(f'<img src="data:image/png;base64,{logo_data}" style="width: 140px; margin-bottom: 20px;">', unsafe_allow_html=True)
            
            st.title("🛡️ FortiCam")
            st.caption(f"👤 {user.username} ({user.role})")
            
            options = []
            if user_rights.get("Dashboard", 0) >= 1: options.append("Dashboard")
            if user_rights.get("FMG_Conn", 0) >= 1: options.append("FMG Bağlantısı")
            if user_rights.get("System", 0) >= 1 or user_rights.get("Auth", 0) >= 1: options.append("Ayarlar")
            if user_rights.get("Logs", 0) >= 1: options.append("Audit Logs")
            
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
