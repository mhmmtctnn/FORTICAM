import streamlit as st
import pandas as pd
import json
import time
import base64
from config_service import ConfigService
from auth_service import AuthService
from system_service import SystemService

def render_settings():
    st.header("⚙️ Sistem Yapılandırması")
    
    user = AuthService.get_current_user()
    cfg = st.session_state.saved_config
    profiles = cfg.get("admin_profiles", [])
    target_profile = next((p for p in profiles if p['name'] == user.role), None)
    
    # Yetki Seviyeleri (System modülü için)
    sys_perm = 2 if user.username == "admin" else (target_profile.get("permissions", {}).get("System", 0) if target_profile else 0)
    can_edit = (sys_perm == 2)

    # --- USER EDIT DIALOG ---
    @st.dialog("Kullanıcı Düzenle", width="large")
    def show_user_edit(username):
        accounts_ref = cfg.get("local_accounts", [])
        acc = next((x for x in accounts_ref if x['user'] == username), None)
        if not acc: st.error("Kullanıcı bulunamadı"); return
        
        st.caption(f"Düzenlenen: **{username}**")
        
        # 1. Profil Degistirme
        avail_profs = [p['name'] for p in cfg.get("admin_profiles", [])]
        cur_idx = avail_profs.index(acc['profile']) if acc['profile'] in avail_profs else 0
        new_prof = st.selectbox("Yetki Profili", avail_profs, index=cur_idx)
        
        st.divider()
        
        # 2. Global Port Izinleri
        st.markdown("#### 🌍 Global Port İzinleri (Tüm Cihazlar)")
        st.caption("Buraya girilen portlar, kullanıcının yönettiği TÜM cihazlarda erişilebilir olacaktır.")
        
        global_ports = acc.get("global_allowed_ports", [])
        gp_str = st.text_area("Global İzinli Portlar (Virgülle ayırın)", value=", ".join(global_ports), help="Örnek: port1, port2, wan1", key=f"gp_area_{username}")
        
        if st.button("Global İzinleri Kaydet", key=f"save_global_{username}"):
            new_gp = [p.strip() for p in gp_str.split(",") if p.strip()]
            acc["global_allowed_ports"] = new_gp
            ConfigService.save_config(cfg)
            st.success("Global izinler başarıyla güncellendi!")
            time.sleep(1); st.rerun()
            
        st.divider()
        st.markdown("#### 🔌 Port Erişim Yetkileri")
        st.caption("Kullanıcının cihazlarda görebileceği portları sınırlayın. (Ayar yapılmazsa tümünü görür)")
        
        current_perms = acc.get("allowed_ports", {})
        
        # Mevcut Izinleri Listele
        if current_perms:
            st.markdown("**Mevcut İzinler:**")
            for dev_name, ports in list(current_perms.items()):
                with st.container(border=True):
                    xc1, xc2 = st.columns([4, 1])
                    xc1.markdown(f"**{dev_name}**")
                    xc1.code(", ".join(ports))
                    if xc2.button("Sil", key=f"rem_perm_{username}_{dev_name}"):
                        del current_perms[dev_name]
                        acc["allowed_ports"] = current_perms
                        ConfigService.save_config(cfg)
                        st.rerun()
        
        st.markdown("---")
        st.markdown("**➕ Yeni Kısıtlama Ekle**")
        
        # DEBUG: Sorunu anlamak icin durum bilgisi
        is_conn = st.session_state.get("fmg_connected")
        dev_list = st.session_state.get("devices")
        st.info(f"Sistem Durumu: Bağlantı={'✅' if is_conn else '❌'}, Cihaz Sayısı={len(dev_list) if dev_list else 0}")
        
        if st.session_state.get("fmg_connected"):
            api = st.session_state.api
            # Cihaz listesini tazele
            if not st.session_state.get("devices"):
                with st.spinner("Cihazlar getiriliyor..."):
                    st.session_state.devices = api.get_devices()
            
            if st.session_state.get("devices"):
                dev_opts = [d['name'] for d in st.session_state.devices]
                s_dev = st.selectbox("Cihaz Seçin", dev_opts, key=f"add_perm_dev_{username}")
                
                if s_dev:
                    # VDOM listesini al
                    with st.spinner("VDOM'lar getiriliyor..."):
                        vdoms = api.get_vdoms(s_dev)
                    s_vdom = st.selectbox("VDOM Seçin", vdoms, key=f"add_perm_vdom_{username}")
                    
                    if s_vdom:
                        try:
                            with st.spinner("Portlar alınıyor..."):
                                raw_ifaces = api.get_interfaces(s_dev, vdom=s_vdom)
                                p_names = [i['name'] for i in raw_ifaces]
                            
                            s_ports = st.multiselect("İzin Verilecek Portlar", p_names, key=f"add_perm_ports_{username}")
                            
                            if st.button("Yetkiyi Kaydet", key=f"save_perm_{username}", type="primary"):
                                if "allowed_ports" not in acc: acc["allowed_ports"] = {}
                                acc["allowed_ports"][s_dev] = s_ports
                                ConfigService.save_config(cfg)
                                st.success("Yetki başarıyla eklendi!")
                                time.sleep(1); st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")
            else:
                st.warning("Hiç cihaz bulunamadı.")
        else:
            st.error("⚠️ Port kısıtlaması eklemek için önce FortiManager'a bağlanmalısınız.")

        st.divider()
        if st.button("Değişiklikleri Kaydet ve Kapat", use_container_width=True):
            acc['profile'] = new_prof
            ConfigService.save_config(cfg)
            st.rerun()

    tab_auth, tab_sys, tab_email = st.tabs([
        "🔐 Kimlik Doğrulama & Yetkilendirme", 
        "🛠️ Sistem Servisleri (DNS/SSL)",
        "📧 E-posta Bildirimleri"
    ])
    
    # --- TAB 1: AUTH & RBAC ---
    with tab_auth:
        col_ldap, col_profiles = st.columns([1.2, 1], gap="large")
        
        with col_ldap:
            ldap_cfg = cfg.get("ldap_settings", {})
            enabled = ldap_cfg.get("enabled", False)
            
            # --- DURUM KONTROLU ---
            current_status = "DISABLED"
            if enabled:
                servers = ldap_cfg.get("servers", [])
                if servers and servers[0]:
                    is_ok = AuthService.is_ldap_reachable(servers[0], ldap_cfg.get("port", 636))
                    current_status = "ONLINE" if is_ok else "OFFLINE"
                else:
                    current_status = "NO_SERVER"
            
            status_color = "green" if current_status == "ONLINE" else "red" if current_status in ["OFFLINE", "ERROR"] else "grey"
            st.markdown(f"### 📂 LDAP / Active Directory :{status_color}[● {current_status}]")
            
            new_enabled = st.toggle("LDAP Girişini Aktif Et", value=enabled, disabled=not can_edit)
            if new_enabled != enabled:
                ldap_cfg["enabled"] = new_enabled
                cfg["ldap_settings"] = ldap_cfg
                ConfigService.save_config(cfg); st.rerun()
            
            with st.container(border=True):
                st.markdown("**1. Sunucu Kümesi (Cluster)**")
                if "temp_servers" not in st.session_state: st.session_state.temp_servers = ldap_cfg.get("servers", [])
                
                for i, srv in enumerate(st.session_state.temp_servers):
                    c_in, c_bt = st.columns([6, 1])
                    st.session_state.temp_servers[i] = c_in.text_input(f"LDAP Sunucu {i+1}", value=srv, label_visibility="collapsed", key=f"srv_u_{i}", disabled=not can_edit)
                    if c_bt.button("🗑️", key=f"del_srv_u_{i}", disabled=not can_edit): 
                        st.session_state.temp_servers.pop(i)
                        st.rerun()
                
                if st.button("➕ Sunucu Ekle", disabled=not can_edit): 
                    st.session_state.temp_servers.append("")
                    st.rerun()
                
                st.divider()
                st.markdown("**2. Bağlantı Parametreleri**")
                c_ssl, c_pi = st.columns([2, 1])
                use_ssl = c_ssl.toggle("SSL Kullan", value=ldap_cfg.get("use_ssl", True), disabled=not can_edit)
                port = 636 if use_ssl else 389
                c_pi.info(f"Port: {port}")
                base_dn = st.text_input("Base DN", value=ldap_cfg.get("base_dn", ""), disabled=not can_edit)
                
                if st.button("💾 LDAP Ayarlarını Kaydet", type="primary", use_container_width=True, disabled=not can_edit):
                    final_servers = [s.strip() for s in st.session_state.temp_servers if s.strip()]
                    ldap_cfg.update({"enabled": new_enabled, "servers": final_servers, "port": port, "use_ssl": use_ssl, "base_dn": base_dn})
                    cfg["ldap_settings"] = ldap_cfg
                    ConfigService.save_config(cfg); st.success("Kaydedildi."); time.sleep(0.5); st.rerun()

            st.markdown("##### 🔗 Grup & Rol Eşleştirmeleri")
            with st.container(border=True):
                mappings = ldap_cfg.get("mappings", [])
                if "temp_mappings" not in st.session_state: st.session_state.temp_mappings = mappings.copy()
                
                if not st.session_state.temp_mappings: st.info("Eşleşme yok.")
                
                for i, m in enumerate(st.session_state.temp_mappings):
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 2, 1])
                        st.session_state.temp_mappings[i]["group_dn"] = c1.text_input("DN", value=m.get("group_dn", ""), key=f"m_dn_{i}", label_visibility="collapsed", disabled=not can_edit)
                        avail_profs = [p['name'] for p in cfg.get("admin_profiles", [])]
                        st.session_state.temp_mappings[i]["profile"] = c2.selectbox("Prof", options=avail_profs, index=avail_profs.index(m.get("profile")) if m.get("profile") in avail_profs else 0, key=f"m_pr_{i}", label_visibility="collapsed", disabled=not can_edit)
                        if c3.button("🗑️", key=f"m_del_{i}", disabled=not can_edit):
                            st.session_state.temp_mappings.pop(i); st.rerun()
                
                c_a1, c_a2 = st.columns(2)
                if c_a1.button("➕ Ekle", disabled=not can_edit): st.session_state.temp_mappings.append({"group_dn": "", "profile": "Standard_User"}); st.rerun()
                if c_a2.button("💾 Mappings Kaydet", disabled=not can_edit):
                    ldap_cfg["mappings"] = st.session_state.temp_mappings
                    ConfigService.save_config(cfg); st.success("Kaydedildi."); time.sleep(0.5); st.rerun()

            with st.expander("🧪 Bağlantı Testi", expanded=True):
                st.caption("Girilen ayarlarla bir kullanıcının LDAP bağlantısını doğrulayın.")
                tu, tp = st.columns(2)
                t_u = tu.text_input("Test Kullanıcı", placeholder="kullaniciadi", key="test_u_final")
                t_p = tp.text_input("Şifre  ", type="password", key="test_p_final")
                
                if st.button("Şimdi Test Et", use_container_width=True, type="secondary"):
                    # Mevcut state'deki sunucuyu al
                    if "temp_servers" in st.session_state and st.session_state.temp_servers:
                        srv = st.session_state.temp_servers[0].strip()
                        if srv:
                            with st.spinner(f"Sorgulanıyor: {srv}..."):
                                s, m = AuthService.test_connection(srv, port, use_ssl, t_u, t_p)
                                if s: st.success(m)
                                else: st.error(m)
                        else:
                            st.error("Sunucu adresi boş olamaz.")
                    else:
                        st.warning("Lütfen önce bir sunucu adresi girin.")

        with col_profiles:
            st.subheader("🛡️ Admin Profiles")
            modules = ["Dashboard", "FMG_Conn", "System", "Audit Logs"] 
            mod_map = {"Dashboard": "Dashboard", "FMG_Conn": "FMG_Conn", "System": "System", "Audit Logs": "Logs"}
            levels = {0: "None", 1: "Read", 2: "Write"}
            level_rev = {"None": 0, "Read": 1, "Write": 2}

            @st.dialog("Edit Profile")
            def show_edit_profile_dialog(edit_name):
                p_obj = next((x for x in profiles if x['name'] == edit_name), None)
                if edit_name == "NEW_PROFILE": p_obj = {"name": "", "permissions": {m: 1 for m in mod_map.values()}}
                is_super = (edit_name == "Super_User")
                if is_super: st.warning("Super_User değiştirilemez.")
                new_n = st.text_input("Profil Adı", value=p_obj['name'], disabled=is_super)
                u_perms = {}
                for display_mod in modules:
                    st.markdown(f"**{display_mod}**")
                    curr_val = p_obj.get("permissions", {}).get(mod_map[display_mod], 0)
                    sel_val = st.segmented_control(label=display_mod, options=["None", "Read", "Write"], default=levels[curr_val], key=f"seg_dlg_{edit_name}_{display_mod}", label_visibility="collapsed", disabled=is_super)
                    u_perms[mod_map[display_mod]] = level_rev.get(sel_val, 0)
                if st.button("Save", type="primary", disabled=is_super):
                    if edit_name == "NEW_PROFILE": cfg["admin_profiles"].append({"name": new_n, "permissions": u_perms})
                    else:
                        for prf in cfg["admin_profiles"]:
                            if prf['name'] == edit_name: prf['permissions'] = u_perms; prf['name'] = new_n
                    ConfigService.save_config(cfg); st.rerun()

            with st.container(border=True):
                for p in profiles:
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**{p['name']}**")
                    perms = p.get("permissions", {})
                    c2.caption(f"D:{perms.get('Dashboard',0)} S:{perms.get('System',0)} L:{perms.get('Logs',0)}")
                    if c3.button("📝", key=f"edit_p_{p['name']}", disabled=not can_edit): show_edit_profile_dialog(p['name'])
                if st.button("➕ Add Profile", disabled=not can_edit, use_container_width=True): show_edit_profile_dialog("NEW_PROFILE")

            st.subheader("👤 Local Accounts")
            with st.container(border=True):
                accounts = cfg.get("local_accounts", [])
                for acc in accounts:
                    c1, c2, c3, c4 = st.columns([2, 2, 0.5, 0.5])
                    c1.write(f"**{acc['user']}**")
                    c2.caption(acc['profile'])
                    
                    if c3.button("⚙️", key=f"u_edit_{acc['user']}", disabled=not can_edit, help="Yetkileri Düzenle"):
                        show_user_edit(acc['user'])
                        
                    if c4.button("🗑️", key=f"u_del_{acc['user']}", disabled=not can_edit):
                        cfg["local_accounts"] = [x for x in accounts if x['user'] != acc['user']]
                        ConfigService.save_config(cfg); st.rerun()
                with st.expander("➕ Add User"):
                    un = st.text_input("Kullanıcı")
                    up = st.text_input("Şifre ", type="password")
                    upr = st.selectbox("Profil ", [p['name'] for p in cfg.get("admin_profiles", [])])
                    if st.button("Kullanıcıyı Kaydet"):
                        cfg["local_accounts"].append({"user": un, "profile": upr, "password": up})
                        ConfigService.save_config(cfg); st.rerun()

    # --- TAB 2: SYSTEM ---
    with tab_sys:
        c_dns, c_cert = st.columns(2, gap="large")
        with c_dns:
            with st.container(border=True):
                dns_ok = SystemService.check_dns_status()
                d_col, d_stat = ("green", "ONLINE") if dns_ok else ("red", "OFFLINE")
                st.markdown(f"### 🌐 DNS Ayarları :{d_col}[● {d_stat}]")
                dns1 = st.text_input("DNS 1", value=cfg.get("primary_dns", "8.8.8.8"), disabled=not can_edit)
                dns2 = st.text_input("DNS 2", value=cfg.get("secondary_dns", "1.1.1.1"), disabled=not can_edit)
                if st.button("Uygula", disabled=not can_edit, type="primary"):
                    cfg.update({"primary_dns": dns1, "secondary_dns": dns2})
                    ConfigService.save_config(cfg); s, m = SystemService.update_dns(dns1, dns2)
                    st.success(m) if s else st.warning(m); time.sleep(0.5); st.rerun()
        with c_cert:
            with st.container(border=True):
                st.markdown("### 📜 SSL Sertifikası")
                upl = st.file_uploader("Dosya", type=["pfx"], disabled=not can_edit)
                pws = st.text_input("Şifre  ", type="password", disabled=not can_edit)
                if st.button("Sertifikayı Yükle", disabled=not can_edit):
                    if upl:
                        b64 = base64.b64encode(upl.getvalue()).decode('utf-8')
                        s, m = SystemService.apply_pfx_certificate(b64, pws)
                        st.success(m) if s else st.error(m)

    # --- TAB 3: EMAIL ---
    with tab_email:
        st.header("📧 E-posta Bildirim Ayarları")
        st.caption("Operatör işlemleri veya kritik durumlarda otomatik e-posta gönderimi için yapılandırma.")
        
        email_cfg = cfg.get("email_settings", {})
        
        # 1. Genel Durum
        is_enabled = st.toggle("E-posta Bildirimlerini Aktif Et", value=email_cfg.get("enabled", False), disabled=not can_edit)
        
        st.divider()
        
        c_smtp, c_receiver = st.columns([1, 1], gap="large")
        
        with c_smtp:
            with st.container(border=True):
                st.subheader("📤 Gönderici (SMTP) Ayarları")
                
                smtp_server = st.text_input("SMTP Sunucusu", value=email_cfg.get("smtp_server", ""), placeholder="smtp.office365.com", disabled=not can_edit)
                smtp_port = st.number_input("SMTP Portu", value=email_cfg.get("smtp_port", 587), step=1, disabled=not can_edit)
                sender_email = st.text_input("Gönderici E-posta", value=email_cfg.get("sender_email", ""), placeholder="noreply@domain.com", disabled=not can_edit)
                sender_password = st.text_input("Gönderici Şifresi / App Password", value=email_cfg.get("sender_password", ""), type="password", disabled=not can_edit)
        
        with c_receiver:
            with st.container(border=True):
                st.subheader("📩 Alıcı Listesi")
                st.caption("Bildirimlerin gönderileceği e-posta adresleri.")
                
                # Alıcıları yönetmek için basit bir liste arayüzü
                receivers = email_cfg.get("receiver_emails", [])
                
                # Data Editor ile düzenleme
                rec_df = pd.DataFrame({"E-posta": receivers})
                edited_df = st.data_editor(rec_df, num_rows="dynamic", use_container_width=True, disabled=not can_edit, key="email_receivers_editor")
                
                current_receivers = [row["E-posta"] for index, row in edited_df.iterrows() if row["E-posta"]]

        st.divider()
        
        c_save, c_test = st.columns([1, 4])
        
        if c_save.button("💾 Ayarları Kaydet", type="primary", disabled=not can_edit, key="save_email_settings"):
            email_cfg["enabled"] = is_enabled
            email_cfg["smtp_server"] = smtp_server
            email_cfg["smtp_port"] = smtp_port
            email_cfg["sender_email"] = sender_email
            email_cfg["sender_password"] = sender_password
            email_cfg["receiver_emails"] = current_receivers
            
            cfg["email_settings"] = email_cfg
            ConfigService.save_config(cfg)
            st.success("E-posta ayarları başarıyla kaydedildi!")
            time.sleep(1)
            st.rerun()

        if c_test.button("🧪 Test E-postası Gönder", disabled=not can_edit, key="test_email_send"):
            # Geçici ayarlarla test etme imkanı (henüz kaydetmemiş olabilir)
            temp_cfg = {
                "enabled": True, # Test için zorla aç
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "sender_email": sender_email,
                "sender_password": sender_password,
                "receiver_emails": current_receivers
            }
            
            # EmailService'i import etmek gerekebilir, fonksiyon başında değilse.
            # Ancak settings_view modül scope'unda importlar var mı kontrol edelim.
            # Yoksa import eklemeliyiz. Fonksiyon içine eklemek güvenli.
            from email_service import EmailService
            
            # Geçici config ile test için ConfigService'i mock'lamak zor olabilir.
            # EmailService doğrudan parametre alsa daha iyi olurdu ama ConfigService'den okuyor.
            # Çözüm: EmailService.send_notification'ı güncellemek yerine, 
            # test mantığını burada manuel yapabiliriz veya ConfigService'e geçici yazıp geri alabiliriz.
            # En temiz: EmailService'e parametre geçebilme yeteneği eklemek.
            # Şimdilik mevcut config üzerinden (önce kaydet uyarısı verelim) ya da manuel smtplib kullanalım.
            
            # Kullanıcıya önce kaydetmesini söylemek en basiti.
            if cfg.get("email_settings") != temp_cfg:
                 st.warning("⚠️ Lütfen önce ayarları kaydedin.")
            else:
                with st.spinner("Test e-postası gönderiliyor..."):
                    success, msg = EmailService.send_notification(
                        subject="[TEST] FortiManager Controller Bildirimi", 
                        message_body="Bu bir test e-postasıdır. Ayarlarınız doğru çalışıyor."
                    )
                    if success:
                        st.success(f"Başarılı: {msg}")
                    else:
                        st.error(f"Hata: {msg}")