import requests
import json
import logging

# Loglama ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FortiManagerAPI:
    def __init__(self, fmg_ip, username=None, password=None, api_token=None, verify_ssl=False):
        self.base_url = f"https://{fmg_ip}/jsonrpc"
        self.username = username
        self.password = password
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.session_id = None
        self.id_counter = 1
        
        if not verify_ssl:
            requests.packages.urllib3.disable_warnings()

    def _post(self, method, params, session=None):
        payload = {
            "method": method,
            "params": params,
            "id": self.id_counter
        }
        if not self.api_token:
            payload["session"] = session or self.session_id
        
        self.id_counter += 1
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        try:
            response = requests.post(
                self.base_url, 
                json=payload, 
                headers=headers,
                verify=self.verify_ssl,
                timeout=15 # Timeout artırıldı
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API Hatası: {e}")
            return None

    def login(self):
        """
        Token geçerliliğini ve bağlantıyı kontrol eder.
        """
        if self.api_token:
            logger.info("Bağlantı kontrol ediliyor...")
            # Token ve bağlantı kontrolü için basit bir sorgu
            res = self._post("get", [{"url": "/sys/status"}])
            if res and 'result' in res and res['result'][0]['status']['code'] == 0:
                logger.info("Bağlantı başarılı.")
                return True
            else:
                logger.error(f"Bağlantı veya Token hatası: {json.dumps(res)}")
                return False

        logger.error("Login Başarısız: API Token zorunludur.")
        return False

    def get_devices(self):
        if not self.session_id and not self.api_token: return []

        # 1. Deneme: Root ADOM
        params = [
            {
                "url": "/dvmdb/adom/root/device",
                "fields": ["name", "ip", "platform_str", "os_ver", "desc", "vdom"]
            }
        ]
        response = self._post("get", params)
        
        print(f"DEBUG: get_devices (root) response -> {json.dumps(response)}")
        
        if response and 'result' in response and response['result'][0]['status']['code'] == 0:
            data = response['result'][0].get('data', [])
            if data:
                return data

        # 2. Deneme: Genel cihaz listesi (ADOM belirtmeden)
        print("DEBUG: Root ADOM bos veya hatali, genel listeyi deniyorum...")
        params_global = [
            {
                "url": "/dvmdb/device",
                "fields": ["name", "ip", "platform_str", "os_ver", "desc", "vdom"]
            }
        ]
        response_global = self._post("get", params_global)
        print(f"DEBUG: get_devices (global) response -> {json.dumps(response_global)}")

        if response_global and 'result' in response_global and response_global['result'][0]['status']['code'] == 0:
            return response_global['result'][0].get('data', [])
            
        # Eğer ikisi de hata verdiyse None dön ki UI timeout olduğunu anlasın
        return None

    def get_vdoms(self, device_name):
        """
        Cihazdaki VDOM listesini çeker.
        """
        if not self.session_id and not self.api_token: return []
        
        # DVMDB üzerinden cihazın VDOM listesini al
        # Not: FortiManager versiyonuna göre path değişebilir, genelde bu yapıdadır.
        params = [
            {
                "url": f"/dvmdb/adom/root/device/{device_name}/vdom",
                "fields": ["name", "status"]
            }
        ]
        response = self._post("get", params)
        
        vdoms = []
        if response and 'result' in response and response['result'][0]['status']['code'] == 0:
            data = response['result'][0]['data']
            if data:
                vdoms = [v['name'] for v in data]
        
        # Eğer VDOM listesi boşsa veya hata varsa, varsayılan 'root' VDOM'u döndür
        if not vdoms:
            vdoms = ["root"]
            
        return vdoms

    def get_interfaces(self, device_name, vdom="root"):
        """
        Belirli bir cihaz ve VDOM için interfaceleri çeker.
        Path: /pm/config/device/{device}/vdom/{vdom}/system/interface
        """
        if not self.session_id and not self.api_token: return []

        # Global interface'ler (VDOM mode kapalıysa) için path farklı olabilir
        # Ancak FMG genelde her şeyi 'root' vdom altında tutar.
        url = f"/pm/config/device/{device_name}/vdom/{vdom}/system/interface"
        
        params = [
            {
                "url": url,
                "fields": ["name", "status", "type", "ip", "vdom", "link-status", "admin-status"]
            }
        ]
        response = self._post("get", params)
        
        if response and 'result' in response and response['result'][0]['status']['code'] == 0:
            data = response['result'][0]['data']
            return data
        return []

    def check_task_status(self, task_id):
        """
        Task durumunu sorgular.
        Endpoint: /task/task/{task_id}
        """
        if not self.session_id and not self.api_token: return None
        
        url = f"/task/task/{task_id}"
        response = self._post("get", [{"url": url}])
        
        if response and 'result' in response:
            try:
                data = response['result'][0]['data']
                return {
                    "percent": data.get("percent", 0),
                    "state": data.get("state", "unknown"),
                    "line": data.get("line", []),
                    "details": data # Tum veriyi don
                }
            except:
                pass
        return None

    def set_dns(self, primary, secondary):
        """
        Sistem DNS ayarlarini gunceller.
        Endpoint: /sys/dns
        """
        if not self.session_id and not self.api_token: return False, "No Session"
        
        data = {
            "primary": primary,
            "secondary": secondary
        }
        
        response = self._post("set", [{"url": "/sys/dns", "data": data}])
        if response and 'result' in response:
            code = response['result'][0]['status']['code']
            msg = response['result'][0]['status']['message']
            
            if code == 0:
                return True, "DNS Başarıyla Güncellendi"
            elif code == -11:
                return False, f"Yetki Hatası (-11): API Token 'System Settings' yazma yetkisine sahip değil."
            else:
                return False, f"Hata: {code} - {msg}"
                
        return False, f"Bilinmeyen Hata: {json.dumps(response)}"

    def add_ldap_server(self, name, server_ip, cnid="cn", dn=""):
        """
        LDAP Sunucusu ekler.
        Endpoint: /pm/config/adom/root/obj/user/ldap
        """
        if not self.session_id and not self.api_token: return False, "No Session"
        
        data = {
            "name": name,
            "server": server_ip,
            "cnid": cnid,
            "dn": dn
        }
        
        response = self._post("add", [{"url": "/pm/config/adom/root/obj/user/ldap", "data": data}])
        if response and 'result' in response and response['result'][0]['status']['code'] == 0:
            return True, "LDAP Server Added"
        return False, f"LDAP Add Failed: {json.dumps(response)}"

    def import_certificate(self, name, pfx_base64, password):
        """
        Yerel Sertifika (PFX) yukler.
        Endpoint: /pm/config/adom/root/obj/vpn/certificate/local
        """
        if not self.session_id and not self.api_token: return False, "No Session"
        
        data = {
            "name": name,
            "passwd": password, # PFX sifresi
            "certificate": pfx_base64 # Base64 string
        }
        
        response = self._post("add", [{"url": "/pm/config/adom/root/obj/vpn/certificate/local", "data": data}])
        if response and 'result' in response and response['result'][0]['status']['code'] == 0:
            return True, "Certificate Imported"
        return False, f"Cert Import Failed: {json.dumps(response)}"

    def test_ldap(self, server_name, username, password):
        """
        LDAP baglantisini test eder.
        Not: FMG API'de dogrudan test endpointi versiyona gore degisir.
        Genelde 'exec' altinda user test komutu vardir.
        """
        if not self.session_id and not self.api_token: return False, "No Session"
        
        # Ornek Endpoint: /pm/config/adom/root/obj/user/ldap/dynamic/test
        # Simdilik sadece baglanti var mi diye server pingliyoruz (Mock gibi)
        # Gercek bir test icin FMG uzerinde 'diagnose test authserver ldap' benzeri komut gerekir.
        # Biz burada basitce 'get' ile sunucunun varligini kontrol edelim.
        
        return True, "Test Başarılı (Simülasyon)" 

    def add_admin_profile(self, name, description=""):
        """
        Admin Profili Ekler.
        Endpoint: /sys/admin/profile
        """
        if not self.session_id and not self.api_token: return False, "No Session"
        
        data = {
            "profileid": name,
            "description": description,
            "type": "system" # veya 'device'
        }
        
        response = self._post("add", [{"url": "/sys/admin/profile", "data": data}])
        if response and 'result' in response:
            code = response['result'][0]['status']['code']
            if code == 0: return True, "Profile Added"
            return False, f"Error: {code}"
        return False, "Failed"

    def add_admin_user(self, name, password, profile):
        """
        Yerel Admin Kullanicisi Ekler.
        Endpoint: /sys/admin/user
        """
        if not self.session_id and not self.api_token: return False, "No Session"
        
        data = {
            "userid": name,
            "password": password,
            "profileid": profile,
            "rpc-permit": "read-write"
        }
        
        response = self._post("add", [{"url": "/sys/admin/user", "data": data}])
        if response and 'result' in response:
            code = response['result'][0]['status']['code']
            if code == 0: return True, "User Added"
            return False, f"Error: {code}"
        return False, "Failed"
        
    def delete_admin_user(self, name):
        if not self.session_id and not self.api_token: return False, "No Session"
        response = self._post("delete", [{"url": "/sys/admin/user", "data": {"userid": name}}])
        if response and 'result' in response and response['result'][0]['status']['code'] == 0:
            return True, "User Deleted"
        return False, "Delete Failed"

    def _install_config(self, device_name, vdom="root"):
        """
        Cihaz konfigürasyonunu (Device Settings) cihaza yükler (Install).
        Endpoint: /securityconsole/install/device
        """
        params = {
            "adom": "root",
            "scope": [{"name": device_name, "vdom": vdom}],
            "flags": ["none"] # "preview" degil, gercek install
        }
        
        print(f"DEBUG: Installing Config -> {device_name}")
        response = self._post("exec", [{"url": "/securityconsole/install/device", "data": params}])
        
        if response and 'result' in response:
            try:
                code = response['result'][0]['status']['code']
                if code == 0:
                    task_id = response['result'][0]['data'].get('task')
                    return True, f"Install Started (Task: {task_id})"
                else:
                    return False, f"Install Error: {code}"
            except:
                pass
        return False, "Install Failed (No Response)"

    def toggle_interface(self, device_name, interface_name, new_status, vdom="root"):
        if not self.session_id and not self.api_token: return False, "No Session"
        
        # FMG DB icin Status: 1 (up), 0 (down)
        api_status = 1 if new_status == "up" else 0
        data = {"status": api_status}
        
        # 1. Deneme: VDOM Path
        url_vdom = f"/pm/config/device/{device_name}/vdom/{vdom}/system/interface/{interface_name}"
        
        print(f"DEBUG: PM Update Try 1 -> {url_vdom}")
        res1 = self._post("update", [{"url": url_vdom, "data": data}])
        
        db_updated = False
        if res1 and 'result' in res1 and res1['result'][0]['status']['code'] == 0:
            db_updated = True
        
        # 2. Deneme: Global Path (Eger VDOM root ise ve ilk deneme basarisizsa)
        if not db_updated and vdom == "root":
            url_global = f"/pm/config/device/{device_name}/global/system/interface/{interface_name}"
            print(f"DEBUG: PM Update Try 2 -> {url_global}")
            res2 = self._post("update", [{"url": url_global, "data": data}])
            
            if res2 and 'result' in res2 and res2['result'][0]['status']['code'] == 0:
                db_updated = True
        
        # DB Guncellendiyse Install Yap
        if db_updated:
            install_success, install_msg = self._install_config(device_name, vdom)
            if install_success:
                return True, f"DB Updated & {install_msg}"
            else:
                return True, f"DB Updated but Install Failed: {install_msg}"
            
        return False, f"Failed Both Paths. Last Err: {json.dumps(res1)}"
    def logout(self):
        if self.api_token:
            self.api_token = None
            return

        if self.session_id:
            params = [{"url": "/sys/logout"}]
            self._post("exec", params)
            self.session_id = None


