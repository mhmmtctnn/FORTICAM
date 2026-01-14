import streamlit as st
import time
import json
import datetime
import pytz
import base64
import pandas as pd

# Servisler ve Bilesenler
from auth_service import AuthService
from log_service import LogService
from config_service import ConfigService
from ui_components import UI
from api_client import FortiManagerAPI
from system_service import SystemService
from settings_view import render_settings

# --- CACHED DATA FUNCTIONS ---
@st.cache_data(ttl=60, show_spinner=False)
def get_cached_devices(_api):
    """Caches device list for 60 seconds."""
    if not _api: return []
    return _api.get_devices() or []

@st.cache_data(ttl=30, show_spinner=False)
def get_cached_vdoms(_api, device_name):
    """Caches VDOM list for 30 seconds."""
    if not _api: return ["root"]
    return _api.get_vdoms(device_name)

@st.cache_data(ttl=10, show_spinner=False)
def get_cached_interfaces(_api, device_name, vdom):
    """Caches interface list for 10 seconds."""
    if not _api: return []
    return _api.get_interfaces(device_name, vdom=vdom)

# --- INITIALIZATION ---
UI.init_page()
# UI.set_bg_image moved to authenticated section

# Global State Init
if 'fmg_connected' not in st.session_state: st.session_state.fmg_connected = False
if 'api' not in st.session_state: st.session_state.api = None
if 'devices' not in st.session_state: st.session_state.devices = []
if 'user_timezone' not in st.session_state: st.session_state.user_timezone = "Europe/Istanbul"
if 'vdoms_cache' not in st.session_state: st.session_state.vdoms_cache = {}
if 'saved_config' not in st.session_state: 
    st.session_state.saved_config = ConfigService.load_config()
    
    # --- AUTO APPLY DNS ---
    # Eger konfigde DNS varsa, uygulama acilisinda (ilk yuklemede) sisteme uygula
    cfg = st.session_state.saved_config
    p_dns = cfg.get("primary_dns")
    s_dns = cfg.get("secondary_dns")
    if p_dns:
        # Sessizce uygula (Hata olursa loga duser ama UI'i bloklamaz)
        try:
            SystemService.update_dns(p_dns, s_dns)
            print(f"Startup DNS Applied: {p_dns}, {s_dns}")
        except Exception as e:
            print(f"Startup DNS Error: {e}")

# --- AUTO CONNECT ---
if not st.session_state.fmg_connected:
    cfg = st.session_state.saved_config
    ip = cfg.get("fmg_ip")
    token = cfg.get("api_token")
    if ip and token:
        try:
            # Hizli baslangic icin kisa timeout
            api = FortiManagerAPI(ip, None, None, token, timeout=2)
            if api.login():
                st.session_state.api = api
                st.session_state.fmg_connected = True
                st.session_state.fmg_ip = ip
        except Exception as e:
            print(f"Auto-connect failed: {e}")

# --- PAGES ---

def render_dashboard():
    st.header("Dashboard")
    tz = pytz.timezone(st.session_state.user_timezone)
    current_time = datetime.datetime.now(tz).strftime("%H:%M:%S")
    st.caption(f"🕒 {current_time} ({st.session_state.user_timezone})")

    if not st.session_state.fmg_connected:
        st.warning("⚠️ FortiManager bağlantısı yok. Lütfen 'FMG Bağlantısı' menüsünden bağlanın.")
        return

    api = st.session_state.api
    if not st.session_state.devices:
        with st.spinner("Cihazlar getiriliyor..."):
            devices_res = api.get_devices()
            if devices_res is None:
                st.error(f"❌ FortiManager'a erişilemiyor ({st.session_state.fmg_ip}).")
                return
            st.session_state.devices = devices_res
            
    if not st.session_state.devices:
        st.info("Yönetilen cihaz bulunamadı.")
        return

    col_dev, col_vdom = st.columns([3, 1])
    device_names = [d['name'] for d in st.session_state.devices]
    with col_dev:
        sel_dev = st.selectbox("Firewall", device_names)
    
    vdoms = ["root"]
    if sel_dev:
        if sel_dev not in st.session_state.vdoms_cache:
            st.session_state.vdoms_cache[sel_dev] = api.get_vdoms(sel_dev)
        vdoms = st.session_state.vdoms_cache[sel_dev]
    with col_vdom:
        sel_vdom = st.selectbox("VDOM", vdoms)

# --- CONSTANTS ---
PHYSICAL_TYPES = ['physical', 'hard-switch', 'fsw', 'root', '0', '4']

def filter_interfaces_for_display(interfaces, user, device_name, show_sub_ifaces):
    """
    Interfaces listesini hem yetki hem de gorunum ayarlarin gore filtreler.
    Clean Code: Logic UI'dan ayrildi.
    """
    if not interfaces: return []
    
    # 1. Yetki Filtresi (Strict Whitelist Check)
    # User objesindeki merkezi kontrol metodunu kullan
    if user:
        interfaces = [i for i in interfaces if user.has_access_to_port(device_name, i['name'])]
    
    if not interfaces: return []

    # 2. Gorunum Filtresi (Tip ve Gizlilik)
    filtered_interfaces = []
    for i in interfaces:
        itype = str(i.get('type', 'unknown'))
        iname = str(i.get('name', '')).lower()
        
        # Manager arayuzunde gizli olan 'modem' vb. arayuzleri filtrele
        # Eger 'Sanal ve Alt Arayüzleri Göster' secili DEGILSE
        if not show_sub_ifaces:
            # Modem gibi sistem arayuzlerini isimden yakala ve gizle
            if "modem" in iname or "ssl." in iname:
                continue
                
            if itype in PHYSICAL_TYPES:
                filtered_interfaces.append(i)
        else:
            # Aciksa hepsini goster
            filtered_interfaces.append(i)
            
    return filtered_interfaces

# --- PAGES ---

def render_dashboard():
    st.header("Dashboard")
    tz = pytz.timezone(st.session_state.user_timezone)
    current_time = datetime.datetime.now(tz).strftime("%H:%M:%S")
    st.caption(f"🕒 {current_time} ({st.session_state.user_timezone})")

    if not st.session_state.fmg_connected:
        st.warning("⚠️ FortiManager bağlantısı yok. Lütfen 'FMG Bağlantısı' menüsünden bağlanın.")
        return

    api = st.session_state.api
    
    with st.spinner("Cihazlar getiriliyor..."):
        devices_res = get_cached_devices(api)
            
    if not devices_res:
        st.info("Yönetilen cihaz bulunamadı.")
        return

    col_dev, col_vdom = st.columns([3, 1])
    device_names = [d['name'] for d in devices_res]
    
    with col_dev:
        sel_dev = st.selectbox("Firewall", device_names)
    
    vdoms = ["root"]
    if sel_dev:
        vdoms = get_cached_vdoms(api, sel_dev)
    
    with col_vdom:
        sel_vdom = st.selectbox("VDOM", vdoms)

    # Kullanici Yetki Seviyesini Al
    user = AuthService.get_current_user()
    cfg = st.session_state.saved_config
    target_profile = next((p for p in cfg.get("admin_profiles", []) if p['name'] == user.role), None)
    
    # Dashboard yetki seviyesi (Default 0)
    dash_perm = 2 if user.username == "admin" else (target_profile.get("permissions", {}).get("Dashboard", 0) if target_profile else 0)

    st.subheader(f"🔌 Port Yönetimi: {sel_dev} [{sel_vdom}]")
    
    # Filtreleme Secenegi
    show_sub_ifaces = st.sidebar.checkbox("Sanal ve Alt Arayüzleri Göster (VLAN vb.)", value=False)
    
    raw_interfaces = get_cached_interfaces(api, sel_dev, sel_vdom)
    
    # Clean Code: Logic helper fonksiyonuna tasindi
    filtered_interfaces = filter_interfaces_for_display(raw_interfaces, user, sel_dev, show_sub_ifaces)

    if not filtered_interfaces:
        if not raw_interfaces:
            st.warning("Cihazdan port bilgisi alınamadı.")
        else:
            st.warning("Görüntülenecek port bulunamadı (Yetkiniz olmayabilir veya filtre kriterlerine uymuyor).")
        
    for iface in filtered_interfaces:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
                
                # Isim ve Tip Gosterimi
                itype = iface.get('type', '?')
                c1.markdown(f"**{iface['name']}**")
                c1.caption(f"Tip: {itype}")
                
                ip_val = iface.get('ip', '-')
                if isinstance(ip_val, list) and ip_val: ip_val = ip_val[0]
                c2.write(ip_val)
                
                # Status Check Logic
                admin_stat = iface.get('status')
                if admin_stat is None: admin_stat = iface.get('admin-status')
                
                raw_stat = str(admin_stat if admin_stat is not None else 'down').lower()
                is_up = raw_stat in ['1', 'up', 'enable', 'true']
                
                # Link Status (Physical) - Optional
                link_stat = iface.get('link-status')
                link_info = ""
                if link_stat is not None:
                    is_link_up = str(link_stat).lower() in ['1', 'up', 'true']
                    link_lbl = "LINK: UP" if is_link_up else "LINK: DOWN"
                    link_col = "green" if is_link_up else "red"
                    link_info = f"  \n:{link_col}[({link_lbl})]"
                
                stat_lbl, stat_col = ("ADMIN: UP", "green") if is_up else ("ADMIN: DOWN", "red")
                c3.markdown(f":{stat_col}[● {stat_lbl}]{link_info}")
                
                btn_lbl, btn_type, target = ("Kapat", "secondary", "down") if is_up else ("Aç", "primary", "up")
                
                # YETKİ KONTROLÜ: Sadece Read-Write (2) ise butonu aktif et
                can_edit = (dash_perm == 2)
                
                # Unique key
                btn_key = f"{sel_dev}_{sel_vdom}_{iface['name']}"
                
                if c4.button(btn_lbl, key=btn_key, type=btn_type, use_container_width=True, disabled=not can_edit):
                    with st.spinner("İşleniyor..."):
                        success, msg = api.toggle_interface(sel_dev, iface['name'], target, vdom=sel_vdom)
                        user_obj = AuthService.get_current_user()
                        LogService.log_action(user_obj.username, f"Port {target.upper()}", f"{sel_dev}[{sel_vdom}]", msg)
                        
                        # Cache temizle
                        get_cached_interfaces.clear()
                        
                        if success:
                            if "Task:" in msg:
                                track_task(api, msg.split("Task:")[1].strip().replace(")", ""))
                            else:
                                st.toast("Başarılı", icon="✅")
                                time.sleep(1); st.rerun()
                        else:
                            st.error("İşlem Başarısız!")
                


def track_task(api, task_id):
    p_bar = st.progress(0, "Başlatılıyor...")
    while True:
        status = api.check_task_status(task_id)
        if not status: break
        pct = int(status.get("percent", 0))
        state = str(status.get("state", "processing")).lower()
        p_bar.progress(pct, f"İlerleme: %{pct} ({state.upper()})")
        if pct >= 100 or state in ["done", "completed", "failed", "error"]:
            if state in ["failed", "error"]: st.error("Task Başarısız!")
            else: st.success("İşlem Tamamlandı!")
            break
        time.sleep(2)
    time.sleep(1); st.rerun()

def render_fmg_connection():
    st.header("🔗 FortiManager Bağlantısı")
    
    user = AuthService.get_current_user()
    cfg = st.session_state.saved_config
    target_profile = next((p for p in cfg.get("admin_profiles", []) if p['name'] == user.role), None)
    fmg_perm = 2 if user.username == "admin" else (target_profile.get("permissions", {}).get("FMG_Conn", 0) if target_profile else 0)
    can_edit = (fmg_perm == 2)
    
    if st.session_state.fmg_connected:
        st.success(f"✅ Bağlı: **{st.session_state.fmg_ip}**")
        if st.button("Bağlantıyı Kes", type="secondary", disabled=not can_edit):
            if st.session_state.api: st.session_state.api.logout()
            st.session_state.fmg_connected = False
            st.session_state.api = None
            st.session_state.devices = []
            st.rerun()
    else:
        st.info("FortiManager'a bağlanmak için API Token girin.")
        with st.form("fmg_conn"):
            ip = st.text_input("IP Adresi", value=cfg.get("fmg_ip", ""), disabled=not can_edit)
            token = st.text_input("API Token", type="password", value=cfg.get("api_token", ""), disabled=not can_edit)
            if st.form_submit_button("Bağlan", type="primary", disabled=not can_edit):
                api = FortiManagerAPI(ip, None, None, token)
                if api.login():
                    st.session_state.api, st.session_state.fmg_connected, st.session_state.fmg_ip = api, True, ip
                    ConfigService.save_config({**cfg, "fmg_ip": ip, "api_token": token})
                    st.rerun()
                else:
                    st.error("Bağlantı başarısız.")

def render_logs():

    st.header("Audit Logs")

    

    # Anti-cache: Her renderda taze veri oku

    if st.button("🔄 Logları Yenile"):

        st.rerun()

        

    df = LogService.get_logs()

    if not df.empty:

        df = df.sort_values(by="Timestamp", ascending=False)

        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Logları İndir (CSV)", df.to_csv(index=False).encode('utf-8'), 'audit_logs.csv', 'text/csv')
    else: st.info("Kayıt yok.")

def render_guide():
    st.header("📚 Kullanım Kılavuzu")
    st.markdown("""
    ### 1. Dashboard
    **İşlev:** Yönetilen cihazların ve portların durumunu anlık olarak izleyebilir, port açma/kapama işlemleri yapabilirsiniz.
    *   **Firewall & VDOM Seçimi:** İşlem yapmak istediğiniz cihazı ve sanal alanı (VDOM) seçin.
    *   **Port Listesi:** Yetkiniz dahilindeki portlar listelenir.
    *   **Durum Göstergeleri:**
        *   :green[● ADMIN: UP] -> Port yönetici tarafından açık.
        *   :red[● ADMIN: DOWN] -> Port yönetici tarafından kapalı.
        *   Link Durumu (Parantez içinde): Fiziksel kablo bağlantısını gösterir.
    *   **Aç/Kapa Butonları:** Port durumunu değiştirmek için kullanılır. (Sadece yazma yetkisi olanlar görebilir).

    ### 2. FMG Bağlantısı
    **İşlev:** FortiManager sunucusu ile bağlantı kurmanızı sağlar.
    *   **IP Adresi:** FortiManager IP adresi.
    *   **API Token:** Erişim için gerekli yetkili anahtar.
    *   Bağlantı kurulduğunda cihaz listesi otomatik çekilir.

    ### 3. Ayarlar
    **İşlev:** Sistem ve kullanıcı yapılandırması. (Sadece Admin yetkisi ile görünür).
    *   **Kullanıcılar:** Yeni kullanıcı ekleyebilir, şifre sıfırlayabilir ve yetki profili atayabilirsiniz.
    *   **Port Yetkilendirme:**
        *   **Global Yetkiler:** Kullanıcının tüm cihazlarda görebileceği ortak portlar.
        *   **Cihaz Bazlı Yetkiler:** Belirli bir cihaz için özel port izinleri.
    *   **E-posta Bildirimleri:** İşlem yapıldığında otomatik e-posta gönderimi ayarları.
    *   **LDAP:** Active Directory entegrasyon ayarları.

    ### 4. Audit Logs
    **İşlev:** Sistemde yapılan tüm kritik işlemlerin (Port açma/kapama, ayar değişimi vb.) kayıtlarını tutar.
    *   Tarih, Kullanıcı, İşlem Tipi ve Cihaz bilgisi içerir.
    *   Logları CSV formatında indirebilirsiniz.
    """)

def main():
    if not AuthService.is_authenticated(): UI.login_screen()
    else:
        UI.set_bg_image("MFA Background/Background_B.jpg")
        page = UI.sidebar_menu()
        if page == "Dashboard": render_dashboard()
        elif page == "FMG Bağlantısı": render_fmg_connection()
        elif page == "Ayarlar": render_settings()
        elif page == "Audit Logs": render_logs()
        elif page == "Kullanım Kılavuzu": render_guide()

if __name__ == "__main__": main()
